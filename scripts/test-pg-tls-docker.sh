#!/bin/bash
# Test PostgreSQL TLS connectivity in Docker Compose environment
# Verifies that PostgreSQL is serving TLS and Django connects with SSL.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== PostgreSQL TLS Test Suite (Docker Compose) ==="
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
echo "--- Pre-check: Certificates exist ---"
if [ -f "infra/postgres/certs/server.crt" ] && [ -f "infra/postgres/certs/server.key" ] && [ -f "infra/postgres/certs/ca.crt" ]; then
    pass "TLS certificates present in infra/postgres/certs/"
else
    fail "TLS certificates missing — run: bash scripts/generate-pg-certs.sh"
    echo "Aborting."
    exit 1
fi

# -------------------------------------------------------
echo ""
echo "--- Test 1: PostgreSQL accepts TLS connections ---"
SSL_INFO=$(docker compose exec -T db psql "host=localhost user=postgres dbname=erechnung_ci sslmode=require" -c "SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();" -t 2>/dev/null || echo "ERROR")
if echo "$SSL_INFO" | grep -q "t"; then
    pass "PostgreSQL reports SSL=true for TCP connection"
else
    fail "PostgreSQL does not report SSL=true (output: $SSL_INFO)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 2: PostgreSQL ssl setting is 'on' ---"
SSL_SETTING=$(docker compose exec -T db psql -U postgres -d erechnung_ci -c "SHOW ssl;" -t 2>/dev/null | tr -d '[:space:]')
if [ "$SSL_SETTING" = "on" ]; then
    pass "PostgreSQL ssl = on"
else
    fail "PostgreSQL ssl = '$SSL_SETTING' (expected 'on')"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 3: Django connects with SSL ---"
DJANGO_SSL=$(docker compose exec -T web python project_root/manage.py shell -c "
from django.db import connection
connection.ensure_connection()
with connection.cursor() as cursor:
    cursor.execute('SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
    row = cursor.fetchone()
    print('SSL=' + str(row[0]) if row else 'SSL=None')
" 2>/dev/null || echo "ERROR")
if echo "$DJANGO_SSL" | grep -q "SSL=True"; then
    pass "Django connects to PostgreSQL with SSL"
else
    fail "Django SSL connection check failed (output: $DJANGO_SSL)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 4: Django DATABASE_SSL_MODE is set ---"
SSL_MODE=$(docker compose exec -T web python project_root/manage.py shell -c "
from django.conf import settings
opts = settings.DATABASES['default'].get('OPTIONS', {})
print('sslmode=' + opts.get('sslmode', 'NOT_SET'))
" 2>/dev/null || echo "ERROR")
if echo "$SSL_MODE" | grep -q "sslmode=require"; then
    pass "Django DATABASE_SSL_MODE = require"
elif echo "$SSL_MODE" | grep -q "sslmode=verify"; then
    pass "Django DATABASE_SSL_MODE = verify-*"
else
    fail "Django sslmode not properly set (output: $SSL_MODE)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 5: SSL cipher/protocol version ---"
CIPHER_INFO=$(docker compose exec -T db psql "host=localhost user=postgres dbname=erechnung_ci sslmode=require" -c "SELECT version, cipher, bits FROM pg_stat_ssl WHERE pid = pg_backend_pid();" -t 2>/dev/null || echo "ERROR")
if echo "$CIPHER_INFO" | grep -qi "TLSv1\.\(2\|3\)"; then
    pass "TLS 1.2 or 1.3 in use"
else
    fail "Unexpected TLS version (output: $CIPHER_INFO)"
fi

# -------------------------------------------------------
echo ""
echo "--- Test 6: Non-SSL connection is possible but upgradable ---"
# PostgreSQL should allow non-SSL too (for pg_isready healthcheck), but prefer SSL
NOSSL_RESULT=$(docker compose exec -T db psql "host=localhost user=postgres dbname=erechnung_ci sslmode=disable" -c "SELECT 1;" -t 2>/dev/null | tr -d '[:space:]')
if [ "$NOSSL_RESULT" = "1" ]; then
    pass "Non-SSL fallback works (pg_isready compatibility)"
else
    fail "Non-SSL connection failed (healthcheck would break)"
fi

# -------------------------------------------------------
echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
