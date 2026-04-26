#!/bin/bash
# Setup script for deploying eRechnung to kind cluster
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Setting up eRechnung in kind cluster..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo -e "${RED}❌ kind is not installed. Please install it first:${NC}"
    echo "   https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed. Please install it first.${NC}"
    exit 1
fi

# Function to wait for deployment
wait_for_deployment() {
    local namespace=$1
    local deployment=$2
    local timeout=${3:-300}

    echo "⏳ Waiting for deployment/$deployment in namespace $namespace..."
    kubectl wait --for=condition=available --timeout=${timeout}s \
        deployment/$deployment -n $namespace 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Deployment $deployment not ready yet, checking pods...${NC}"
        kubectl get pods -n $namespace
    }
}

# Step 1: Create kind cluster
echo -e "\n${GREEN}Step 1: Creating kind cluster...${NC}"
if kind get clusters 2>/dev/null | grep -q "^erechnung$"; then
    echo -e "${YELLOW}⚠️  Cluster 'erechnung' already exists.${NC}"
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kind delete cluster --name erechnung
        kind create cluster --config "$SCRIPT_DIR/kind-cluster-config.yaml"
    fi
else
    kind create cluster --config "$SCRIPT_DIR/kind-cluster-config.yaml"
fi

# Step 2: Install nginx-ingress controller
echo -e "\n${GREEN}Step 2: Installing nginx-ingress controller...${NC}"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ingress-nginx to be ready
echo "⏳ Waiting for ingress-nginx namespace and resources..."
sleep 5  # Give k8s time to create resources

# Wait for deployment to exist
echo "Waiting for ingress-nginx-controller deployment..."
until kubectl get deployment -n ingress-nginx ingress-nginx-controller &> /dev/null; do
    echo -n "."
    sleep 2
done
echo " found!"

# Now wait for pods to be ready
echo "Waiting for ingress-nginx pods to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s || {
    echo -e "${YELLOW}⚠️  Timeout waiting for ingress-nginx, checking status...${NC}"
    kubectl get pods -n ingress-nginx
}

# Fix: Ensure ingress-controller runs on node with port mappings (multi-node clusters)
echo -e "\n${GREEN}Configuring ingress for multi-node setup...${NC}"
# Label control-plane node for ingress (if not already labeled)
kubectl label node erechnung-control-plane ingress-ready=true --overwrite || true
# Patch ingress-controller to use nodeSelector for control-plane
kubectl patch deployment ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}' || true
echo "⏳ Waiting for ingress-controller to reschedule..."
sleep 10
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=60s || echo -e "${YELLOW}⚠️  Ingress not yet ready${NC}"

# Step 2.5: Install MetalLB (optional)
echo -e "\n${GREEN}Step 2.5: MetalLB LoadBalancer (optional)${NC}"
echo "MetalLB provides production-like LoadBalancer services."
echo "Without MetalLB, hostPort mapping is used (development only)."
read -p "Install MetalLB? (recommended for production-like setup) [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Installing MetalLB v0.14.8..."
    kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml

    echo "⏳ Waiting for MetalLB controller..."
    kubectl wait --namespace metallb-system \
      --for=condition=ready pod \
      --selector=app=metallb,component=controller \
      --timeout=120s || {
        echo -e "${YELLOW}⚠️  MetalLB not ready yet${NC}"
    }

    echo "⏳ Waiting for MetalLB speaker..."
    kubectl wait --namespace metallb-system \
      --for=condition=ready pod \
      --selector=app=metallb,component=speaker \
      --timeout=120s || {
        echo -e "${YELLOW}⚠️  MetalLB not ready yet${NC}"
    }

    echo "Configuring MetalLB IP pool..."
    kubectl apply -f "$SCRIPT_DIR/metallb-config.yaml"
    sleep 5

    # Configure Ingress-Controller as LoadBalancer
    echo "Configuring ingress-controller as LoadBalancer..."
    kubectl patch svc ingress-nginx-controller -n ingress-nginx \
      -p '{"spec":{"type":"LoadBalancer"}}'

    echo "⏳ Waiting for LoadBalancer IP assignment..."
    sleep 10
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        echo -e "${GREEN}✅ Ingress LoadBalancer IP: ${INGRESS_IP}${NC}"
    else
        echo -e "${YELLOW}⚠️  LoadBalancer IP pending (check metallb-config.yaml IP range)${NC}"
    fi
else
    # Optimize ingress-controller service (ClusterIP is sufficient with hostPort)
    echo -e "\n${GREEN}Using hostPort mode (no MetalLB)...${NC}"
    kubectl patch svc ingress-nginx-controller -n ingress-nginx \
      -p '{"spec":{"type":"ClusterIP"}}' || true
fi

# Step 3: Update secrets (optional)
echo -e "\n${GREEN}Step 3: Configuring secrets...${NC}"
echo -e "${YELLOW}📝 Using default secrets from k8s-erechnung.yaml${NC}"
echo "   For production, update these with:"
echo "   echo -n 'your-secret' | base64"

# Step 4: Deploy application
echo -e "\n${GREEN}Step 4: Building and loading local Docker images...${NC}"
if [ -f "$SCRIPT_DIR/build-and-load-images.sh" ]; then
    "$SCRIPT_DIR/build-and-load-images.sh"
else
    echo -e "${YELLOW}⚠️  build-and-load-images.sh not found, skipping image build${NC}"
fi

# Step 5: Deploy application
echo -e "\n${GREEN}Step 5: Deploying eRechnung application...${NC}"

# Use kind-specific manifest with local images
if [ -f "$SCRIPT_DIR/k8s-erechnung-local.yaml" ]; then
    echo "Using kind-specific manifest with local images..."
    kubectl apply -f "$SCRIPT_DIR/k8s-erechnung-local.yaml"
else
    echo "Using main k8s-erechnung.yaml (may have image pull issues)..."
    kubectl apply -f "$K8S_DIR/k8s-erechnung.yaml"
fi

# Override with kind-specific configurations
kubectl apply -f "$SCRIPT_DIR/api-gateway-service.yaml"
kubectl apply -f "$SCRIPT_DIR/ingress.yaml"

# Step 6: Wait for deployments
echo -e "\n${GREEN}Step 6: Waiting for deployments to be ready...${NC}"
echo "⏳ This may take a few minutes for image pulls..."

# Wait for PostgreSQL
wait_for_deployment erechnung postgres

# Wait for Redis
wait_for_deployment erechnung redis

# Wait for Django
wait_for_deployment erechnung django-web

# Wait for API Gateway
wait_for_deployment erechnung api-gateway

# Step 7: Show status
echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo -e "\n${GREEN}📊 Cluster Status:${NC}"
kubectl get all -n erechnung

# Step 7: Show status
echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo -e "\n${GREEN}📊 Cluster Status:${NC}"
kubectl get all -n erechnung

echo -e "\n${GREEN}🌐 Access Information:${NC}"
echo "---------------------------------------------------"

# Check if MetalLB is installed
if kubectl get namespace metallb-system &> /dev/null; then
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

    if [ -n "$INGRESS_IP" ]; then
        echo "LoadBalancer Mode (MetalLB):"
        echo "  http://$INGRESS_IP"
        echo "  http://erechnung.local (add to DNS/hosts)"
        echo ""
        echo "Add to /etc/hosts:"
        echo "  $INGRESS_IP api.erechnung.local"
        echo "  $INGRESS_IP erechnung.local"
    else
        echo "LoadBalancer IP pending - check:"
        echo "  kubectl get svc -n ingress-nginx"
        echo "  kubectl logs -n metallb-system -l app=metallb"
    fi
else
    echo "HostPort Mode (Development):"
    echo "  http://localhost"
    echo "  http://api.erechnung.local"
    echo ""
    echo "Remote access (if running on remote machine):"
    echo "  http://192.168.178.80"
    echo ""
    echo "Add to /etc/hosts for hostname access:"
    echo "  127.0.0.1 api.erechnung.local"
fi
echo ""
echo "Port-forward alternative:"
echo "  kubectl port-forward -n erechnung svc/api-gateway-service 8080:80"
echo "  Then access: http://localhost:8080"
echo "---------------------------------------------------"

# Step 8: Show logs helper
echo -e "\n${GREEN}📝 Useful commands:${NC}"
echo "View logs:"
echo "  kubectl logs -n erechnung -l app=django-web --tail=50 -f"
echo "  kubectl logs -n erechnung -l app=api-gateway --tail=50 -f"
echo ""
echo "Get pod status:"
echo "  kubectl get pods -n erechnung"
echo ""
echo "Execute commands in Django pod:"
echo "  kubectl exec -it -n erechnung deployment/django-web -- python project_root/manage.py shell"
echo ""
echo "Delete cluster:"
echo "  kind delete cluster --name erechnung"
