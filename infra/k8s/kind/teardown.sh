#!/bin/bash
# Teardown script for kind cluster
set -e

echo "🗑️  Tearing down eRechnung kind cluster..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if cluster exists
if ! kind get clusters 2>/dev/null | grep -q "^erechnung$"; then
    echo -e "${YELLOW}⚠️  Cluster 'erechnung' does not exist.${NC}"
    exit 0
fi

# Confirm deletion
echo -e "${YELLOW}⚠️  This will delete the entire kind cluster 'erechnung'.${NC}"
echo "All data will be lost!"
read -p "Continue? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Delete cluster
echo "Deleting kind cluster..."
kind delete cluster --name erechnung

echo -e "${GREEN}✅ Cluster deleted successfully.${NC}"
