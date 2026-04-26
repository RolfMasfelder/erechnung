#!/bin/bash
set -e

echo "🗑️  Deleting existing kind cluster..."
ssh -o StrictHostKeyChecking=no rmasfelder@192.168.178.80 'kind delete cluster --name erechnung' || true

echo ""
echo "🏗️  Creating fresh single-node kind cluster..."
ssh -o StrictHostKeyChecking=no rmasfelder@192.168.178.80 'cat > /tmp/kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: erechnung
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
networking:
  disableDefaultCNI: true
  podSubnet: 192.168.0.0/16
EOF
kind create cluster --config /tmp/kind-config.yaml'

echo ""
echo "✅ Cluster created!"
echo ""
echo "📊 Cluster status:"
kubectl get nodes -o wide

echo ""
echo "🔧 Next steps:"
echo "1. Install Calico: cd /home/rolf/workspace/eRechnung/eRechnung_Django_App/k8s/kind && ./fix-calico-remote.sh"
echo "2. Deploy app: kubectl apply -f k8s-erechnung-local.yaml"
echo "3. Apply Network Policies: kubectl apply -f network-policies.yaml"
