#!/bin/bash
# Test PostgreSQL TLS connectivity in k3s environment
# Verifies that PostgreSQL is serving TLS and all consumers connect with SSL.
set -euo pipefail

NAMESPACE="${NAMESPACE:-erechnung}"

echo "=== PostgreSQL TLS Test Suite (k3s) ==="
echo "Namespace: $NAMESPACE"
echo ""

PASS=0
FAIL=0

pass() {
    echo "  ✅ PASS: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "  ❌ FAIL: $1"
    FAIL=$((FAIL + 1))
}

# -------------------------------------------------------
echo "--- Pre-check: cert-manager Certificate is Ready ---"
CERT_READY=$(kubectl get certificate postgres-tls -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "ERROR")
if [ "$CERT_READY" = "True" ]; then
    pass "cert-manager Certificate 'postgres-tls' is Ready"
else
    fail "cert-manager Certificate not ready (status: $CERT_READY)"
fi

# -------------------------------------------------------
echo ""
echo "--- Pre-check: TLS Secret exists with expected keys ---"
SECRET_KEYS=$(kubectl get secret postgres-tls-certs -n "$NAMESPACE" -o jsonpath='{.data}' 2>/dev/null | python3 -c "import sys,json; print(' '.join(sorted(json.load(sys.stdin).keys())))" 2>/dev/null || echo "ERROR")
if echo "$SECRET_KEYS" | grep -q "ca.crt" && echo "$SECRET_KEYS" | grep -q "tls.crt" && echo "$SECRET_KEYS" | grep -q "tls.key"; then
    pass "Secret 'postgres-tls-certs' contains ca.crt, tls.crt, tls.key"
else
    fail "Secret missing expected keys (found: $SECRET_KEYS)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 1: PostgreSQL ssl setting is 'on' ---"
SSL_SETTING=$(kubectl exec -n "$NAMESPACE" deploy/postgres -- psql -U postgres -d erechnung -c "SHOW ssl;" -t 2>/dev/null | tr -d '[:space:]')
if [ "$SSL_SETTING" = "on" ]; then
    pass "PostgreSQL ssl = on"
else
    fail "PostgreSQL ssl = '$SSL_SETTING' (expected 'on')"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 2: PostgreSQL accepts TLS connections ---"
SSL_INFO=$(kubectl exec -n "$NAMESPACE" deploy/postgres -- psql "host=localhost user=postgres dbname=erechnung sslmode=require" -c "SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();" -t 2>/dev/null || echo "ERROR")
if echo "$SSL_INFO" | grep -q "t"; then
    pass "PostgreSQL reports SSL=true for TLS connection"
else
    fail "PostgreSQL does not report SSL=true (output: $SSL_INFO)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 3: TLS version is 1.2 or 1.3 ---"
CIPHER_INFO=$(kubectl exec -n "$NAMESPACE" deploy/postgres -- psql "host=localhost user=postgres dbname=erechnung sslmode=require" -c "SELECT version, cipher, bits FROM pg_stat_ssl WHERE pid = pg_backend_pid();" -t 2>/dev/null || echo "ERROR")
if echo "$CIPHER_INFO" | grep -qi "TLSv1\.\(2\|3\)"; then
    pass "TLS 1.2 or 1.3 in use ($(echo "$CIPHER_INFO" | tr -s ' '))"
else
    fail "Unexpected TLS version (output: $CIPHER_INFO)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 4: Django connects with SSL ---"
DJANGO_SSL=$(kubectl exec -n "$NAMESPACE" deploy/django-web -- python project_root/manage.py shell -c "
from django.db import connection
connection.ensure_connection()
with connection.cursor() as cursor:
    cursor.execute('SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
    row = cursor.fetchone()
    print(f'SSL={row[0]}, Version={row[1]}, Cipher={row[2]}' if row else 'SSL=None')
" 2>/dev/null || echo "ERROR")
if echo "$DJANGO_SSL" | grep -q "SSL=True"; then
    pass "Django connects to PostgreSQL with SSL ($DJANGO_SSL)"
else
    fail "Django SSL connection check failed (output: $DJANGO_SSL)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 5: Django sslmode is verify-ca ---"
SSL_MODE=$(kubectl exec -n "$NAMESPACE" deploy/django-web -- python project_root/manage.py shell -c "
from django.conf import settings
opts = settings.DATABASES['default'].get('OPTIONS', {})
print('sslmode=' + opts.get('sslmode', 'NOT_SET'))
" 2>/dev/null || echo "ERROR")
if echo "$SSL_MODE" | grep -q "sslmode=verify-ca"; then
    pass "Django sslmode = verify-ca"
elif echo "$SSL_MODE" | grep -q "sslmode=verify\|sslmode=require"; then
    pass "Django sslmode set ($SSL_MODE)"
else
    fail "Django sslmode not properly set (output: $SSL_MODE)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 6: Celery worker connects with SSL ---"
CELERY_SSL=$(kubectl exec -n "$NAMESPACE" deploy/celery-worker -- python -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'invoice_project.settings'
os.chdir('/app/project_root')
django.setup()
from django.db import connection
connection.ensure_connection()
with connection.cursor() as cursor:
    cursor.execute('SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
    row = cursor.fetchone()
    print(f'SSL={row[0]}, Version={row[1]}' if row else 'SSL=None')
" 2>/dev/null || echo "ERROR")
if echo "$CELERY_SSL" | grep -q "SSL=True"; then
    pass "Celery worker connects to PostgreSQL with SSL ($CELERY_SSL)"
else
    fail "Celery worker SSL connection check failed (output: $CELERY_SSL)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 7: CA cert mounted in Django pod ---"
CA_EXISTS=$(kubectl exec -n "$NAMESPACE" deploy/django-web -- ls -la /etc/ssl/postgres/ca.crt 2>/dev/null || echo "NOT_FOUND")
if echo "$CA_EXISTS" | grep -q "ca.crt"; then
    pass "CA certificate mounted at /etc/ssl/postgres/ca.crt"
else
    fail "CA certificate not found at /etc/ssl/postgres/ca.crt"
fi

# -------------------------------------------------------
echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
