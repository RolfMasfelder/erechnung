#!/usr/bin/env bash
# =============================================================================
# Ebene-1 K3s Update-Skript-Tests (S-05, S-06, S-12)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.3
#
# Tests für die Skript-Logik von update-k3s.sh und preflight.sh (K3s-Teil).
# Verwendet Mocking für externe Abhängigkeiten (kubectl, curl etc.).
#
# Usage:
#   ./scripts/tests/test_update_k3s.sh          # Alle Tests
#   ./scripts/tests/test_update_k3s.sh S-05      # Einzelner Test
#
# Benötigt: bash 4+
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LIB_DIR="$PROJECT_ROOT/scripts/lib"

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

# Test-Result-Array für Summary
declare -a TEST_RESULTS=()

# --- Test Framework ----------------------------------------------------------

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    if [[ "$actual" == "$expected" ]]; then
        return 0
    else
        echo "  Expected exit code $expected, got $actual" >&2
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    if echo "$haystack" | grep -q "$needle"; then
        return 0
    else
        echo "  Expected output to contain: $needle" >&2
        return 1
    fi
}

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

# --- Mock Setup --------------------------------------------------------------

MOCK_DIR=""

setup_mocks() {
    MOCK_DIR=$(mktemp -d)

    # Mock kubectl: always fail (cluster not reachable)
    cat > "$MOCK_DIR/kubectl-fail" <<'MOCKEOF'
#!/bin/bash
echo "error: the server doesn't have a resource type" >&2
exit 1
MOCKEOF
    chmod +x "$MOCK_DIR/kubectl-fail"

    # Mock kubectl: node NotReady
    cat > "$MOCK_DIR/kubectl-node-notready" <<'MOCKEOF'
#!/bin/bash
case "$*" in
    "cluster-info")
        echo "Kubernetes control plane is running at https://192.168.178.80:6443"
        exit 0
        ;;
    "get nodes --no-headers")
        echo "k3s-node1   NotReady   control-plane,master   10d   v1.28.5"
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
MOCKEOF
    chmod +x "$MOCK_DIR/kubectl-node-notready"

    # Mock kubectl: all healthy
    cat > "$MOCK_DIR/kubectl-healthy" <<'MOCKEOF'
#!/bin/bash
case "$*" in
    "cluster-info")
        echo "Kubernetes control plane is running at https://192.168.178.80:6443"
        exit 0
        ;;
    "get nodes --no-headers")
        echo "k3s-node1   Ready   control-plane,master   10d   v1.28.5"
        exit 0
        ;;
    *)
        exit 0
        ;;
esac
MOCKEOF
    chmod +x "$MOCK_DIR/kubectl-healthy"
}

teardown_mocks() {
    if [[ -n "$MOCK_DIR" && -d "$MOCK_DIR" ]]; then
        rm -rf "$MOCK_DIR"
    fi
}

# =============================================================================
# S-05: Cluster nicht erreichbar → Exit 1
# =============================================================================
test_s05_cluster_not_reachable() {
    # Override kubectl with failing mock
    kubectl() {
        "$MOCK_DIR/kubectl-fail" "$@"
    }
    export -f kubectl

    # Source preflight and test check_cluster_health
    local output result=0
    output=$(source "$LIB_DIR/preflight.sh" && check_cluster_health 2>&1) || result=$?

    # Restore kubectl
    unset -f kubectl

    assert_exit_code "1" "$result"
    assert_contains "$output" "nicht erreichbar"
}

# =============================================================================
# S-06: Node NotReady → Exit 1 + Node-Liste
# =============================================================================
test_s06_node_not_ready() {
    # Override kubectl with node-notready mock
    kubectl() {
        "$MOCK_DIR/kubectl-node-notready" "$@"
    }
    export -f kubectl

    local output result=0
    output=$(source "$LIB_DIR/preflight.sh" && check_nodes_ready 2>&1) || result=$?

    # Restore kubectl
    unset -f kubectl

    assert_exit_code "1" "$result"
    assert_contains "$output" "nicht Ready"
}

# =============================================================================
# S-12: kustomization.yaml newTag korrekt ersetzt
# =============================================================================
test_s12_kustomization_newtag_update() {
    # Create temp kustomization.yaml
    local tmp_kust
    tmp_kust=$(mktemp)

    cat > "$tmp_kust" <<'KUSTEOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - manifests/50-deploy-django-web.yaml

images:
  - name: 192.168.178.80:5000/erechnung-web
    newTag: v1.0.0-abc1234
  - name: 192.168.178.80:5000/erechnung-init
    newTag: v1.0.0-abc1234
  - name: 192.168.178.80:5000/erechnung-celery
    newTag: v1.0.0-abc1234
  - name: 192.168.178.80:5000/erechnung-frontend
    newTag: v1.0.0-abc1234
  - name: 192.168.178.80:5000/erechnung-api-gateway
    newTag: v1.0.0-abc1234
  - name: 192.168.178.80:5000/erechnung-postgres
    newTag: v1.0.0-abc1234
KUSTEOF

    local new_tag="v1.1.0-def5678"

    # Run the same Python inline script used in update-k3s.sh
    python3 - "$tmp_kust" "$new_tag" <<'PYEOF'
import sys, re

kustomization_file = sys.argv[1]
new_tag = sys.argv[2]

with open(kustomization_file, 'r') as f:
    content = f.read()

self_built_images = [
    'erechnung-web', 'erechnung-init', 'erechnung-celery',
    'erechnung-frontend', 'erechnung-api-gateway', 'erechnung-postgres',
]

for img in self_built_images:
    pattern = r'(- name: [^\n]*/{}[^\n]*\n    newTag: )[^\n]+'.format(re.escape(img))
    replacement = r'\g<1>' + new_tag
    content = re.sub(pattern, replacement, content)

with open(kustomization_file, 'w') as f:
    f.write(content)
PYEOF

    # Verify all images got the new tag
    local content
    content=$(cat "$tmp_kust")

    local all_updated=true
    for img in erechnung-web erechnung-init erechnung-celery erechnung-frontend erechnung-api-gateway erechnung-postgres; do
        if ! echo "$content" | grep -A1 "$img" | grep -q "$new_tag"; then
            echo "  $img was not updated to $new_tag" >&2
            all_updated=false
        fi
    done

    # Verify old tag is gone
    if echo "$content" | grep -q "v1.0.0-abc1234"; then
        echo "  Old tag v1.0.0-abc1234 still present" >&2
        all_updated=false
    fi

    rm -f "$tmp_kust"

    [[ "$all_updated" == true ]]
}

# =============================================================================
# Main
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Ebene 1: K3s-Skript-Unit-Tests (S-05..S-12) ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""

    setup_mocks

    if [[ -z "$filter" || "$filter" == "S-05" ]]; then
        run_test "S-05" "Cluster nicht erreichbar → Exit 1" test_s05_cluster_not_reachable
    fi

    if [[ -z "$filter" || "$filter" == "S-06" ]]; then
        run_test "S-06" "Node NotReady → Exit 1 + Meldung" test_s06_node_not_ready
    fi

    if [[ -z "$filter" || "$filter" == "S-12" ]]; then
        run_test "S-12" "kustomization.yaml newTag korrekt ersetzt" test_s12_kustomization_newtag_update
    fi

    teardown_mocks

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
