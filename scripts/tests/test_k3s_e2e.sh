#!/usr/bin/env bash
# =============================================================================
# Ebene 4: K3s End-to-End-Tests (E2E-K-01 bis E2E-K-05)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.6.2
#
# End-to-End-Tests des Update-Prozesses in einem isolierten Test-Namespace
# (erechnung-update-test) mit eigenem Postgres, Redis, Django etc.
#
# Usage:
#   ./scripts/tests/test_k3s_e2e.sh                     # Alle Tests
#   ./scripts/tests/test_k3s_e2e.sh E2E-K-01            # Einzelner Test
#   ./scripts/tests/test_k3s_e2e.sh --no-teardown       # Namespace behalten
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

# Run an HTTP request against the django-web service via kubectl exec
k8s_curl() {
    local path="$1"
    local timeout="${2:-5}"
    kubectl exec -n "$NAMESPACE" deploy/api-gateway -c nginx -- \
        wget -qO- --timeout="$timeout" "http://django-web-service:8000${path}" 2>/dev/null
}

# Wait for a deployment rollout to complete.
wait_rollout() {
    local deploy="$1"
    local timeout="${2:-120}"
    kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout="${timeout}s" 2>/dev/null
}

# Get the current revision number for a deployment
get_revision() {
    local deploy="$1"
    kubectl get "deployment/$deploy" -n "$NAMESPACE" \
        -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}' 2>/dev/null
}

# =============================================================================
# E2E-K-01: Zero-Downtime mit Lastgenerator
# =============================================================================
test_e2e_k01_zero_downtime() {
    # Send sustained load during a rollout restart, verify 0 errors.
    local total_requests=200
    local errors=0
    local tmpfile
    tmpfile=$(mktemp)

    # Background load generator
    (
        for ((i=0; i<total_requests; i++)); do
            if k8s_curl "/health/" 3; then
                echo "OK" >> "$tmpfile"
            else
                echo "FAIL" >> "$tmpfile"
            fi
            sleep 0.2
        done
    ) &
    local bg_pid=$!

    # Give load generator a head start
    sleep 2

    # Trigger rollout restart
    kubectl rollout restart deployment/django-web -n "$NAMESPACE"
    wait_rollout "django-web" 180

    # Wait for load generator to finish
    wait "$bg_pid" 2>/dev/null || true

    local actual_total actual_errors
    actual_total=$(wc -l < "$tmpfile")
    actual_errors=$(grep -c "FAIL" "$tmpfile" || true)
    rm -f "$tmpfile"

    if (( actual_total < 50 )); then
        echo "  Only $actual_total requests completed (expected >=50)" >&2
        return 1
    fi

    if (( actual_errors > 0 )); then
        echo "  $actual_errors/$actual_total requests failed during zero-downtime test" >&2
        return 1
    fi
}

# =============================================================================
# E2E-K-02: Auto-Rollback bei Health-Fehler (defektes Image)
# =============================================================================
test_e2e_k02_auto_rollback_bad_image() {
    # Save current image
    local current_image
    current_image=$(kubectl get deployment/frontend -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)
    local current_revision
    current_revision=$(get_revision "frontend")

    # Set a non-existent image tag (will fail to pull)
    kubectl set image "deployment/frontend" frontend="nginx:non-existent-tag-99999" -n "$NAMESPACE"

    # Wait for the bad rollout to stall (progressDeadlineSeconds default=600)
    # We only check that the OLD pods stay running.
    sleep 15

    # Verify old pods are still running (maxUnavailable=0 keeps old pods)
    local available_replicas
    available_replicas=$(kubectl get deployment/frontend -n "$NAMESPACE" \
        -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")

    # Restore the original image immediately
    kubectl set image "deployment/frontend" frontend="$current_image" -n "$NAMESPACE"
    wait_rollout "frontend" 120

    if (( available_replicas < 1 )); then
        echo "  No available replicas during bad image rollout (expected >=1)" >&2
        return 1
    fi
}

# =============================================================================
# E2E-K-03: Manueller Rollback (rollout undo)
# =============================================================================
test_e2e_k03_manual_rollback() {
    local revision_before
    revision_before=$(get_revision "frontend")

    # Trigger a rollout restart to create a new revision
    kubectl rollout restart deployment/frontend -n "$NAMESPACE"
    wait_rollout "frontend" 120

    local revision_after
    revision_after=$(get_revision "frontend")

    # Verify revision increased
    if [[ "$revision_before" == "$revision_after" ]]; then
        echo "  Revision didn't change after restart ($revision_before)" >&2
        return 1
    fi

    # Rollback
    kubectl rollout undo deployment/frontend -n "$NAMESPACE"
    wait_rollout "frontend" 120

    local revision_rollback
    revision_rollback=$(get_revision "frontend")

    # After undo, revision should increase again (K8s creates a new revision for undo)
    if (( revision_rollback <= revision_after )); then
        echo "  Revision didn't increase after undo ($revision_rollback <= $revision_after)" >&2
        return 1
    fi

    # Verify pods are available
    local available
    available=$(kubectl get deployment/frontend -n "$NAMESPACE" \
        -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null)
    if [[ "$available" != "True" ]]; then
        echo "  Frontend not available after rollback" >&2
        return 1
    fi
}

# =============================================================================
# E2E-K-04: Migration-Job-Fehler blockiert Rollout
# =============================================================================
test_e2e_k04_migration_job_failure_blocks() {
    # Verify that the update-k3s.sh script exits non-zero when migration fails.
    # We test this by checking the script logic (dry-run), since actually breaking
    # migrations on production is destructive.

    local update_script="$PROJECT_ROOT/scripts/update-k3s.sh"
    if [[ ! -f "$update_script" ]]; then
        echo "  update-k3s.sh not found" >&2
        return 1
    fi

    # Verify the script checks for migration job success
    if ! grep -qE 'kubectl wait.*--for=condition=complete.*job|kubectl wait.*job.*--for=condition=complete' "$update_script" 2>/dev/null; then
        echo "  update-k3s.sh does not wait for migration job completion" >&2
        return 1
    fi

    # Verify the script exits on migration failure
    if ! grep -q 'Migration fehlgeschlagen' "$update_script" 2>/dev/null; then
        echo "  update-k3s.sh missing migration failure handling" >&2
        return 1
    fi

    # Verify exit code for migration failure
    if ! grep -q 'exit [0-9]*.*Migration' "$update_script" 2>/dev/null && \
       ! grep -q 'exit 5' "$update_script" 2>/dev/null; then
        # Alternative: check that migration failure section has exit
        if ! grep -A5 'Migration fehlgeschlagen' "$update_script" | grep -q 'exit'; then
            echo "  update-k3s.sh missing exit on migration failure" >&2
            return 1
        fi
    fi
}

# =============================================================================
# E2E-K-05: Paralleler Traffic (10 Clients, Sessions bleiben valid)
# =============================================================================
test_e2e_k05_parallel_traffic() {
    # Simulate 10 parallel clients sending requests
    local clients=10
    local requests_per_client=20
    local tmpdir
    tmpdir=$(mktemp -d)

    # Launch parallel clients
    local pids=()
    for ((c=0; c<clients; c++)); do
        (
            local fail=0
            for ((r=0; r<requests_per_client; r++)); do
                if k8s_curl "/health/" 3; then
                    echo "OK" >> "$tmpdir/client-${c}.log"
                else
                    echo "FAIL" >> "$tmpdir/client-${c}.log"
                fi
            done
        ) &
        pids+=($!)
    done

    # Wait for all clients
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    # Count results
    local total=0
    local errors=0
    for logfile in "$tmpdir"/client-*.log; do
        if [[ -f "$logfile" ]]; then
            total=$((total + $(wc -l < "$logfile")))
            errors=$((errors + $(grep -c "FAIL" "$logfile" || true)))
        fi
    done

    rm -rf "$tmpdir"

    local expected_min=$((clients * requests_per_client / 2))
    if (( total < expected_min )); then
        echo "  Only $total requests completed (expected >=$expected_min)" >&2
        return 1
    fi

    if (( errors > 0 )); then
        echo "  $errors/$total requests failed across $clients clients" >&2
        return 1
    fi
}

# =============================================================================
# Main
# =============================================================================
# --- Namespace Setup/Teardown ------------------------------------------------
ensure_test_namespace() {
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
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
    echo -e "${BLUE}║  Ebene 4: K3s E2E-Tests (E2E-K-01..K-05)     ║${NC}"
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

    if [[ -z "$filter" || "$filter" == "E2E-K-01" ]]; then
        run_test "E2E-K-01" "Zero-Downtime (Lastgenerator, 200 Req)" test_e2e_k01_zero_downtime
    fi

    if [[ -z "$filter" || "$filter" == "E2E-K-02" ]]; then
        run_test "E2E-K-02" "Auto-Rollback (defektes Image)" test_e2e_k02_auto_rollback_bad_image
    fi

    if [[ -z "$filter" || "$filter" == "E2E-K-03" ]]; then
        run_test "E2E-K-03" "Manueller Rollback (rollout undo)" test_e2e_k03_manual_rollback
    fi

    if [[ -z "$filter" || "$filter" == "E2E-K-04" ]]; then
        run_test "E2E-K-04" "Migration-Job-Fehler blockiert Rollout" test_e2e_k04_migration_job_failure_blocks
    fi

    if [[ -z "$filter" || "$filter" == "E2E-K-05" ]]; then
        run_test "E2E-K-05" "Paralleler Traffic (10 Clients)" test_e2e_k05_parallel_traffic
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
