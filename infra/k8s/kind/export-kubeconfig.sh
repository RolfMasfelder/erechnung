#!/bin/bash
# Export kubeconfig for remote access
# Run this on the REMOTE HOST where kind cluster is running

set -e

CLUSTER_NAME="erechnung"
OUTPUT_FILE="${HOME}/kubeconfig-${CLUSTER_NAME}.yaml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔧 Exporting kubeconfig for cluster '${CLUSTER_NAME}'..."

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ kind is not installed${NC}"
    exit 1
fi

# Check if cluster exists
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${RED}❌ Cluster '${CLUSTER_NAME}' does not exist${NC}"
    echo "Available clusters:"
    kind get clusters
    exit 1
fi

# Export kubeconfig
echo "Exporting kubeconfig..."
kind get kubeconfig --name "${CLUSTER_NAME}" > "${OUTPUT_FILE}"

if [ ! -f "${OUTPUT_FILE}" ]; then
    echo -e "${RED}❌ Failed to export kubeconfig${NC}"
    exit 1
fi

# Make readable only by user
chmod 600 "${OUTPUT_FILE}"

# Extract API server details
API_SERVER=$(grep "server:" "${OUTPUT_FILE}" | awk '{print $2}')
API_PORT=$(echo "${API_SERVER}" | sed -E 's/.*:([0-9]+).*/\1/')

echo -e "${GREEN}✅ Kubeconfig exported successfully${NC}"
echo ""
echo "File: ${OUTPUT_FILE}"
echo "API Server: ${API_SERVER}"
echo "API Port: ${API_PORT}"
echo ""
echo "Next steps:"
echo "1. This file is ready to be copied to your local machine"
echo "2. Run setup-remote-access.sh on your local machine"
echo ""
echo "Or manually:"
echo "  scp $(whoami)@$(hostname):${OUTPUT_FILE} ~/.kube/config-kind-erechnung"
