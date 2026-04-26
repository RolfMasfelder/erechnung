#!/usr/bin/env bash
# =============================================================================
# Setup/Teardown für K3s Update-Test-Namespace
# =============================================================================
# Deployt einen vollständigen isolierten eRechnung-Stack im Namespace
# erechnung-update-test und wartet bis alle Pods ready sind.
#
# Usage:
#   ./scripts/tests/k3s_test_ns_setup.sh setup     # Stack deployen
#   ./scripts/tests/k3s_test_ns_setup.sh teardown   # Namespace löschen
#   ./scripts/tests/k3s_test_ns_setup.sh status     # Status anzeigen
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_MANIFESTS="$PROJECT_ROOT/infra/k8s/k3s/test"
NAMESPACE="erechnung-update-test"

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

# ---------------------------------------------------------------------------
# Setup: Deploy full stack into test namespace
# ---------------------------------------------------------------------------
do_setup() {
    echo -e "${BLUE}=== Test-Namespace Setup: $NAMESPACE ===${NC}"

    # 1. Apply kustomization (creates namespace + all resources)
    echo -e "  ${BLUE}[1/5]${NC} Applying kustomization..."
    kubectl apply -k "$TEST_MANIFESTS"

    # 2. Wait for Postgres to be ready
    echo -e "  ${BLUE}[2/5]${NC} Waiting for Postgres..."
    kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=120s

    # 3. Wait for Redis to be ready
    echo -e "  ${BLUE}[3/5]${NC} Waiting for Redis..."
    kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=60s

    # 4. Wait for Init Job to complete (migrations + collectstatic)
    echo -e "  ${BLUE}[4/5]${NC} Waiting for Django Init Job..."
    # The job needs the DB to be ready first, so wait a bit for init container
    if ! kubectl wait --for=condition=complete job/django-init -n "$NAMESPACE" --timeout=180s 2>/dev/null; then
        echo -e "  ${YELLOW}Init Job noch nicht fertig, prüfe Status...${NC}"
        kubectl get job/django-init -n "$NAMESPACE" -o wide
        kubectl logs job/django-init -n "$NAMESPACE" --all-containers 2>/dev/null || true
        echo -e "  ${RED}Init Job fehlgeschlagen!${NC}"
        return 1
    fi

    # 5. Wait for all deployments to be ready
    echo -e "  ${BLUE}[5/5]${NC} Waiting for all deployments..."
    for deploy in django-web celery-worker api-gateway frontend; do
        echo -ne "    $deploy ... "
        if kubectl rollout status "deployment/$deploy" -n "$NAMESPACE" --timeout=180s 2>/dev/null; then
            echo -e "${GREEN}ready${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            kubectl get pods -n "$NAMESPACE" -l "app=$deploy" -o wide
            return 1
        fi
    done

    echo ""
    echo -e "${GREEN}=== Test-Namespace $NAMESPACE ist bereit ===${NC}"
    echo ""
    do_status
}

# ---------------------------------------------------------------------------
# Teardown: Delete the entire test namespace
# ---------------------------------------------------------------------------
do_teardown() {
    echo -e "${BLUE}=== Test-Namespace Teardown: $NAMESPACE ===${NC}"

    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        echo -e "  Lösche Namespace $NAMESPACE..."
        kubectl delete namespace "$NAMESPACE" --timeout=120s
        echo -e "  ${GREEN}Namespace gelöscht.${NC}"
    else
        echo -e "  ${YELLOW}Namespace $NAMESPACE existiert nicht.${NC}"
    fi
}

# ---------------------------------------------------------------------------
# Status: Show current state of test namespace
# ---------------------------------------------------------------------------
do_status() {
    echo -e "${BLUE}=== Status: $NAMESPACE ===${NC}"

    if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
        echo -e "  ${YELLOW}Namespace existiert nicht.${NC}"
        return 1
    fi

    echo -e "\n${BLUE}--- Pods ---${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || true

    echo -e "\n${BLUE}--- Deployments ---${NC}"
    kubectl get deployments -n "$NAMESPACE" 2>/dev/null || true

    echo -e "\n${BLUE}--- Services ---${NC}"
    kubectl get svc -n "$NAMESPACE" 2>/dev/null || true

    echo -e "\n${BLUE}--- PDBs ---${NC}"
    kubectl get pdb -n "$NAMESPACE" 2>/dev/null || true

    echo -e "\n${BLUE}--- Jobs ---${NC}"
    kubectl get jobs -n "$NAMESPACE" 2>/dev/null || true

    echo -e "\n${BLUE}--- PVCs ---${NC}"
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
case "${1:-}" in
    setup)
        do_setup
        ;;
    teardown)
        do_teardown
        ;;
    status)
        do_status
        ;;
    *)
        echo "Usage: $(basename "$0") {setup|teardown|status}"
        exit 1
        ;;
esac
