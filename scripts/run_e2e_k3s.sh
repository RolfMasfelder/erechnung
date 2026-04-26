#!/bin/bash

# E2E Tests gegen k3s Cluster (Smoke Tests / Production Validation)
# Testet das deployed System auf 192.168.178.80 (k3s) mit LoadBalancer IP 192.168.178.200
# Nutzt E2E Container für Tests (keine Host-Dependencies)

set -e

# Konfiguration
K3S_HOST="192.168.178.200"
K3S_HOSTNAME="erechnung.local"
K3S_URL="https://${K3S_HOSTNAME}"
CURL_RESOLVE="--resolve ${K3S_HOSTNAME}:443:${K3S_HOST} --resolve ${K3S_HOSTNAME}:80:${K3S_HOST}"
TEST_USER="testuser"
TEST_PASS="testpass123"
MIN_INVOICES=60  # Minimum für Pagination-Tests
E2E_NAMESPACE="${E2E_NAMESPACE:-erechnung}"
E2E_IMAGE="${E2E_IMAGE:-mcr.microsoft.com/playwright:v1.59.1-noble}"
E2E_WORKERS="${E2E_WORKERS:-1}"
E2E_RETRIES="${E2E_RETRIES:-2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "════════════════════════════════════════════════════════════"
echo "  E2E Smoke Tests - k3s Cluster"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Target: $K3S_URL"
echo "Test User: $TEST_USER"
echo ""

# Funktion: HTTP Request mit Curl (für Health & Auth Checks)
# Nutzt --resolve für erechnung.local → MetalLB IP und -k für self-signed Cert
check_http() {
    local url=$1
    local max_retries=${2:-3}
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if curl -s -f -k -L -m 5 $CURL_RESOLVE "$url" > /dev/null 2>&1; then
            return 0
        fi
        retry=$((retry + 1))
        [ $retry -lt $max_retries ] && sleep 2
    done
    return 1
}

# 1. Cluster Erreichbarkeit prüfen
echo "→ [1/4] Checking k3s cluster connectivity..."
if ! check_http "$K3S_URL/health" 5; then
    echo "  ❌ FEHLER: k3s Cluster nicht erreichbar!"
    echo ""
    echo "  Mögliche Ursachen:"
    echo "  - k3s Cluster läuft nicht: ssh rolf@192.168.178.80 'sudo k3s kubectl get pods -n erechnung'"
    echo "  - LoadBalancer IP nicht zugewiesen: kubectl get svc -n erechnung"
    echo "  - Application nicht deployed: kubectl get ingress -n erechnung"
    echo ""
    exit 1
fi
echo "  ✓ Cluster erreichbar"

# 2. Test User Authentication prüfen
echo ""
echo "→ [2/4] Checking test user authentication..."
AUTH_RESPONSE=$(curl -s -k -L $CURL_RESOLVE -X POST "$K3S_URL/api/auth/token/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}" \
    -w "\n%{http_code}" 2>/dev/null || echo "000")

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "  ❌ FEHLER: Test User Authentication fehlgeschlagen! (HTTP $HTTP_CODE)"
    echo ""
    echo "  Test User muss existieren: $TEST_USER / $TEST_PASS"
    echo ""
    echo "  Fix (in k3s Pod):"
    echo "  kubectl exec -n erechnung deploy/django-web -- python project_root/manage.py shell -c \\"
    echo "    from django.contrib.auth import get_user_model; \\"
    echo "    User = get_user_model(); \\"
    echo "    User.objects.filter(username='$TEST_USER').exists() or \\"
    echo "    User.objects.create_user('$TEST_USER', 'test@example.com', '$TEST_PASS')\""
    echo ""
    exit 1
fi

# Token extrahieren
TOKEN=$(echo "$AUTH_BODY" | grep -o '"access":"[^"]*' | sed 's/"access":"//' || echo "")
if [ -z "$TOKEN" ]; then
    echo "  ❌ FEHLER: Kein JWT Token erhalten!"
    echo "  Response: $AUTH_BODY"
    exit 1
fi
echo "  ✓ Authentication erfolgreich (Token erhalten)"

# 3. Test-Daten prüfen (Invoice Count)
echo ""
echo "→ [3/4] Checking test data (invoices)..."
INVOICE_RESPONSE=$(curl -s -k -L $CURL_RESOLVE "$K3S_URL/api/invoices/?page=1&page_size=1" \
    -H "Authorization: Bearer $TOKEN" \
    -w "\n%{http_code}" 2>/dev/null || echo "000")

HTTP_CODE=$(echo "$INVOICE_RESPONSE" | tail -n1)
INVOICE_BODY=$(echo "$INVOICE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "  ❌ FEHLER: Invoice API nicht erreichbar! (HTTP $HTTP_CODE)"
    exit 1
fi

INVOICE_COUNT=$(echo "$INVOICE_BODY" | grep -o '"count":[0-9]*' | sed 's/"count"://' || echo "0")
echo "  Found: $INVOICE_COUNT invoices (minimum required: $MIN_INVOICES)"

if [ "$INVOICE_COUNT" -lt "$MIN_INVOICES" ]; then
    echo "  ⚠️  WARNUNG: Nicht genug Test-Daten für alle Tests!"
    echo ""
    echo "  Pagination-Tests benötigen mindestens $MIN_INVOICES Invoices."
    echo ""
    echo "  Fix (in k3s - django-init Job sollte das gemacht haben):"
    echo "  kubectl logs -n erechnung job/django-init"
    echo ""
    echo "  Manual fix (Django Shell in k3s):"
    echo "  kubectl exec -n erechnung deploy/django-web -- python project_root/manage.py create_test_data --count=50"
    echo ""
    read -p "  Trotzdem fortfahren? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "  ✓ Sufficient test data available"
fi

# 4. E2E Tests ausführen (IM k3s Cluster)
echo ""
echo "→ [4/4] Running Playwright E2E Tests in k3s pod..."
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Playwright Tests (in-cluster Runner gegen k3s)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Test URL: $K3S_URL"
echo "Browser: Chromium (mcr.microsoft.com/playwright)"
echo "Namespace: $E2E_NAMESPACE"
echo "Mode: CI=true, workers=$E2E_WORKERS, retries=$E2E_RETRIES"
echo ""

E2E_RUNNER_POD="e2e-runner-$(date +%s)"
ARTIFACT_DIR="$PROJECT_ROOT/test-artifacts/playwright-k3s-$(date +%Y%m%d-%H%M%S)"

cleanup_runner() {
        echo ""
        echo "Cleaning up E2E runner pod..."
        kubectl delete pod "$E2E_RUNNER_POD" -n "$E2E_NAMESPACE" --ignore-not-found --wait=false > /dev/null 2>&1 || true
}
trap cleanup_runner EXIT

echo "Starting temporary runner pod: $E2E_RUNNER_POD"
kubectl apply -n "$E2E_NAMESPACE" -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $E2E_RUNNER_POD
  namespace: $E2E_NAMESPACE
spec:
  restartPolicy: Never
  hostAliases:
  - ip: "$K3S_HOST"
    hostnames:
    - "$K3S_HOSTNAME"
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  volumes:
  - name: workspace
    emptyDir: {}
  containers:
  - name: $E2E_RUNNER_POD
    image: $E2E_IMAGE
    command: ["sleep", "3600"]
    volumeMounts:
    - name: workspace
      mountPath: /app
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
EOF

echo "⏳ Waiting for runner pod readiness..."
kubectl wait --for=condition=Ready pod/"$E2E_RUNNER_POD" -n "$E2E_NAMESPACE" --timeout=180s

echo "Copying frontend workspace into runner pod..."
kubectl cp "$PROJECT_ROOT/frontend/." "$E2E_NAMESPACE/$E2E_RUNNER_POD:/app" 2>/dev/null

echo "Installing npm dependencies in runner pod..."
kubectl exec -n "$E2E_NAMESPACE" "$E2E_RUNNER_POD" -- bash -lc "cd /app && npm ci"

PW_EXTRA_ARGS=""
if [ "$#" -gt 0 ]; then
        PW_EXTRA_ARGS=$(printf "%q " "$@")
fi

set +e
kubectl exec -n "$E2E_NAMESPACE" "$E2E_RUNNER_POD" -- \
    bash -lc "cd /app && CI=true PLAYWRIGHT_BASE_URL='$K3S_URL' NODE_TLS_REJECT_UNAUTHORIZED=0 npm run test:e2e -- --workers=$E2E_WORKERS --retries=$E2E_RETRIES $PW_EXTRA_ARGS"
TEST_EXIT_CODE=$?
set -e

mkdir -p "$ARTIFACT_DIR"
echo "Collecting Playwright artifacts to: $ARTIFACT_DIR"
kubectl cp "$E2E_NAMESPACE/$E2E_RUNNER_POD:/app/playwright-report" "$ARTIFACT_DIR/playwright-report" > /dev/null 2>&1 || true
kubectl cp "$E2E_NAMESPACE/$E2E_RUNNER_POD:/app/test-results" "$ARTIFACT_DIR/test-results" > /dev/null 2>&1 || true

# Ergebnis
echo ""
echo "════════════════════════════════════════════════════════════"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "  ✅ All E2E tests passed against k3s cluster!"
    echo ""
    echo "  Production deployment validated successfully! 🚀"
else
    echo "  ❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo ""
    echo "  Dies sind Smoke Tests gegen Production-Deployment."
    echo "  Fehler bedeuten, dass das k3s Deployment nicht korrekt funktioniert!"
fi
echo "════════════════════════════════════════════════════════════"
echo ""
echo "View detailed results:"
echo "  ls -la $ARTIFACT_DIR"
echo ""
echo "Check k3s cluster status:"
echo "  kubectl get pods -n erechnung"
echo "  kubectl logs -n erechnung deploy/django-web"
echo "  kubectl logs -n erechnung deploy/frontend"
echo ""

exit $TEST_EXIT_CODE
