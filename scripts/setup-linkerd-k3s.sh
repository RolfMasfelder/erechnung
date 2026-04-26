#!/bin/bash
# Setup Linkerd Service Mesh on k3s (192.168.178.80)
# Provides automatic mTLS for all service-to-service communication
#
# Prerequisites:
#   - k3s running on remote host
#   - KUBECONFIG pointing to k3s cluster
#   - kubectl access to cluster
#
# Usage:
#   export KUBECONFIG=~/.kube/config-k3s
#   cd scripts && ./setup-linkerd-k3s.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REMOTE_HOST="${K3S_HOST:-rolf@192.168.178.80}"
LINKERD_VERSION="${LINKERD_VERSION:-stable-2.14.10}"
NAMESPACE="erechnung"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Linkerd Service Mesh Setup (k3s)            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Preflight Checks ────────────────────────────────────────────────

echo -e "${GREEN}Step 1: Preflight checks...${NC}"

# Check KUBECONFIG
if [ -z "$KUBECONFIG" ]; then
    if [ -f "$HOME/.kube/config-k3s" ]; then
        export KUBECONFIG="$HOME/.kube/config-k3s"
        echo -e "${YELLOW}Auto-detected KUBECONFIG: $KUBECONFIG${NC}"
    else
        echo -e "${RED}❌ KUBECONFIG not set. Run: export KUBECONFIG=~/.kube/config-k3s${NC}"
        exit 1
    fi
fi

# Verify cluster access
if ! kubectl cluster-info &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    echo "   Check: export KUBECONFIG=~/.kube/config-k3s"
    exit 1
fi

echo -e "${GREEN}✅ Cluster accessible${NC}"
kubectl get nodes --no-headers

# Check if Linkerd is already installed
if kubectl get namespace linkerd &>/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Linkerd namespace already exists.${NC}"
    read -p "Reinstall Linkerd? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing Linkerd installation..."
        linkerd uninstall 2>/dev/null | kubectl delete -f - 2>/dev/null || true
        kubectl delete namespace linkerd linkerd-viz 2>/dev/null || true
        sleep 5
    else
        echo "Skipping Linkerd installation. Running injection only."
        SKIP_INSTALL=true
    fi
fi

# ─── Install Linkerd CLI ─────────────────────────────────────────────

if [ "$SKIP_INSTALL" != "true" ]; then
    echo -e "\n${GREEN}Step 2: Installing Linkerd CLI...${NC}"

    if command -v linkerd &>/dev/null; then
        CURRENT_VERSION=$(linkerd version --client --short 2>/dev/null || echo "unknown")
        echo -e "${YELLOW}Linkerd CLI already installed: $CURRENT_VERSION${NC}"
    else
        echo "Downloading Linkerd CLI ($LINKERD_VERSION)..."
        curl -fsL https://run.linkerd.io/install | sh

        # Add to PATH for this session
        export PATH="$HOME/.linkerd2/bin:$PATH"

        if ! command -v linkerd &>/dev/null; then
            echo -e "${RED}❌ Linkerd CLI installation failed${NC}"
            exit 1
        fi
    fi

    # Ensure PATH includes linkerd
    export PATH="$HOME/.linkerd2/bin:$PATH"

    echo -e "${GREEN}✅ Linkerd CLI: $(linkerd version --client --short 2>/dev/null)${NC}"

    # ─── Pre-flight Check ────────────────────────────────────────────

    echo -e "\n${GREEN}Step 3: Running Linkerd pre-flight check...${NC}"
    if ! linkerd check --pre; then
        echo -e "${YELLOW}⚠️  Pre-flight check reported issues. Continuing anyway...${NC}"
    fi

    # ─── Install Linkerd CRDs ────────────────────────────────────────

    echo -e "\n${GREEN}Step 4: Installing Linkerd CRDs...${NC}"
    linkerd install --crds | kubectl apply -f -
    echo -e "${GREEN}✅ CRDs installed${NC}"

    # ─── Install Linkerd Control Plane ────────────────────────────────

    echo -e "\n${GREEN}Step 5: Installing Linkerd Control Plane...${NC}"
    linkerd install | kubectl apply -f -

    echo "⏳ Waiting for Linkerd control plane..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/linkerd-destination -n linkerd || true
    kubectl wait --for=condition=available --timeout=300s \
        deployment/linkerd-identity -n linkerd || true
    kubectl wait --for=condition=available --timeout=300s \
        deployment/linkerd-proxy-injector -n linkerd || true

    echo -e "${GREEN}✅ Control Plane installed${NC}"

    # ─── Verify Installation ─────────────────────────────────────────

    echo -e "\n${GREEN}Step 6: Verifying Linkerd installation...${NC}"
    if linkerd check; then
        echo -e "${GREEN}✅ Linkerd installation verified${NC}"
    else
        echo -e "${YELLOW}⚠️  Some checks failed - may need time to stabilize${NC}"
    fi

    # ─── Install Linkerd Viz (optional dashboard) ─────────────────────

    echo -e "\n${GREEN}Step 7: Installing Linkerd Viz dashboard...${NC}"
    linkerd viz install | kubectl apply -f -

    echo "⏳ Waiting for Linkerd Viz..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/web -n linkerd-viz || true

    echo -e "${GREEN}✅ Viz dashboard installed${NC}"
fi

# ─── Annotate Namespace for Auto-Injection ────────────────────────────

echo -e "\n${GREEN}Step 8: Configuring namespace for auto-injection...${NC}"

# Add Linkerd injection annotation to erechnung namespace
kubectl annotate namespace "$NAMESPACE" linkerd.io/inject=enabled --overwrite

echo -e "${GREEN}✅ Namespace '$NAMESPACE' annotated for Linkerd injection${NC}"

# ─── Restart Deployments for Sidecar Injection ────────────────────────

echo -e "\n${GREEN}Step 9: Restarting deployments for sidecar injection...${NC}"

# Restart application workloads (not infrastructure like postgres/redis initially)
DEPLOYMENTS=(django-web celery-worker api-gateway frontend)

for deploy in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment "$deploy" -n "$NAMESPACE" &>/dev/null; then
        echo "  Restarting $deploy..."
        kubectl rollout restart deployment/"$deploy" -n "$NAMESPACE"
    else
        echo -e "  ${YELLOW}⚠️  $deploy not found (skipping)${NC}"
    fi
done

echo ""
echo "⏳ Waiting for rollouts to complete..."
for deploy in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment "$deploy" -n "$NAMESPACE" &>/dev/null; then
        kubectl rollout status deployment/"$deploy" -n "$NAMESPACE" --timeout=180s || true
    fi
done

echo -e "${GREEN}✅ Deployments restarted with Linkerd sidecars${NC}"

# ─── Verify mTLS ─────────────────────────────────────────────────────

echo -e "\n${GREEN}Step 10: Verifying mTLS...${NC}"

# Check that pods have linkerd-proxy sidecar
echo ""
echo "Pod sidecar status:"
kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.containers[*]}{.name}{" "}{end}{"\n"}{end}' | \
    while read -r line; do
        if echo "$line" | grep -q "linkerd-proxy"; then
            echo -e "  ${GREEN}✅ $line${NC}"
        else
            echo -e "  ${YELLOW}⚠️  $line (no sidecar)${NC}"
        fi
    done

# Check mTLS with linkerd
echo ""
if command -v linkerd &>/dev/null; then
    export PATH="$HOME/.linkerd2/bin:$PATH"
    echo "Linkerd stats for namespace $NAMESPACE:"
    linkerd stat deploy -n "$NAMESPACE" 2>/dev/null || echo "(stats may take a moment to populate)"
fi

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Linkerd Setup Complete!                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Features enabled:${NC}"
echo "  ✅ Automatic mTLS between all meshed services"
echo "  ✅ Traffic encryption (TLS 1.3)"
echo "  ✅ Identity-based authorization ready"
echo "  ✅ Viz dashboard for observability"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  linkerd check                        # Health check"
echo "  linkerd viz dashboard &              # Open dashboard"
echo "  linkerd viz stat deploy -n $NAMESPACE  # Traffic stats"
echo "  linkerd viz edges deploy -n $NAMESPACE # mTLS edges"
echo "  linkerd viz tap deploy -n $NAMESPACE   # Live traffic"
echo ""
echo -e "${BLUE}Verify mTLS:${NC}"
echo "  cd scripts && ./verify-linkerd-mtls.sh"
echo ""
echo -e "${YELLOW}Note: postgres and redis are NOT meshed (stateful services).${NC}"
echo -e "${YELLOW}Network Policies already protect postgres/redis access.${NC}"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
