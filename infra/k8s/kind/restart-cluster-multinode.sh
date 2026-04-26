#!/bin/bash
set -e

echo "🗑️  Deleting existing kind cluster..."
ssh -o StrictHostKeyChecking=no rolf@192.168.178.80 'kind delete cluster --name erechnung' || true

echo ""
echo "🏗️  Creating multi-node kind cluster (1 control-plane + 2 workers)..."
echo "   Simplified config ohne kubeadm-patches (Standard kind-Verhalten)"
ssh -o StrictHostKeyChecking=no rolf@192.168.178.80 'cat > /tmp/kind-config.yaml << '\''EOF'\''
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: erechnung
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      certSANs:
      - "192.168.178.80"
  extraPortMappings:
  - containerPort: 6443
    hostPort: 6443
    protocol: TCP
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
- role: worker
- role: worker
networking:
  disableDefaultCNI: true
  podSubnet: 192.168.0.0/16
EOF
kind create cluster --config /tmp/kind-config.yaml'

# Configure containerd registry for all nodes (post-creation)
echo ""
echo "🔧 Configuring containerd registry on all nodes..."
for node in erechnung-control-plane erechnung-worker erechnung-worker2; do
  echo "→ Configuring $node..."
  ssh -o StrictHostKeyChecking=no rolf@192.168.178.80 "docker exec $node mkdir -p /etc/containerd/certs.d/192.168.178.80:5000"
  ssh -o StrictHostKeyChecking=no rolf@192.168.178.80 "docker exec $node sh -c 'cat > /etc/containerd/certs.d/192.168.178.80:5000/hosts.toml <<EOF
server = \"https://192.168.178.80:5000\"

[host.\"https://192.168.178.80:5000\"]
  capabilities = [\"pull\", \"resolve\"]
  skip_verify = true
EOF
'"
  ssh -o StrictHostKeyChecking=no rolf@192.168.178.80 "docker exec $node systemctl restart containerd"
done
echo "✅ containerd registry configured on all nodes!"

echo ""
echo "✅ Multi-node cluster created!"
echo ""
echo "📊 Cluster nodes:"
kubectl get nodes -o wide

echo ""
echo "🔧 Next steps:"
echo "1. Install Calico: ./fix-calico-remote.sh"
echo "2. Deploy app: kubectl apply -f k8s-erechnung-local.yaml"
echo "3. Apply Network Policies: kubectl apply -f network-policies.yaml"
