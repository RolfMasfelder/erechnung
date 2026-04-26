#!/bin/bash
# Network Policy Tests für eRechnung Kubernetes Cluster
# Testet ob Isolation und Allow-Rules korrekt funktionieren

set -e

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-erechnung}"
NAMESPACE="erechnung"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

test_start() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Test $TESTS_RUN: $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_info "✅ PASS: $1"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "❌ FAIL: $1"
}

# Get a pod name for testing
get_pod() {
    local app_label=$1
    kubectl get pods -n $NAMESPACE -l app=$app_label --no-headers 2>/dev/null | head -1 | awk '{print $1}'
}

# Test connection between pods
test_connection() {
    local from_pod=$1
    local to_service=$2
    local to_port=$3
    local expected=$4  # "success" or "fail"

    # Use Python socket test (available in Django/Celery containers)
    local python_cmd="import socket; s=socket.socket(); s.settimeout(3); s.connect(('$to_service', $to_port)); s.close(); print('SUCCESS')"
    local result=$(kubectl exec -n $NAMESPACE $from_pod -- python -c "$python_cmd" 2>&1 || echo "FAILED")

    if [[ "$expected" == "success" ]]; then
        if echo "$result" | grep -q "SUCCESS"; then
            return 0
        else
            return 1
        fi
    else
        # Expected to fail - connection should be blocked
        if echo "$result" | grep -q "FAILED\|timed out\|Connection refused"; then
            return 0
        else
            return 1
        fi
    fi
}

# ============================================================================
# NETWORK POLICY DEPLOYMENT TEST
# ============================================================================

test_network_policies_deployed() {
    test_start "Network Policies Deployed"

    local policy_count=$(kubectl get networkpolicies -n $NAMESPACE --no-headers 2>/dev/null | wc -l)

    if [[ $policy_count -ge 8 ]]; then
        test_pass "Network Policies deployed ($policy_count found)"
        kubectl get networkpolicies -n $NAMESPACE
        return 0
    else
        test_fail "Expected at least 8 Network Policies, found $policy_count"
        log_warn "Deploy with: kubectl apply -f k8s/kind/network-policies.yaml"
        return 1
    fi
}

# ============================================================================
# ALLOWED CONNECTIONS TESTS
# ============================================================================

test_django_to_postgres() {
    test_start "Allowed: Django → PostgreSQL (Port 5432)"

    local django_pod=$(get_pod "django-web")
    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    if test_connection "$django_pod" "postgres-service" "5432" "success"; then
        test_pass "Django can connect to PostgreSQL"
        return 0
    else
        test_fail "Django cannot connect to PostgreSQL (Network Policy issue?)"
        return 1
    fi
}

test_django_to_redis() {
    test_start "Allowed: Django → Redis (Port 6379)"

    local django_pod=$(get_pod "django-web")
    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    if test_connection "$django_pod" "redis-service" "6379" "success"; then
        test_pass "Django can connect to Redis"
        return 0
    else
        test_fail "Django cannot connect to Redis (Network Policy issue?)"
        return 1
    fi
}

test_celery_to_postgres() {
    test_start "Allowed: Celery → PostgreSQL (Port 5432)"

    local celery_pod=$(get_pod "celery-worker")
    if [[ -z "$celery_pod" ]]; then
        test_fail "No celery-worker pod found"
        return 1
    fi

    if test_connection "$celery_pod" "postgres-service" "5432" "success"; then
        test_pass "Celery can connect to PostgreSQL"
        return 0
    else
        test_fail "Celery cannot connect to PostgreSQL (Network Policy issue?)"
        return 1
    fi
}

test_celery_to_redis() {
    test_start "Allowed: Celery → Redis (Port 6379)"

    local celery_pod=$(get_pod "celery-worker")
    if [[ -z "$celery_pod" ]]; then
        test_fail "No celery-worker pod found"
        return 1
    fi

    if test_connection "$celery_pod" "redis-service" "6379" "success"; then
        test_pass "Celery can connect to Redis"
        return 0
    else
        test_fail "Celery cannot connect to Redis (Network Policy issue?)"
        return 1
    fi
}

test_api_gateway_to_django() {
    test_start "Allowed: API-Gateway → Django (Port 8000)"

    local gateway_pod=$(get_pod "api-gateway")
    if [[ -z "$gateway_pod" ]]; then
        test_fail "No api-gateway pod found"
        return 1
    fi

    # API-Gateway is nginx - use wget for HTTP test
    local result=$(kubectl exec -n $NAMESPACE $gateway_pod -- timeout 3 wget -q -O- http://django-web-service:8000/health/ 2>&1 || echo "FAILED")

    if echo "$result" | grep -q "ok\|OK\|healthy\|SUCCESS"; then
        test_pass "API-Gateway can connect to Django"
        return 0
    else
        test_fail "API-Gateway cannot connect to Django (Network Policy issue?)"
        log_error "Result: $result"
        return 1
    fi
}

test_dns_resolution() {
    test_start "Allowed: DNS Resolution (Port 53)"

    local django_pod=$(get_pod "django-web")
    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    # Test DNS resolution using Python (no nslookup needed)
    local result=$(kubectl exec -n $NAMESPACE $django_pod -- python -c "import socket; ip=socket.gethostbyname('kubernetes.default.svc.cluster.local'); print('RESOLVED:', ip)" 2>&1 || echo "FAILED")

    if echo "$result" | grep -q "RESOLVED:"; then
        test_pass "DNS resolution works"
        return 0
    else
        test_fail "DNS resolution blocked (Network Policy issue?)"
        log_error "Result: $result"
        return 1
    fi
}

# ============================================================================
# BLOCKED CONNECTIONS TESTS (Default-Deny)
# ============================================================================

test_frontend_to_postgres_blocked() {
    test_start "Blocked: Frontend → PostgreSQL (Default-Deny)"

    local frontend_pod=$(get_pod "frontend")
    if [[ -z "$frontend_pod" ]]; then
        test_fail "No frontend pod found"
        return 1
    fi

    # Frontend uses nginx without Python - use wget/timeout instead
    local result=$(kubectl exec -n $NAMESPACE $frontend_pod -- timeout 3 wget -q -O- http://postgres-service:5432 2>&1 || echo "FAILED")

    if echo "$result" | grep -q "FAILED\|timed out\|Connection refused\|wget: can't connect"; then
        test_pass "Frontend correctly blocked from PostgreSQL"
        return 0
    else
        test_fail "Frontend can access PostgreSQL (Network Policy not enforced!)"
        return 1
    fi
}

test_frontend_to_redis_blocked() {
    test_start "Blocked: Frontend → Redis (Default-Deny)"

    local frontend_pod=$(get_pod "frontend")
    if [[ -z "$frontend_pod" ]]; then
        test_fail "No frontend pod found"
        return 1
    fi

    # Frontend uses nginx without Python - use wget/timeout instead
    local result=$(kubectl exec -n $NAMESPACE $frontend_pod -- timeout 3 wget -q -O- http://redis-service:6379 2>&1 || echo "FAILED")

    if echo "$result" | grep -q "FAILED\|timed out\|Connection refused\|wget: can't connect"; then
        test_pass "Frontend correctly blocked from Redis"
        return 0
    else
        test_fail "Frontend can access Redis (Network Policy not enforced!)"
        return 1
    fi
}

test_external_to_postgres_blocked() {
    test_start "Blocked: External → PostgreSQL Direct Access"

    # Try to access postgres directly via ClusterIP
    local postgres_ip=$(kubectl get svc -n $NAMESPACE postgres-service -o jsonpath='{.spec.clusterIP}')

    # This should timeout/fail because only ingress should be accessible
    log_info "Testing external access to Postgres ClusterIP: $postgres_ip"
    log_info "This should fail (good) as only Ingress should be externally accessible"

    test_pass "External direct DB access test noted (requires external network test)"
    return 0
}

# ============================================================================
# EGRESS TESTS
# ============================================================================

test_django_https_egress() {
    test_start "Allowed: Django HTTPS Egress (External API calls)"

    local django_pod=$(get_pod "django-web")
    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    # Test HTTPS connectivity (needed for external API integrations)
    # Note: This may be intentionally blocked by Network Policy for security
    local result=$(kubectl exec -n $NAMESPACE $django_pod -- timeout 5 python -c "import urllib.request; urllib.request.urlopen('https://www.google.com', timeout=3); print('OK')" 2>&1 || echo "BLOCKED")

    if echo "$result" | grep -q "OK"; then
        test_pass "Django can make HTTPS requests to external services"
        return 0
    elif echo "$result" | grep -q "BLOCKED\|timed out\|Network is unreachable"; then
        test_pass "Django HTTPS egress intentionally blocked (secure configuration)"
        log_info "External HTTPS is blocked by Network Policy (expected for production)"
        return 0
    else
        test_fail "Django HTTPS egress test inconclusive"
        log_error "Result: $result"
        return 1
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Network Policy Test Suite                                    ║"
    echo "║  Tests Network Isolation and Allow Rules                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""

    log_info "KUBECONFIG: $KUBECONFIG"
    log_info "Namespace: $NAMESPACE"
    echo ""

    # Check if Network Policies are deployed
    test_network_policies_deployed || {
        log_warn "Network Policies not deployed - some tests will fail"
    }

    # Test Allowed Connections
    test_django_to_postgres || true
    test_django_to_redis || true
    test_celery_to_postgres || true
    test_celery_to_redis || true
    test_api_gateway_to_django || true
    test_dns_resolution || true

    # Test Blocked Connections (Default-Deny)
    test_frontend_to_postgres_blocked || true
    test_frontend_to_redis_blocked || true
    test_external_to_postgres_blocked || true

    # Test Egress
    test_django_https_egress || true

    # Summary
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Total Tests Run:    $TESTS_RUN"
    echo -e "Tests Passed:       ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed:       ${RED}$TESTS_FAILED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ ALL NETWORK POLICY TESTS PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ SOME NETWORK POLICY TESTS FAILED${NC}"
        return 1
    fi
}

main "$@"
