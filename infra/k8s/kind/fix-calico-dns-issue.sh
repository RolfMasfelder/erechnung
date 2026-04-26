#!/bin/bash
# Workaround für Calico ImagePullBackOff in kind
# Problem: DNS-Resolution in kind funktioniert nicht zuverlässig
# Lösung: Images manuell pullen und in kind laden

set -e

CALICO_VERSION="v3.27.0"
KIND_CLUSTER_NAME="erechnung"

echo "=================================================="
echo "Calico DNS Issue Workaround für kind"
echo "Version: ${CALICO_VERSION}"
echo "=================================================="
echo ""

# Prüfe ob Docker verfügbar ist
if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker not found!"
    exit 1
fi

echo "✓ Docker found"
echo ""

# Prüfe ob kind Cluster läuft
if ! kind get clusters | grep -q "^${KIND_CLUSTER_NAME}$"; then
    echo "❌ Error: kind cluster '${KIND_CLUSTER_NAME}' not found!"
    echo "   Available clusters:"
    kind get clusters
    exit 1
fi

echo "✓ kind cluster '${KIND_CLUSTER_NAME}' found"
echo ""

# Calico Images
IMAGES=(
    "quay.io/calico/cni:${CALICO_VERSION}"
    "quay.io/calico/node:${CALICO_VERSION}"
    "quay.io/calico/kube-controllers:${CALICO_VERSION}"
)

echo "Pulling Calico images from Docker Hub..."
echo ""

for IMAGE in "${IMAGES[@]}"; do
    echo "→ Pulling: ${IMAGE}"
    docker pull "${IMAGE}"

    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to pull: ${IMAGE}"
        exit 1
    fi

    echo "→ Loading into kind cluster: ${KIND_CLUSTER_NAME}"
    kind load docker-image "${IMAGE}" --name "${KIND_CLUSTER_NAME}"

    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to load: ${IMAGE}"
        exit 1
    fi

    echo "✓ Image loaded: ${IMAGE}"
    echo ""
done

echo "=================================================="
echo "✅ All Calico images loaded into kind cluster!"
echo "=================================================="
echo ""

# Calico Pods neu starten
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
    --timeout=180s

kubectl wait --for=condition=ready pod \
    -l k8s-app=calico-kube-controllers \
    -n kube-system \
    --timeout=180s

echo ""
echo "=================================================="
echo "✅ Calico is now running!"
echo "=================================================="
echo ""

# Status anzeigen
kubectl get pods -n kube-system -l k8s-app=calico-node
echo ""
kubectl get pods -n kube-system -l k8s-app=calico-kube-controllers
echo ""

echo "Next Steps:"
echo "1. Apply Network Policies:"
echo "   kubectl apply -f $(dirname "${BASH_SOURCE[0]}")/network-policies.yaml"
echo "2. Verify policies:"
echo "   kubectl get networkpolicies -n erechnung"
