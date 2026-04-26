#!/bin/bash
# Install Calico Network Policy Provider for kind cluster
# kind does not include a network policy provider by default
# Part of Phase 1 Security Implementation (Network Policies)

set -e

# Using v3.27.0 (stable, tested with kind)
# v3.31.0 has DNS resolution issues in some kind environments
CALICO_VERSION="v3.27.0"
CALICO_MANIFEST="https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/calico.yaml"

echo "=================================================="
echo "Installing Calico Network Policy Provider"
echo "Version: ${CALICO_VERSION}"
echo "=================================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl not found!"
    echo "   Please install kubectl first."
    exit 1
fi

echo "✓ kubectl found"
echo ""

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot access Kubernetes cluster!"
    echo "   Make sure your kind cluster is running:"
    echo "   kind get clusters"
    exit 1
fi

echo "✓ Kubernetes cluster accessible"
echo ""

# Check if Calico is already installed
if kubectl get daemonset calico-node -n kube-system &> /dev/null; then
    echo "⚠️  Calico appears to be already installed"
    kubectl get pods -n kube-system -l k8s-app=calico-node
    echo ""
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✓ Using existing Calico installation"
        exit 0
    fi
fi

# Download and apply Calico manifest
echo "Downloading Calico manifest from:"
echo "  ${CALICO_MANIFEST}"
echo ""

kubectl apply -f "${CALICO_MANIFEST}"

if [[ $? -ne 0 ]]; then
    echo ""
    echo "❌ Failed to install Calico!"
    exit 1
fi

echo ""
echo "Waiting for Calico pods to be ready..."
echo "(This may take 1-2 minutes)"
echo ""

# Wait for Calico pods to be ready
kubectl wait --for=condition=ready pod \
    -l k8s-app=calico-node \
    -n kube-system \
    --timeout=180s

echo ""
echo "=================================================="
echo "✅ Calico installed successfully!"
echo "=================================================="
echo ""

# Show Calico pod status
echo "Calico Components:"
kubectl get pods -n kube-system -l k8s-app=calico-node
echo ""
kubectl get pods -n kube-system -l k8s-app=calico-kube-controllers
echo ""

# Test network policy support
echo "Testing Network Policy support..."
cat <<EOF | kubectl apply -f - &> /dev/null
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: test-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      test: test
  policyTypes:
  - Ingress
EOF

if kubectl get networkpolicy test-network-policy -n default &> /dev/null; then
    echo "✓ Network Policy API is working"
    kubectl delete networkpolicy test-network-policy -n default &> /dev/null
else
    echo "⚠️  Network Policy API test failed"
fi

echo ""
echo "Next Steps:"
echo "1. Create Network Policies:"
echo "   kubectl apply -f $(dirname "${BASH_SOURCE[0]}")/network-policies.yaml"
echo "2. Verify policies are applied:"
echo "   kubectl get networkpolicies -n erechnung"
echo "3. Test connectivity to ensure policies work as expected"
