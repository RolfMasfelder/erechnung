#!/bin/bash
# Setup k3s on local server (192.168.178.80 / cirrus7-neu)
# Provides real Kubernetes with MetalLB LAN-IP support
set -e

REMOTE_HOST="${K3S_HOST:-rolf@192.168.178.80}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   k3s Setup auf cirrus7-neu (192.168.178.80)  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check SSH connection
echo -e "${GREEN}Step 1: Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'Connection OK'" &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to $REMOTE_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH connection successful${NC}"

# Check if k3s is already installed
echo -e "\n${GREEN}Step 2: Checking k3s installation...${NC}"
if ssh "$REMOTE_HOST" "command -v k3s &> /dev/null"; then
    echo -e "${YELLOW}⚠️  k3s is already installed.${NC}"
    read -p "Reinstall k3s? This will delete existing cluster! [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstalling k3s..."
        ssh "$REMOTE_HOST" "sudo /usr/local/bin/k3s-uninstall.sh" || true
        sleep 3
    else
        echo "Skipping k3s installation."
        SKIP_K3S_INSTALL=true
    fi
fi

# Install k3s
if [ "$SKIP_K3S_INSTALL" != "true" ]; then
    echo -e "\n${GREEN}Step 3: Installing k3s on remote server...${NC}"

    # Create registry config for k3s
    echo "Creating k3s registry config..."
    ssh "$REMOTE_HOST" << 'EOF'
        # Create registries.yaml for k3s to trust local registry
        sudo mkdir -p /etc/rancher/k3s
        sudo tee /etc/rancher/k3s/registries.yaml > /dev/null <<REGEOF
mirrors:
  "192.168.178.80:5000":
    endpoint:
      - "https://192.168.178.80:5000"
configs:
  "192.168.178.80:5000":
    tls:
      insecure_skip_verify: true
REGEOF

        echo "Installing k3s (lightweight Kubernetes)..."
        # Installation flags (NOT changeable later without reinstall):
        # --disable traefik    : We use nginx-ingress instead
        # --disable servicelb  : We use MetalLB instead (required for LAN IPs)
        #
        # NOTE: servicelb (Klipper LB) and MetalLB cannot run simultaneously.
        # To use k3s built-in ServiceLB instead: Remove --disable servicelb
        # and skip MetalLB installation (Step 6)
        curl -sfL https://get.k3s.io | sh -s - \
            --write-kubeconfig-mode 644 \
            --disable traefik \
            --disable servicelb

        echo "Waiting for k3s to be ready..."
        sleep 10
        sudo k3s kubectl wait --for=condition=ready node --all --timeout=120s
EOF
    echo -e "${GREEN}✅ k3s installed successfully${NC}"
fi

# Get kubeconfig
echo -e "\n${GREEN}Step 4: Exporting kubeconfig...${NC}"
KUBECONFIG_DIR="$HOME/.kube"
mkdir -p "$KUBECONFIG_DIR"

ssh "$REMOTE_HOST" "sudo cat /etc/rancher/k3s/k3s.yaml" > "$KUBECONFIG_DIR/config-k3s"

# Replace server IP and rename all 'default' references to 'k3s-cirrus7'
sed -i 's|server: https://127.0.0.1:6443|server: https://192.168.178.80:6443|g' "$KUBECONFIG_DIR/config-k3s"
sed -i 's|name: default|name: k3s-cirrus7|g' "$KUBECONFIG_DIR/config-k3s"
sed -i 's|cluster: default|cluster: k3s-cirrus7|g' "$KUBECONFIG_DIR/config-k3s"
sed -i 's|user: default|user: k3s-cirrus7|g' "$KUBECONFIG_DIR/config-k3s"
sed -i 's|current-context: default|current-context: k3s-cirrus7|g' "$KUBECONFIG_DIR/config-k3s"

echo -e "${GREEN}✅ Kubeconfig exported to ~/.kube/config-k3s${NC}"

# Export for this session
export KUBECONFIG="$KUBECONFIG_DIR/config-k3s"

# Verify connection
echo -e "\n${GREEN}Step 5: Verifying cluster access...${NC}"
kubectl cluster-info
kubectl get nodes

# Configure firewalld to allow pod-to-pod traffic (if firewalld is active)
echo -e "\n${GREEN}Step 5b: Configuring firewalld for CNI...${NC}"
if ssh "$REMOTE_HOST" "command -v firewall-cmd >/dev/null 2>&1 && sudo firewall-cmd --state | grep -q running"; then
    ssh "$REMOTE_HOST" << 'EOF'
        # cni0 and flannel.1 need to be trusted for pod-to-pod traffic
        sudo firewall-cmd --permanent --zone=trusted --add-interface=cni0 || true
        sudo firewall-cmd --permanent --zone=trusted --add-interface=flannel.1 || true
        sudo firewall-cmd --reload || true
EOF
    echo -e "${GREEN}✅ firewalld updated for CNI${NC}"
else
    echo -e "${YELLOW}⚠️  firewalld not active (skipping)${NC}"
fi

# Install MetalLB
echo -e "\n${GREEN}Step 6: Installing MetalLB...${NC}"
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml

echo "⏳ Waiting for MetalLB controller..."
kubectl wait --namespace metallb-system \
    --for=condition=ready pod \
    --selector=app=metallb,component=controller \
    --timeout=120s

echo "⏳ Waiting for MetalLB speaker..."
kubectl wait --namespace metallb-system \
    --for=condition=ready pod \
    --selector=app=metallb,component=speaker \
    --timeout=120s

echo -e "${GREEN}✅ MetalLB installed${NC}"

# Configure MetalLB with LAN IPs
echo -e "\n${GREEN}Step 7: Configuring MetalLB IP pool (LAN)...${NC}"
kubectl apply -f "$PROJECT_ROOT/infra/k8s/k3s/metallb-lan-config.yaml"
sleep 5

kubectl get ipaddresspool -n metallb-system
kubectl get l2advertisement -n metallb-system

# Install nginx-ingress
echo -e "\n${GREEN}Step 8: Installing nginx-ingress controller...${NC}"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/baremetal/deploy.yaml

echo "⏳ Waiting for ingress-nginx controller..."
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=120s

# Change ingress service to LoadBalancer
kubectl patch svc ingress-nginx-controller -n ingress-nginx \
    -p '{"spec":{"type":"LoadBalancer"}}'

echo "⏳ Waiting for LoadBalancer IP..."
sleep 10
INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}✅ Ingress LoadBalancer IP: $INGRESS_IP${NC}"
else
    echo -e "${YELLOW}⚠️  LoadBalancer IP pending (check MetalLB logs)${NC}"
fi

# Install cert-manager for automatic TLS certificates
echo -e "\n${GREEN}Step 8b: Installing cert-manager...${NC}"
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.yaml

echo "⏳ Waiting for cert-manager to be ready..."
kubectl wait --namespace cert-manager \
    --for=condition=Available \
    deployment/cert-manager \
    --timeout=120s
kubectl wait --namespace cert-manager \
    --for=condition=Available \
    deployment/cert-manager-webhook \
    --timeout=120s

echo -e "${GREEN}✅ cert-manager installed${NC}"

# Build and push images to local Docker registry
echo -e "\n${GREEN}Step 9: Setting up container images (via Registry)...${NC}"

# Check if registry is running
echo "Checking if Docker registry is running on $REMOTE_HOST:5000..."
if ! ssh "$REMOTE_HOST" "docker ps --filter name=registry --format '{{.Names}}' | grep -q '^registry$'"; then
    echo -e "${YELLOW}⚠️  Docker registry not running. Starting it...${NC}"
    ssh "$REMOTE_HOST" << 'EOF'
        docker run -d \
          --name registry \
          --restart=always \
          -p 5000:5000 \
          -v /home/rolf/workspace/eRechnung/eRechnung_Django_App/infra/api-gateway/certs:/certs \
          -e REGISTRY_HTTP_ADDR=0.0.0.0:5000 \
          -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/localhost.crt \
          -e REGISTRY_HTTP_TLS_KEY=/certs/localhost.key \
          registry:2
EOF
    sleep 3
    echo -e "${GREEN}✅ Registry started${NC}"
else
    echo -e "${GREEN}✅ Registry already running${NC}"
fi

# Build images locally
cd "$PROJECT_ROOT"
echo "Building application images..."
docker compose build web init
docker build -f frontend/Dockerfile.prod -t erechnung-frontend:build frontend
docker build -f infra/api-gateway/Dockerfile -t erechnung-api-gateway:build infra/api-gateway
docker build -t erechnung-postgres:build infra/postgres

# Pull and tag base images
echo "Pulling and tagging base images..."
docker pull redis:7-alpine
docker pull busybox:1.35

# Versioned image tag: v<version>-<git-sha>
VERSION=$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
GIT_SHA=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)
TAG="v${VERSION}-${GIT_SHA}"
echo -e "${BLUE}🏷️  Image tag: ${TAG}${NC}"

# Tag all images for registry (versioned tags only — no :latest)
echo "Tagging images for registry (192.168.178.80:5000) with tag ${TAG}..."
docker tag erechnung_django_app-web:latest 192.168.178.80:5000/erechnung-web:$TAG
docker tag erechnung_django_app-init:latest 192.168.178.80:5000/erechnung-init:$TAG
docker tag erechnung_django_app-web:latest 192.168.178.80:5000/erechnung-celery:$TAG
docker tag erechnung-frontend:build 192.168.178.80:5000/erechnung-frontend:$TAG
docker tag erechnung-api-gateway:build 192.168.178.80:5000/erechnung-api-gateway:$TAG
docker tag erechnung-postgres:build 192.168.178.80:5000/erechnung-postgres:$TAG
docker tag redis:7-alpine 192.168.178.80:5000/redis:7-alpine
docker tag busybox:1.35 192.168.178.80:5000/busybox:1.35

# Push to registry
echo "Pushing images to registry..."
docker push 192.168.178.80:5000/erechnung-web:$TAG
docker push 192.168.178.80:5000/erechnung-init:$TAG
docker push 192.168.178.80:5000/erechnung-celery:$TAG
docker push 192.168.178.80:5000/erechnung-frontend:$TAG
docker push 192.168.178.80:5000/erechnung-api-gateway:$TAG
docker push 192.168.178.80:5000/erechnung-postgres:$TAG
docker push 192.168.178.80:5000/redis:7-alpine
docker push 192.168.178.80:5000/busybox:1.35

echo -e "${GREEN}✅ Images transferred${NC}"

# Update kustomization.yaml with versioned tag
echo -e "\n${GREEN}Step 10a: Updating kustomization.yaml with tag ${TAG}...${NC}"
KUSTOMIZATION="$PROJECT_ROOT/infra/k8s/k3s/kustomization.yaml"
python3 - "$KUSTOMIZATION" "$TAG" <<'PYEOF'
import sys, re
kustomization_file = sys.argv[1]
new_tag = sys.argv[2]
with open(kustomization_file, 'r') as f:
    content = f.read()
for img in ['erechnung-web', 'erechnung-init', 'erechnung-celery', 'erechnung-frontend', 'erechnung-api-gateway', 'erechnung-postgres']:
    pattern = r'(- name: [^\n]*/{}[^\n]*\n    newTag: )[^\n]+'.format(re.escape(img))
    content = re.sub(pattern, r'\g<1>' + new_tag, content)
with open(kustomization_file, 'w') as f:
    f.write(content)
print(f"  Updated kustomization.yaml → {new_tag}")
PYEOF

# Deploy application
echo -e "\n${GREEN}Step 10b: Deploying eRechnung application (kustomize)...${NC}"
kubectl apply -k "$PROJECT_ROOT/infra/k8s/k3s"

echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s \
    deployment/postgres -n erechnung || true

kubectl wait --for=condition=available --timeout=300s \
    deployment/redis -n erechnung || true

kubectl wait --for=condition=available --timeout=300s \
    deployment/django-web -n erechnung || true

kubectl wait --for=condition=available --timeout=300s \
    deployment/frontend -n erechnung || true

# Show status
echo -e "\n${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           k3s Setup Complete!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📊 Cluster Status:${NC}"
kubectl get nodes
echo ""
kubectl get pods -n erechnung
echo ""

echo -e "${BLUE}🌐 Access Information:${NC}"
echo "---------------------------------------------------"
if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}LoadBalancer IP: $INGRESS_IP${NC}"
    echo "  https://erechnung.local"
    echo "  https://monitoring.erechnung.local/grafana/"
    echo ""
    echo "From anywhere in your LAN (192.168.178.x):"
    echo "  curl -k https://erechnung.local"
    echo ""
    echo "Add to /etc/hosts:"
    echo "  $INGRESS_IP  erechnung.local monitoring.erechnung.local"
else
    echo "Waiting for LoadBalancer IP assignment..."
    echo "Check: kubectl get svc -n ingress-nginx"
fi
echo "---------------------------------------------------"

echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo "Export kubeconfig:"
echo "  export KUBECONFIG=~/.kube/config-k3s"
echo ""
echo "View logs:"
echo "  kubectl logs -n erechnung -l app=django-web --tail=50 -f"
echo ""
echo "Get services:"
echo "  kubectl get svc -A"
echo ""
echo "Uninstall k3s:"
echo "  ssh $REMOTE_HOST 'sudo /usr/local/bin/k3s-uninstall.sh'"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
