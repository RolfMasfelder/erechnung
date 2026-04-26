#!/bin/bash
# Uninstall k3s from remote server (192.168.178.80)
set -e

REMOTE_HOST="${K3S_HOST:-rolf@192.168.178.80}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║        k3s Uninstall (192.168.178.80)         ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will delete the entire k3s cluster!${NC}"
echo -e "${YELLOW}⚠️  All deployments, data, and PersistentVolumes will be lost!${NC}"
echo ""
read -p "Are you sure you want to uninstall k3s? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Check SSH connection
echo -e "\n${GREEN}Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'Connection OK'" &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to $REMOTE_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH connection successful${NC}"

# Check if k3s is installed
if ! ssh "$REMOTE_HOST" "command -v k3s &> /dev/null"; then
    echo -e "${YELLOW}⚠️  k3s is not installed on $REMOTE_HOST${NC}"
    exit 0
fi

# Uninstall k3s
echo -e "\n${GREEN}Uninstalling k3s...${NC}"
ssh "$REMOTE_HOST" << 'EOF'
    if [ -f /usr/local/bin/k3s-uninstall.sh ]; then
        echo "Running k3s-uninstall.sh..."
        sudo /usr/local/bin/k3s-uninstall.sh
        echo "✅ k3s uninstalled"
    else
        echo "⚠️  k3s-uninstall.sh not found"
        exit 1
    fi
EOF

# Remove local kubeconfig
echo -e "\n${GREEN}Removing local kubeconfig...${NC}"
if [ -f "$HOME/.kube/config-k3s" ]; then
    rm "$HOME/.kube/config-k3s"
    echo -e "${GREEN}✅ Removed ~/.kube/config-k3s${NC}"
fi

echo -e "\n${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         k3s Successfully Uninstalled!          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "To reinstall, run: ./setup-k3s-local.sh"
