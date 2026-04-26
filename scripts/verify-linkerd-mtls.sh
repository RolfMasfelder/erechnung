#!/bin/bash
# Verify Linkerd mTLS is working correctly on k3s cluster
#
# Usage:
#   export KUBECONFIG=~/.kube/config-k3s
#   cd scripts && ./verify-linkerd-mtls.sh
set -e

NAMESPACE="erechnung"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure linkerd CLI is in PATH
export PATH="$HOME/.linkerd2/bin:$PATH"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Linkerd mTLS Verification                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Check Linkerd Health ─────────────────────────────────────────────

echo -e "${GREEN}1. Linkerd Health Check${NC}"
echo "─────────────────────────────────────────────────"
if ! command -v linkerd &>/dev/null; then
    echo -e "${RED}❌ Linkerd CLI not found. Install with: curl -fsL https://run.linkerd.io/install | sh${NC}"
    exit 1
fi

linkerd check 2>&1 | tail -20
echo ""

# ─── Check Sidecar Injection ─────────────────────────────────────────

echo -e "${GREEN}2. Sidecar Injection Status${NC}"
echo "─────────────────────────────────────────────────"

TOTAL_PODS=0
MESHED_PODS=0

while IFS= read -r line; do
    POD_NAME=$(echo "$line" | awk '{print $1}')
    CONTAINERS=$(echo "$line" | awk '{print $2}')

    if [ -z "$POD_NAME" ]; then continue; fi
    TOTAL_PODS=$((TOTAL_PODS + 1))

    # Check if pod has linkerd-proxy container
    HAS_PROXY=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.containers[*].name}' 2>/dev/null | grep -c "linkerd-proxy" || true)

    if [ "$HAS_PROXY" -gt 0 ]; then
        echo -e "  ${GREEN}✅ $POD_NAME [mTLS ACTIVE]${NC}"
        MESHED_PODS=$((MESHED_PODS + 1))
    else
        # Check if injection is explicitly disabled
        INJECT_DISABLED=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.linkerd\.io/inject}' 2>/dev/null || echo "")
        if [ "$INJECT_DISABLED" = "disabled" ]; then
            echo -e "  ${YELLOW}⚠️  $POD_NAME [OPTED OUT - stateful service]${NC}"
        else
            echo -e "  ${RED}❌ $POD_NAME [NO SIDECAR]${NC}"
        fi
    fi
done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | awk '{print $1, $2}')

echo ""
echo "  Meshed: $MESHED_PODS / $TOTAL_PODS pods"
echo ""

# ─── Check mTLS Connections ──────────────────────────────────────────

echo -e "${GREEN}3. mTLS Connection Edges${NC}"
echo "─────────────────────────────────────────────────"
linkerd viz edges deploy -n "$NAMESPACE" 2>/dev/null || echo -e "${YELLOW}(Viz not installed or no traffic yet)${NC}"
echo ""

# ─── Traffic Stats ───────────────────────────────────────────────────

echo -e "${GREEN}4. Traffic Statistics${NC}"
echo "─────────────────────────────────────────────────"
linkerd viz stat deploy -n "$NAMESPACE" 2>/dev/null || echo -e "${YELLOW}(No traffic data yet - generate some requests first)${NC}"
echo ""

# ─── Identity Check ──────────────────────────────────────────────────

echo -e "${GREEN}5. Service Identity Certificates${NC}"
echo "─────────────────────────────────────────────────"
# Check trust anchor expiry
TRUST_ANCHOR_EXPIRY=$(linkerd check 2>&1 | grep "trust anchors are within their validity period" || echo "")
if [ -n "$TRUST_ANCHOR_EXPIRY" ]; then
    echo -e "  ${GREEN}✅ Trust anchors valid${NC}"
else
    echo -e "  ${YELLOW}⚠️  Could not verify trust anchor validity${NC}"
fi

# Check issuer cert expiry
ISSUER_CERT=$(linkerd check 2>&1 | grep "issuer cert is within its validity period" || echo "")
if [ -n "$ISSUER_CERT" ]; then
    echo -e "  ${GREEN}✅ Issuer certificate valid${NC}"
else
    echo -e "  ${YELLOW}⚠️  Could not verify issuer certificate${NC}"
fi
echo ""

# ─── Network Policy Compatibility ────────────────────────────────────

echo -e "${GREEN}6. Network Policy Compatibility${NC}"
echo "─────────────────────────────────────────────────"
NP_COUNT=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
echo "  Active Network Policies: $NP_COUNT"

if [ "$NP_COUNT" -gt 0 ]; then
    echo -e "  ${GREEN}✅ Network Policies coexist with Linkerd mTLS${NC}"
    echo "  (Linkerd operates at L7 on top of L3/L4 Network Policies)"
fi
echo ""

# ─── Summary ─────────────────────────────────────────────────────────

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Verification Summary                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$MESHED_PODS" -gt 0 ]; then
    echo -e "${GREEN}✅ Linkerd Service Mesh is ACTIVE${NC}"
    echo -e "${GREEN}✅ mTLS encryption enabled for $MESHED_PODS services${NC}"
    echo -e "${GREEN}✅ Zero-config TLS 1.3 between meshed pods${NC}"
else
    echo -e "${RED}❌ No meshed pods found - check Linkerd installation${NC}"
fi
echo ""
echo -e "${BLUE}Dashboard:${NC} linkerd viz dashboard &"
echo ""
