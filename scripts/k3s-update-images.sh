#!/bin/bash
# Build, push and deploy all self-built images to the k3s cluster via the local registry.
# Uses kustomize image overrides in infra/k8s/k3s/kustomization.yaml — no manifest changes needed.
# Usage: ./k3s-update-images.sh [--skip-build]
set -e

REMOTE_HOST="${K3S_HOST:-rolf@192.168.178.80}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="192.168.178.80:5000"
KUSTOMIZATION="$PROJECT_ROOT/infra/k8s/k3s/kustomization.yaml"
KUSTOMIZATION_STAGING="$PROJECT_ROOT/infra/k8s/k3s/overlays/staging/kustomization.yaml"
SKIP_BUILD=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-build) SKIP_BUILD=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# Versioned image tag: v<version>-<git-sha>
VERSION=$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
GIT_SHA=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)
TAG="v${VERSION}-${GIT_SHA}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Update eRechnung Images (k3s via Registry) ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# Image definitions: image-name → build-source (compose service | Dockerfile)
# ---------------------------------------------------------------------------
# Format of IMAGES array:  "<registry-image-name>|<build-method>|<build-arg>"
#   build-method = "compose"  → docker compose build <service>; local tag = erechnung-<service>
#   build-method = "docker"   → docker build -f <Dockerfile> -t <local-tag> <context>
# ---------------------------------------------------------------------------
declare -a IMAGES=(
    "erechnung-web|compose|web"
    "erechnung-init|compose|init"
    "erechnung-celery|compose|web"        # same Dockerfile as web, different deployment
    "erechnung-frontend|docker|frontend/Dockerfile.prod|frontend"
    "erechnung-api-gateway|docker|infra/api-gateway/Dockerfile|infra/api-gateway"
)

# ---------------------------------------------------------------------------
# Pre-flight: registry accessible?
# ---------------------------------------------------------------------------
echo -e "${BLUE}🏷️  Image tag: ${TAG}${NC}"
echo ""
echo "Checking registry access..."
if ! curl -k -s "https://$REGISTRY/v2/" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot access registry at $REGISTRY${NC}"
    echo "Make sure the registry is running on $REMOTE_HOST"
    exit 1
fi
echo -e "${GREEN}✅ Registry accessible${NC}"

# ---------------------------------------------------------------------------
# Kubeconfig check (needed for Step 4)
# ---------------------------------------------------------------------------
export KUBECONFIG="$HOME/.kube/config-k3s"
if [ ! -f "$KUBECONFIG" ]; then
    echo -e "${RED}❌ Kubeconfig not found: $KUBECONFIG${NC}"
    echo "Run ./setup-k3s-local.sh first"
    exit 1
fi

cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Step 1: Build images
# ---------------------------------------------------------------------------
if [ "$SKIP_BUILD" = false ]; then
    echo -e "\n${GREEN}Step 1: Building application images...${NC}"

    # Build all compose services in one call
    docker compose build web init

    # Build standalone images
    echo "Building frontend..."
    docker build -f frontend/Dockerfile.prod -t erechnung-frontend:build frontend

    echo "Building api-gateway..."
    docker build -f infra/api-gateway/Dockerfile -t erechnung-api-gateway:build infra/api-gateway

    echo "Building postgres (with pgTAP)..."
    docker build -t erechnung-postgres:build infra/postgres
else
    echo -e "\n${YELLOW}Step 1: Skipping build (--skip-build)${NC}"
fi

# ---------------------------------------------------------------------------
# Step 2: Tag and push each image (versioned + latest)
# ---------------------------------------------------------------------------
echo -e "\n${GREEN}Step 2: Tagging and pushing images (tag: ${TAG})...${NC}"

tag_and_push() {
    local registry_name="$1"   # e.g. erechnung-web
    local local_tag="$2"       # local image:tag to tag from

    echo -e "  ${BLUE}→ $registry_name:$TAG${NC}"
    docker tag "$local_tag" "$REGISTRY/$registry_name:$TAG"
    docker push "$REGISTRY/$registry_name:$TAG"
}

# compose-built images have this local name pattern
COMPOSE_PROJECT_NAME=$(grep -oP '(?<=^name: ).*' docker-compose.yml 2>/dev/null || echo "erechnung")

tag_and_push "erechnung-web"         "${COMPOSE_PROJECT_NAME}-web:latest"
tag_and_push "erechnung-init"        "${COMPOSE_PROJECT_NAME}-init:latest"
tag_and_push "erechnung-celery"      "${COMPOSE_PROJECT_NAME}-web:latest"  # same image, different tag
tag_and_push "erechnung-frontend"    "erechnung-frontend:build"
tag_and_push "erechnung-api-gateway" "erechnung-api-gateway:build"
tag_and_push "erechnung-postgres"    "erechnung-postgres:build"

echo -e "${GREEN}✅ All images pushed${NC}"

# ---------------------------------------------------------------------------
# Step 3: Update kustomization.yaml image tags
# ---------------------------------------------------------------------------
echo -e "\n${GREEN}Step 3: Updating kustomization.yaml with tag ${TAG}...${NC}"

python3 - "$KUSTOMIZATION" "$TAG" <<'PYEOF'
import sys, re

kustomization_file = sys.argv[1]
new_tag = sys.argv[2]

with open(kustomization_file, 'r') as f:
    content = f.read()

# Replace newTag for all self-built images
self_built_images = [
    'erechnung-web',
    'erechnung-init',
    'erechnung-celery',
    'erechnung-frontend',
    'erechnung-api-gateway',
    'erechnung-postgres',
]

for img in self_built_images:
    # Match lines like:  - name: .../erechnung-web     followed by   newTag: <anything>
    pattern = r'(- name: [^\n]*/{}[^\n]*\n    newTag: )[^\n]+'.format(re.escape(img))
    replacement = r'\g<1>' + new_tag
    content = re.sub(pattern, replacement, content)

with open(kustomization_file, 'w') as f:
    f.write(content)

print(f"  Updated kustomization.yaml → {new_tag}")
PYEOF

# Same update for staging overlay
python3 - "$KUSTOMIZATION_STAGING" "$TAG" <<'PYEOF'
import sys, re

kustomization_file = sys.argv[1]
new_tag = sys.argv[2]

with open(kustomization_file, 'r') as f:
    content = f.read()

self_built_images = [
    'erechnung-web',
    'erechnung-init',
    'erechnung-celery',
    'erechnung-frontend',
    'erechnung-api-gateway',
    'erechnung-postgres',
]

for img in self_built_images:
    pattern = r'(- name: [^\n]*/{}[^\n]*\n    newTag: )[^\n]+'.format(re.escape(img))
    replacement = r'\g<1>' + new_tag
    content = re.sub(pattern, replacement, content)

with open(kustomization_file, 'w') as f:
    f.write(content)

print(f"  Updated overlays/staging/kustomization.yaml → {new_tag}")
PYEOF

echo -e "${GREEN}✅ kustomization.yaml updated (production + staging)${NC}"

# ---------------------------------------------------------------------------
# Step 4a: Deploy production namespace (erechnung)
# ---------------------------------------------------------------------------
echo -e "\n${GREEN}Step 4a: Deploying production namespace (erechnung)...${NC}"

# Jobs are immutable once created — delete first so the job is recreated with
# the new image and migrations are actually applied.
echo "  Deleting old init job (will be recreated)..."
kubectl delete job django-init -n erechnung --ignore-not-found=true

kubectl apply -k "$PROJECT_ROOT/infra/k8s/k3s/"

# Wait for init job to finish before checking deployments
echo -e "\n${GREEN}  Waiting for django-init job (production) to complete...${NC}"
kubectl wait --for=condition=complete job/django-init -n erechnung --timeout=120s \
    || { echo -e "${RED}❌ Init job (production) failed or timed out — check logs:"; \
         kubectl logs -n erechnung -l job-name=django-init --tail=50; exit 1; }

# ---------------------------------------------------------------------------
# Step 4b: Deploy staging namespace (erechnung-staging)
# ---------------------------------------------------------------------------
echo -e "\n${GREEN}Step 4b: Deploying staging namespace (erechnung-staging)...${NC}"

echo "  Deleting old init job in staging (will be recreated)..."
kubectl delete job django-init -n erechnung-staging --ignore-not-found=true

kubectl kustomize --load-restrictor=LoadRestrictionsNone "$PROJECT_ROOT/infra/k8s/k3s/overlays/staging/" | kubectl apply -f -

# Wait for staging init job
echo -e "\n${GREEN}  Waiting for django-init job (staging) to complete...${NC}"
kubectl wait --for=condition=complete job/django-init -n erechnung-staging --timeout=180s \
    || { echo -e "${YELLOW}⚠️  Staging init job timed out — check logs (non-fatal):"; \
         kubectl logs -n erechnung-staging -l job-name=django-init --tail=30; }

# ---------------------------------------------------------------------------
# Step 5: Wait for rollouts
# ---------------------------------------------------------------------------
echo -e "\n${GREEN}Step 5: Waiting for rollouts (production)...${NC}"
kubectl rollout status deployment/django-web    -n erechnung --timeout=180s
kubectl rollout status deployment/celery-worker -n erechnung --timeout=180s
kubectl rollout status deployment/frontend      -n erechnung --timeout=180s
kubectl rollout status deployment/api-gateway   -n erechnung --timeout=180s

echo -e "\n${GREEN}Step 5b: Waiting for rollouts (staging)...${NC}"
kubectl rollout status deployment/django-web    -n erechnung-staging --timeout=180s
kubectl rollout status deployment/celery-worker -n erechnung-staging --timeout=180s
kubectl rollout status deployment/frontend      -n erechnung-staging --timeout=180s
kubectl rollout status deployment/api-gateway   -n erechnung-staging --timeout=180s

echo -e "\n${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Images Successfully Updated!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🏷️  Deployed tag: ${TAG}${NC}"
echo ""

echo -e "${BLUE}📊 Current Status (production):${NC}"
kubectl get pods -n erechnung
echo ""
echo -e "${BLUE}📊 Current Status (staging):${NC}"
kubectl get pods -n erechnung-staging
echo ""

echo -e "${BLUE}📝 View logs:${NC}"
echo "  kubectl logs -n erechnung -l app=django-web --tail=20 -f"
echo "  kubectl logs -n erechnung-staging -l app=django-web --tail=20 -f"
