#!/bin/bash
# Setup script for DIRECT kubectl access to kind cluster (no SSH tunnel)
# Run this on your LOCAL machine to access the remote kind cluster
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REMOTE_HOST="rolf@192.168.178.80"  # e.g., user@192.168.1.100
REMOTE_IP="192.168.178.80"      # e.g., 192.168.1.100 (without user@)
CLUSTER_NAME="erechnung"
KUBECONFIG_PATH="$HOME/.kube/config-kind-erechnung"

echo -e "${BLUE}🔧 Direct kubectl Setup for kind cluster '${CLUSTER_NAME}'${NC}\n"

echo -e "${GREEN}Step 1: Checking prerequisites...${NC}"
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not installed${NC}"
    exit 1
fi
echo "✓ kubectl found"

echo -e "\n${GREEN}Step 2: Fetching kubeconfig from remote...${NC}"
if ! ssh "$REMOTE_HOST" "kind get kubeconfig --name ${CLUSTER_NAME}" > /tmp/kubeconfig-${CLUSTER_NAME}.tmp 2>/dev/null; then
    echo -e "${RED}❌ Failed to get kubeconfig${NC}"
    exit 1
fi

# Extract API server port from kubeconfig
API_PORT=$(grep "server:" /tmp/kubeconfig-${CLUSTER_NAME}.tmp | sed -E 's/.*:([0-9]+).*/\1/')
echo "✓ API server port: $API_PORT"

# Create kubeconfig with direct remote IP
mkdir -p "$(dirname "$KUBECONFIG_PATH")"
sed "s|server:.*|server: https://${REMOTE_IP}:${API_PORT}|" \
    /tmp/kubeconfig-${CLUSTER_NAME}.tmp > "$KUBECONFIG_PATH"
chmod 600 "$KUBECONFIG_PATH"
rm /tmp/kubeconfig-${CLUSTER_NAME}.tmp

echo "✓ Kubeconfig saved: $KUBECONFIG_PATH"
echo "  Server: https://${REMOTE_IP}:${API_PORT}"

echo -e "\n${GREEN}Step 3: Testing connection...${NC}"
export KUBECONFIG="$KUBECONFIG_PATH"

if kubectl cluster-info --request-timeout=10s &> /dev/null; then
    echo -e "${GREEN}✅ Connection successful!${NC}"
    echo ""
    kubectl get nodes
    echo ""
    kubectl get pods -n erechnung 2>/dev/null || echo "(namespace erechnung not found)"
else
    echo -e "${RED}❌ Connection failed${NC}"
    echo ""
    echo "Firewall-Check erforderlich:"
    echo "  1. Auf ${REMOTE_IP} muss Port ${API_PORT} offen sein"
    echo "  2. Prüfe: sudo firewall-cmd --list-all"
    echo "  3. Öffne: sudo firewall-cmd --permanent --add-port=${API_PORT}/tcp"
    echo "  4. Reload: sudo firewall-cmd --reload"
    echo ""
    echo "Oder teste manuell:"
    echo "  curl -k https://${REMOTE_IP}:${API_PORT}"
    exit 1
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Verwendung:"
echo -e "  ${YELLOW}export KUBECONFIG=\"$KUBECONFIG_PATH\"${NC}"
echo "  kubectl get pods -n erechnung"
echo "  kubectl logs -n erechnung deployment/django-web"
echo ""
echo "Oder in Shell-Profile (~/.bashrc):"
echo "  export KUBECONFIG=\"$KUBECONFIG_PATH\""
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
