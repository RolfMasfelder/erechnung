#!/bin/bash
# Build Docker images and load them into kind cluster
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CLUSTER_NAME="erechnung"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔨 Building and loading Docker images into kind...${NC}\n"

# Check if kind cluster exists
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${RED}❌ Cluster '${CLUSTER_NAME}' does not exist${NC}"
    echo "Create it first with: ./k8s/kind/setup.sh"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Step 1: Build Django/API Gateway image
echo -e "${GREEN}Step 1: Building Django application image...${NC}"
if [ -f "Dockerfile" ]; then
    docker build --target development -t erechnung-django:local -f Dockerfile .
    echo "✓ Built erechnung-django:local (development stage)"
else
    echo -e "${RED}❌ Dockerfile not found in $PROJECT_ROOT${NC}"
    exit 1
fi

# Step 2: Load image into kind
echo -e "\n${GREEN}Step 2: Loading image into kind cluster...${NC}"
kind load docker-image erechnung-django:local --name "${CLUSTER_NAME}"
echo "✓ Loaded erechnung-django:local into kind"

# Step 3: Check external images (they will be pulled automatically)
echo -e "\n${GREEN}Step 3: Checking external images...${NC}"
echo "The following images will be pulled automatically by kind:"
echo "  - postgres:17"
echo "  - redis:7-alpine"
echo "  - nginx:alpine"
echo "  - busybox:1.35"

echo -e "\n${GREEN}✅ Images ready for deployment${NC}"
echo ""
echo "Next step: Update k8s manifests to use local image"
echo "  Image name: erechnung-django:local"
echo "  Add imagePullPolicy: Never"
