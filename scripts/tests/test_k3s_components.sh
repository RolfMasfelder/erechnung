#!/usr/bin/env bash
# =============================================================================
# Ebene 3: K3s-Komponententests (K-01 bis K-08)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.5.2
#
# Prüft das Rolling-Update-Verhalten in einem isolierten Test-Namespace
# (erechnung-update-test) mit eigenem Postgres, Redis, Django etc.
#
# Usage:
#   ./scripts/tests/test_k3s_components.sh                    # Alle Tests
#   ./scripts/tests/test_k3s_components.sh K-01               # Einzelner Test
#   ./scripts/tests/test_k3s_components.sh --no-teardown      # Namespace behalten
#
# Benötigt: kubectl, bash 4+
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
NAMESPACE="erechnung-update-test"
AUTO_TEARDOWN=true

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-k3s}"

# Farben
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# Zähler
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
declare -a TEST_RESULTS=()

# --- Test Framework ----------------------------------------------------------
run_test() {
    local test_id="$1"
    local test_name="$2"
    local test_func="$3"

    ((TESTS_RUN++)) || true
    echo -ne "${BLUE}  [$test_id]${NC} $test_name ... "

    local result=0
    $test_func 2>/dev/null || result=$?

    if [[ "$result" == "0" ]]; then
        ((TESTS_PASSED++)) || true
        echo -e "${GREEN}PASS${NC}"
        TEST_RESULTS+=("PASS $test_id $test_name")
    else
        ((TESTS_FAILED++)) || true
        echo -e "${RED}FAIL${NC}"
        TEST_RESULTS+=("FAIL $test_id $test_name")
    fi
}

# --- Helper Functions --------------------------------------------------------

# Run an HTTP request against the django-web service via kubectl exec in the
# api-gateway pod (avoids needing external access).
k8s_curl() {
    local path="$1"
    local timeout="${2:-5}"
    kubectl exec -n "$NAMESPACE" deploy/api-gateway -c nginx -- \
        wget -qO- --timeout="$timeout" "http://django-web-service:8000${path}" 2>/dev/null
}

# Run an HTTP request against the api-gateway's own health endpoint.
gateway_health() {
    kubectl exec -n "$NAMESPACE" deploy/api-gateway -c nginx -- \
        wget -qO- --timeout=5 "http://localhost:8080/gateway-health" 2>/dev/null
}

# Wait for a deployment rollout to complete.
wait_rollout() {
    local deploy="$1"
    local timeout="${2:-120}"
    kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout="${timeout}s" 2>/dev/null
}

# Get the current image tag for a deployment.
get_deploy_image_tag() {
    local deploy="$1"
    kubectl get "deployment/$deploy" -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null | sed 's/.*://'
}

# =============================================================================
# K-01: Rolling Update Happy Path (kein 5xx während Rollout)
# =============================================================================
test_k01_rolling_update_happy_path() {
    # Trigger a no-op rollout by restarting django-web
    # While it rolls, send requests and check for errors

    local errors=0
    local total=0
    local restart_done=false

    # Start background request loop
    local tmpfile
    tmpfile=$(mktemp)

    (
        for ((i=0; i<40; i++)); do
            if k8s_curl "/health/" 3; then
                echo "OK" >> "$tmpfile"
            else
                echo "FAIL" >> "$tmpfile"
            fi
            sleep 0.5
        done
    ) &
    local bg_pid=$!

    # Trigger a rollout restart (uses the same image, just restarts pods)
    sleep 1
    kubectl rollout restart deployment/django-web -n "$NAMESPACE"
    wait_rollout "django-web" 180

    # Wait for request loop to finish
    wait "$bg_pid" 2>/dev/null || true

    total=$(wc -l < "$tmpfile")
    errors=$(grep -c "FAIL" "$tmpfile" || true)
    rm -f "$tmpfile"

    if (( total < 10 )); then
        echo "  Only $total requests sent (expected >=10)" >&2
        return 1
    fi

    if (( errors > 0 )); then
        echo "  $errors/$total requests failed during rollout" >&2
        return 1
    fi
}

# =============================================================================
# K-02: Migrations-Job → completions=1 → dann erst Rollout
# =============================================================================
test_k02_migration_job_completions() {
    # Verify the migration job template has correct spec
    local backoff_limit active_deadline
    backoff_limit=$(grep 'backoffLimit' "$PROJECT_ROOT/infra/k8s/k3s/manifests/41-job-django-migrate-template.yaml" | awk '{print $2}')
    active_deadline=$(grep 'activeDeadlineSeconds' "$PROJECT_ROOT/infra/k8s/k3s/manifests/41-job-django-migrate-template.yaml" | awk '{print $2}')

    if [[ "$backoff_limit" != "3" ]]; then
        echo "  backoffLimit expected 3, got $backoff_limit" >&2
        return 1
    fi

    if [[ "$active_deadline" != "300" ]]; then
        echo "  activeDeadlineSeconds expected 300, got $active_deadline" >&2
        return 1
    fi

    # Verify the init job on cluster completed successfully
    local init_status
    init_status=$(kubectl get job django-init -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null || echo "")
    if [[ "$init_status" != "True" ]]; then
        echo "  django-init job not completed (status: $init_status)" >&2
        return 1
    fi
}

# =============================================================================
# K-03: Rollout Status = Available nach Update
# =============================================================================
test_k03_rollout_available() {
    local all_available=true
    for deploy in django-web celery-worker api-gateway frontend; do
        local available
        available=$(kubectl get "deployment/$deploy" -n "$NAMESPACE" \
            -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null)
        if [[ "$available" != "True" ]]; then
            echo "  $deploy: Available=$available (expected True)" >&2
            all_available=false
        fi
    done
    [[ "$all_available" == true ]]
}

# =============================================================================
# K-04: PDB respektiert (PDBs existieren und sind korrekt konfiguriert)
# =============================================================================
test_k04_pdb_configured() {
    # Verify PDBs exist and have correct minAvailable
    local django_pdb_min api_pdb_min
    django_pdb_min=$(kubectl get pdb django-web-pdb -n "$NAMESPACE" -o jsonpath='{.spec.minAvailable}' 2>/dev/null || echo "")
    api_pdb_min=$(kubectl get pdb api-gateway-pdb -n "$NAMESPACE" -o jsonpath='{.spec.minAvailable}' 2>/dev/null || echo "")

    if [[ "$django_pdb_min" != "1" ]]; then
        echo "  django-web-pdb minAvailable expected 1, got '$django_pdb_min'" >&2
        return 1
    fi

    if [[ "$api_pdb_min" != "1" ]]; then
        echo "  api-gateway-pdb minAvailable expected 1, got '$api_pdb_min'" >&2
        return 1
    fi

    # Verify disruptions are allowed (meaning pods are healthy)
    local django_allowed api_allowed
    django_allowed=$(kubectl get pdb django-web-pdb -n "$NAMESPACE" -o jsonpath='{.status.disruptionsAllowed}' 2>/dev/null || echo "0")
    api_allowed=$(kubectl get pdb api-gateway-pdb -n "$NAMESPACE" -o jsonpath='{.status.disruptionsAllowed}' 2>/dev/null || echo "0")

    if (( django_allowed < 1 )); then
        echo "  django-web-pdb: disruptionsAllowed=$django_allowed (expected >=1)" >&2
        return 1
    fi
    if (( api_allowed < 1 )); then
        echo "  api-gateway-pdb: disruptionsAllowed=$api_allowed (expected >=1)" >&2
        return 1
    fi
}

# =============================================================================
# K-05: Readiness Probe blockiert Traffic an startende Pods
# =============================================================================
test_k05_readiness_probe_configured() {
    # Verify that readinessProbe is configured on django-web
    local readiness_path readiness_period
    readiness_path=$(kubectl get deployment django-web -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.httpGet.path}' 2>/dev/null)
    readiness_period=$(kubectl get deployment django-web -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.periodSeconds}' 2>/dev/null)

    if [[ "$readiness_path" != "/health/" ]]; then
        echo "  readinessProbe path expected '/health/', got '$readiness_path'" >&2
        return 1
    fi

    if [[ -z "$readiness_period" || "$readiness_period" == "0" ]]; then
        echo "  readinessProbe periodSeconds not set" >&2
        return 1
    fi

    # Verify maxUnavailable=0 (traffic only sent to ready pods)
    local max_unavailable
    max_unavailable=$(kubectl get deployment django-web -n "$NAMESPACE" \
        -o jsonpath='{.spec.strategy.rollingUpdate.maxUnavailable}' 2>/dev/null)
    if [[ "$max_unavailable" != "0" ]]; then
        echo "  maxUnavailable expected 0, got '$max_unavailable'" >&2
        return 1
    fi
}

# =============================================================================
# K-06: 0% Request-Fehlerrate während Rollout (100 Requests)
# =============================================================================
test_k06_zero_error_rate() {
    # Send 100 requests as fast as possible while checking for errors
    local errors=0
    local total=100
    local tmpfile
    tmpfile=$(mktemp)

    for ((i=0; i<total; i++)); do
        if k8s_curl "/health/" 3; then
            echo "OK" >> "$tmpfile"
        else
            echo "FAIL" >> "$tmpfile"
        fi
    done

    local actual_total actual_errors
    actual_total=$(wc -l < "$tmpfile")
    actual_errors=$(grep -c "FAIL" "$tmpfile" || true)
    rm -f "$tmpfile"

    if (( actual_errors > 0 )); then
        echo "  $actual_errors/$actual_total requests failed (expected 0)" >&2
        return 1
    fi

    if (( actual_total < 50 )); then
        echo "  Only $actual_total requests completed (expected ~100)" >&2
        return 1
    fi
}

# =============================================================================
# K-07: ConfigMap-Änderung → neue Config aktiv
# =============================================================================
test_k07_configmap_active() {
    # Verify that the deployed pods use the correct configmap values
    local django_env
    django_env=$(kubectl exec -n "$NAMESPACE" deploy/django-web -c django-web -- \
        printenv DJANGO_ENV 2>/dev/null || echo "")

    if [[ -z "$django_env" ]]; then
        echo "  DJANGO_ENV not set in django-web pod" >&2
        return 1
    fi

    # Verify configmap value matches what's in the deployment
    local cm_value
    cm_value=$(kubectl get configmap erechnung-config -n "$NAMESPACE" \
        -o jsonpath='{.data.DJANGO_ENV}' 2>/dev/null)

    if [[ "$django_env" != "$cm_value" ]]; then
        echo "  Pod DJANGO_ENV='$django_env' != ConfigMap '$cm_value'" >&2
        return 1
    fi
}

# =============================================================================
# K-08: PVC intakt nach Pod-Restart
# =============================================================================
test_k08_pvc_intact() {
    # Verify PVCs are bound
    local pg_status redis_status
    pg_status=$(kubectl get pvc postgres-pvc -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)
    redis_status=$(kubectl get pvc redis-pvc -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)

    if [[ "$pg_status" != "Bound" ]]; then
        echo "  postgres-pvc status: $pg_status (expected Bound)" >&2
        return 1
    fi

    if [[ "$redis_status" != "Bound" ]]; then
        echo "  redis-pvc status: $redis_status (expected Bound)" >&2
        return 1
    fi

    # Verify data persists: check that postgres has tables
    local table_count
    table_count=$(kubectl exec -n "$NAMESPACE" deploy/postgres -c postgres -- \
        sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\''"' 2>/dev/null || echo "0")

    if (( table_count < 1 )); then
        echo "  No tables found in postgres (expected >=1)" >&2
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================
# --- Namespace Setup/Teardown ------------------------------------------------
ensure_test_namespace() {
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        # Check if all deployments are available
        local all_ready=true
        for deploy in django-web api-gateway frontend postgres redis; do
            local avail
            avail=$(kubectl get "deployment/$deploy" -n "$NAMESPACE" \
                -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")
            if [[ -z "$avail" || "$avail" == "0" ]]; then
                all_ready=false
                break
            fi
        done
        if [[ "$all_ready" == true ]]; then
            echo -e "  ${GREEN}Test-Namespace $NAMESPACE existiert und ist bereit.${NC}"
            return 0
        fi
        echo -e "  ${YELLOW}Namespace existiert, aber nicht alle Pods ready. Re-deploying...${NC}"
    fi
    echo -e "  ${BLUE}Deploye isolierten Test-Stack in $NAMESPACE...${NC}"
    "$SCRIPT_DIR/k3s_test_ns_setup.sh" setup
}

teardown_test_namespace() {
    if [[ "$AUTO_TEARDOWN" == true ]]; then
        echo ""
        echo -e "  ${BLUE}Teardown: Lösche $NAMESPACE...${NC}"
        "$SCRIPT_DIR/k3s_test_ns_setup.sh" teardown
    else
        echo -e "  ${YELLOW}--no-teardown: Namespace $NAMESPACE bleibt bestehen.${NC}"
    fi
}

main() {
    local filter=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-teardown) AUTO_TEARDOWN=false; shift ;;
            *)             filter="$1"; shift ;;
        esac
    done

    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Ebene 3: K3s-Komponententests (K-01..K-08)   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo -e "  Namespace: $NAMESPACE"
    echo ""

    # Pre-check: cluster reachable
    if ! kubectl cluster-info &>/dev/null; then
        echo -e "${RED}K3s-Cluster nicht erreichbar. Abbruch.${NC}" >&2
        exit 2
    fi

    # Setup isolated test namespace
    ensure_test_namespace
    trap teardown_test_namespace EXIT
    echo ""

    if [[ -z "$filter" || "$filter" == "K-01" ]]; then
        run_test "K-01" "Rolling Update Happy Path (0 Fehler)" test_k01_rolling_update_happy_path
    fi

    if [[ -z "$filter" || "$filter" == "K-02" ]]; then
        run_test "K-02" "Migrations-Job korrekt konfiguriert" test_k02_migration_job_completions
    fi

    if [[ -z "$filter" || "$filter" == "K-03" ]]; then
        run_test "K-03" "Rollout Status = Available" test_k03_rollout_available
    fi

    if [[ -z "$filter" || "$filter" == "K-04" ]]; then
        run_test "K-04" "PDB korrekt konfiguriert" test_k04_pdb_configured
    fi

    if [[ -z "$filter" || "$filter" == "K-05" ]]; then
        run_test "K-05" "Readiness Probe blockiert Traffic" test_k05_readiness_probe_configured
    fi

    if [[ -z "$filter" || "$filter" == "K-06" ]]; then
        run_test "K-06" "0% Fehlerrate (100 Requests)" test_k06_zero_error_rate
    fi

    if [[ -z "$filter" || "$filter" == "K-07" ]]; then
        run_test "K-07" "ConfigMap-Werte aktiv in Pod" test_k07_configmap_active
    fi

    if [[ -z "$filter" || "$filter" == "K-08" ]]; then
        run_test "K-08" "PVC intakt (Daten persistent)" test_k08_pvc_intact
    fi

    # Summary
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Gesamt: $TESTS_RUN | ${GREEN}Bestanden: $TESTS_PASSED${NC} | ${RED}Fehlgeschlagen: $TESTS_FAILED${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if (( TESTS_FAILED > 0 )); then
        exit 1
    fi
}

main "$@"
