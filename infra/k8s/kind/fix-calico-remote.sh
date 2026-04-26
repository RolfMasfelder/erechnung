#!/bin/bash
# Remote Calico DNS Issue Fix für kind auf 192.168.178.80
# Führt fix-calico-dns-issue.sh via SSH auf Remote-Host aus

set -e

REMOTE_HOST="192.168.178.80"
REMOTE_USER="${USER}"  # Verwendet aktuellen User
CALICO_VERSION="v3.27.0"
KIND_CLUSTER_NAME="erechnung"

echo "=================================================="
echo "Remote Calico Fix für kind@${REMOTE_HOST}"
echo "Version: ${CALICO_VERSION}"
echo "=================================================="
echo ""

# Prüfe SSH-Verbindung
echo "Testing SSH connection to ${REMOTE_HOST}..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${REMOTE_USER}@${REMOTE_HOST}" "echo 'SSH OK'" &> /dev/null; then
    echo "❌ Error: Cannot connect to ${REMOTE_HOST} via SSH!"
    echo "   Please ensure:"
    echo "   1. SSH key is in ssh-agent: ssh-add ~/.ssh/your_key"
    echo "   2. Host is reachable: ping ${REMOTE_HOST}"
    exit 1
fi

echo "✓ SSH connection successful"
echo ""

# Prüfe ob kind auf Remote-Host verfügbar ist
echo "Checking kind cluster on remote host..."
if ! ssh "${REMOTE_USER}@${REMOTE_HOST}" "kind get clusters | grep -q '^${KIND_CLUSTER_NAME}$'"; then
    echo "❌ Error: kind cluster '${KIND_CLUSTER_NAME}' not found on ${REMOTE_HOST}!"
    echo ""
    echo "Available clusters:"
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "kind get clusters"
    exit 1
fi

echo "✓ kind cluster '${KIND_CLUSTER_NAME}' found"
echo ""

# Calico Images (beide Registries: quay.io und docker.io)
# Calico verwendet beide je nach Installation
IMAGES=(
    "quay.io/calico/cni:${CALICO_VERSION}"
    "quay.io/calico/node:${CALICO_VERSION}"
    "quay.io/calico/kube-controllers:${CALICO_VERSION}"
    "docker.io/calico/cni:${CALICO_VERSION}"
    "docker.io/calico/node:${CALICO_VERSION}"
    "docker.io/calico/kube-controllers:${CALICO_VERSION}"
)

echo "Pulling and loading Calico images on remote host..."
echo ""

for IMAGE in "${IMAGES[@]}"; do
    echo "→ Processing: ${IMAGE}"

    # Pull auf Remote-Host
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "docker pull ${IMAGE}"

    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to pull: ${IMAGE}"
        exit 1
    fi

    # Load in kind auf Remote-Host
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "kind load docker-image ${IMAGE} --name ${KIND_CLUSTER_NAME}"

    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to load: ${IMAGE}"
        exit 1
    fi

    echo "✓ Image loaded: ${IMAGE}"
    echo ""
done

echo "=================================================="
echo "✅ All Calico images loaded on remote cluster!"
echo "=================================================="
echo ""

# Calico Pods neu starten (kubectl läuft lokal gegen Remote-Cluster)
echo "Restarting Calico pods..."
kubectl delete pods -n kube-system -l k8s-app=calico-node
kubectl delete pods -n kube-system -l k8s-app=calico-kube-controllers

echo ""
echo "Waiting for Calico pods to be ready..."
echo "(This may take 1-2 minutes)"
echo ""

# Warte bis Pods ready sind
kubectl wait --for=condition=ready pod \
    -l k8s-app=calico-node \
    -n kube-system \
    --timeout=180s || true

kubectl wait --for=condition=ready pod \
    -l k8s-app=calico-kube-controllers \
    -n kube-system \
    --timeout=180s || true

echo ""
echo "=================================================="
echo "✅ Calico should now be running!"
echo "=================================================="
echo ""

# Status anzeigen
echo "Calico Node Pods:"
kubectl get pods -n kube-system -l k8s-app=calico-node
echo ""
echo "Calico Controller:"
kubectl get pods -n kube-system -l k8s-app=calico-kube-controllers
echo ""

# Network Policy Test
echo "Testing Network Policy support..."
cat <<EOF | kubectl apply -f - &> /dev/null || true
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
echo "1. Apply Network Policies:"
echo "   kubectl apply -f network-policies.yaml"
echo "2. Verify policies:"
echo "   kubectl get networkpolicies -n erechnung"
