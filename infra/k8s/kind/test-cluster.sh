#!/bin/bash
# Automatisierte Tests für kind Multi-Node Cluster
# Testet Infrastruktur, Network Policies, LoadBalancer, Application Integration

set -e

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-erechnung}"
REMOTE_HOST="${REMOTE_HOST:-192.168.178.80}"
NAMESPACE="erechnung"
INGRESS_IP=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
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

# ============================================================================
# CLUSTER INFRASTRUCTURE TESTS
# ============================================================================

test_nodes_ready() {
    test_start "Cluster Nodes Ready"

    local nodes_total=$(kubectl get nodes --no-headers | wc -l)
    local nodes_ready=$(kubectl get nodes --no-headers | grep -c " Ready ")

    if [[ $nodes_total -eq 3 ]] && [[ $nodes_ready -eq 3 ]]; then
        test_pass "All 3 nodes are Ready ($nodes_ready/$nodes_total)"
        kubectl get nodes -o wide
        return 0
    else
        test_fail "Expected 3 Ready nodes, got $nodes_ready/$nodes_total"
        kubectl get nodes
        return 1
    fi
}

test_calico_running() {
    test_start "Calico Network Plugin"

    local calico_nodes=$(kubectl get pods -n kube-system -l k8s-app=calico-node --no-headers | grep -c "Running")
    local expected=3  # Should match number of nodes

    if [[ $calico_nodes -eq $expected ]]; then
        test_pass "Calico running on all $expected nodes"
        kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
        return 0
    else
        test_fail "Expected $expected calico-node pods, got $calico_nodes"
        kubectl get pods -n kube-system -l k8s-app=calico-node
        return 1
    fi
}

test_metallb_running() {
    test_start "MetalLB LoadBalancer"

    local controller=$(kubectl get pods -n metallb-system -l app=metallb,component=controller --no-headers | grep -c "Running")
    local speakers=$(kubectl get pods -n metallb-system -l app=metallb,component=speaker --no-headers | grep -c "Running")

    if [[ $controller -eq 1 ]] && [[ $speakers -eq 3 ]]; then
        test_pass "MetalLB controller (1) and speakers ($speakers) running"
        kubectl get pods -n metallb-system -o wide

        # Check IP pool configuration
        local pool=$(kubectl get ipaddresspool -n metallb-system --no-headers | wc -l)
        if [[ $pool -ge 1 ]]; then
            test_pass "IP Address Pool configured"
            kubectl get ipaddresspool -n metallb-system
        else
            test_fail "No IP Address Pool found"
        fi
        return 0
    else
        test_fail "MetalLB not fully running (controller: $controller, speakers: $speakers)"
        kubectl get pods -n metallb-system
        return 1
    fi
}

test_ingress_controller() {
    test_start "nginx Ingress Controller"

    local ingress_pods=$(kubectl get pods -n ingress-nginx -l app.kubernetes.io/component=controller --no-headers | grep -c "Running")

    if [[ $ingress_pods -ge 1 ]]; then
        test_pass "Ingress controller pod(s) running"

        # Get LoadBalancer External-IP
        INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

        if [[ -n "$INGRESS_IP" ]]; then
            test_pass "LoadBalancer has External-IP: $INGRESS_IP"
            kubectl get svc -n ingress-nginx ingress-nginx-controller
            return 0
        else
            test_fail "LoadBalancer has no External-IP (MetalLB issue?)"
            kubectl get svc -n ingress-nginx ingress-nginx-controller
            return 1
        fi
    else
        test_fail "Ingress controller not running"
        kubectl get pods -n ingress-nginx
        return 1
    fi
}

# ============================================================================
# APPLICATION TESTS
# ============================================================================

test_application_pods() {
    test_start "Application Pods Running"

    local expected_pods=("postgres" "redis" "django-web" "celery-worker" "frontend" "api-gateway")
    local all_running=true

    for pod_name in "${expected_pods[@]}"; do
        local running=$(kubectl get pods -n $NAMESPACE -l app=$pod_name --no-headers 2>/dev/null | grep -c "Running" || echo "0")
        if [[ $running -ge 1 ]]; then
            log_info "  ✓ $pod_name: $running pod(s) running"
        else
            log_error "  ✗ $pod_name: not running"
            all_running=false
        fi
    done

    if $all_running; then
        test_pass "All application pods running"
        kubectl get pods -n $NAMESPACE -o wide
        return 0
    else
        test_fail "Some application pods not running"
        kubectl get pods -n $NAMESPACE
        return 1
    fi
}

test_services_exist() {
    test_start "Kubernetes Services Configured"

    local expected_services=("postgres-service" "redis-service" "django-web-service" "frontend-service" "api-gateway-service")
    local all_exist=true

    for svc_name in "${expected_services[@]}"; do
        if kubectl get svc -n $NAMESPACE $svc_name &>/dev/null; then
            log_info "  ✓ $svc_name exists"
        else
            log_error "  ✗ $svc_name missing"
            all_exist=false
        fi
    done

    if $all_exist; then
        test_pass "All required services configured"
        kubectl get svc -n $NAMESPACE
        return 0
    else
        test_fail "Some services missing"
        kubectl get svc -n $NAMESPACE
        return 1
    fi
}

test_database_connectivity() {
    test_start "Database Connectivity (Django → Postgres)"

    local django_pod=$(kubectl get pods -n $NAMESPACE -l app=django-web --no-headers | head -1 | awk '{print $1}')

    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    # Test DB connection via Django shell
    local test_result=$(kubectl exec -n $NAMESPACE $django_pod -- python project_root/manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('OK')" 2>&1)

    if echo "$test_result" | grep -q "OK"; then
        test_pass "Django can connect to PostgreSQL"
        return 0
    else
        test_fail "Django cannot connect to PostgreSQL"
        log_error "Error: $test_result"
        return 1
    fi
}

test_redis_connectivity() {
    test_start "Redis Connectivity (Django → Redis)"

    local django_pod=$(kubectl get pods -n $NAMESPACE -l app=django-web --no-headers | head -1 | awk '{print $1}')

    if [[ -z "$django_pod" ]]; then
        test_fail "No django-web pod found"
        return 1
    fi

    # Test Redis connection via Django shell
    local test_result=$(kubectl exec -n $NAMESPACE $django_pod -- python project_root/manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok', 10); print(cache.get('test'))" 2>&1)

    if echo "$test_result" | grep -q "ok"; then
        test_pass "Django can connect to Redis"
        return 0
    else
        test_fail "Django cannot connect to Redis"
        log_error "Error: $test_result"
        return 1
    fi
}

# ============================================================================
# INGRESS/LOADBALANCER TESTS
# ============================================================================

test_ingress_http_redirect() {
    test_start "Ingress HTTP → HTTPS Redirect"

    if [[ -z "$INGRESS_IP" ]]; then
        test_fail "No Ingress IP available (run test_ingress_controller first)"
        return 1
    fi

    local response=$(ssh -o StrictHostKeyChecking=no $REMOTE_HOST "curl -s -o /dev/null -w '%{http_code}' -H 'Host: api.erechnung.local' http://$INGRESS_IP/" 2>&1)

    if [[ "$response" == "308" ]] || [[ "$response" == "301" ]]; then
        test_pass "HTTP redirects to HTTPS (Status: $response)"
        return 0
    else
        test_fail "Expected 308/301 redirect, got: $response"
        return 1
    fi
}

test_frontend_accessible() {
    test_start "Frontend Accessible via HTTPS"

    if [[ -z "$INGRESS_IP" ]]; then
        test_fail "No Ingress IP available"
        return 1
    fi

    local response=$(ssh -o StrictHostKeyChecking=no $REMOTE_HOST "curl -k -s -H 'Host: api.erechnung.local' https://$INGRESS_IP/" 2>&1)

    if echo "$response" | grep -q "eRechnung"; then
        test_pass "Frontend returns Vue.js application"
        return 0
    else
        test_fail "Frontend not accessible or wrong content"
        log_error "Response: ${response:0:200}..."
        return 1
    fi
}

test_api_accessible() {
    test_start "Django API Accessible via HTTPS"

    if [[ -z "$INGRESS_IP" ]]; then
        test_fail "No Ingress IP available"
        return 1
    fi

    local response=$(ssh -o StrictHostKeyChecking=no $REMOTE_HOST "curl -k -s -H 'Host: api.erechnung.local' https://$INGRESS_IP/api/invoices/" 2>&1)

    if echo "$response" | grep -q "Authentication credentials were not provided"; then
        test_pass "Django API responds correctly (JWT authentication required)"
        return 0
    else
        test_fail "Django API not accessible or wrong response"
        log_error "Response: $response"
        return 1
    fi
}

# ============================================================================
# SECURITY TESTS
# ============================================================================

test_pod_security_labels() {
    test_start "Pod Security Standards Labels"

    local enforce=$(kubectl get ns $NAMESPACE -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}')
    local audit=$(kubectl get ns $NAMESPACE -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/audit}')

    if [[ "$enforce" == "baseline" ]] && [[ "$audit" == "restricted" ]]; then
        test_pass "Namespace has correct Pod Security labels (enforce: baseline, audit: restricted)"
        kubectl get ns $NAMESPACE -o yaml | grep -A 5 "labels:"
        return 0
    else
        test_fail "Pod Security labels incorrect or missing (enforce: $enforce, audit: $audit)"
        return 1
    fi
}

test_network_policy_api() {
    test_start "Network Policy API Available"

    # Try to create a test network policy
    kubectl apply -f - <<EOF >/dev/null 2>&1
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-policy
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: test
  policyTypes:
  - Ingress
EOF

    if kubectl get networkpolicy -n $NAMESPACE test-policy &>/dev/null; then
        test_pass "Network Policy API is working"
        kubectl delete networkpolicy -n $NAMESPACE test-policy &>/dev/null
        return 0
    else
        test_fail "Network Policy API not working (Calico issue?)"
        return 1
    fi
}

# ============================================================================
# PERFORMANCE/RESOURCE TESTS
# ============================================================================

test_resource_usage() {
    test_start "Pod Resource Usage"

    log_info "Current resource usage:"
    kubectl top pods -n $NAMESPACE 2>&1 || {
        log_warn "metrics-server not installed (optional for production)"
        log_info "Install with: kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
    }

    test_pass "Resource usage check completed (manual review)"
    return 0
}

test_persistent_volumes() {
    test_start "Persistent Volumes Bound"

    local postgres_pvc=$(kubectl get pvc -n $NAMESPACE postgres-pvc -o jsonpath='{.status.phase}')
    local redis_pvc=$(kubectl get pvc -n $NAMESPACE redis-pvc -o jsonpath='{.status.phase}')

    if [[ "$postgres_pvc" == "Bound" ]] && [[ "$redis_pvc" == "Bound" ]]; then
        test_pass "All PVCs bound (postgres: $postgres_pvc, redis: $redis_pvc)"
        kubectl get pvc -n $NAMESPACE
        return 0
    else
        test_fail "PVC issues (postgres: $postgres_pvc, redis: $redis_pvc)"
        kubectl get pvc -n $NAMESPACE
        return 1
    fi
}

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  eRechnung Kubernetes Cluster Test Suite                     ║"
    echo "║  Multi-Node kind Cluster (192.168.178.80)                    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""

    log_info "KUBECONFIG: $KUBECONFIG"
    log_info "Remote Host: $REMOTE_HOST"
    log_info "Namespace: $NAMESPACE"
    echo ""

    # Cluster Infrastructure Tests
    test_nodes_ready || true
    test_calico_running || true
    test_metallb_running || true
    test_ingress_controller || true

    # Application Tests
    test_application_pods || true
    test_services_exist || true
    test_database_connectivity || true
    test_redis_connectivity || true

    # Ingress/LoadBalancer Tests
    test_ingress_http_redirect || true
    test_frontend_accessible || true
    test_api_accessible || true

    # Security Tests
    test_pod_security_labels || true
    test_network_policy_api || true

    # Resource Tests
    test_persistent_volumes || true
    test_resource_usage || true

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
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        return 1
    fi
}

main "$@"
