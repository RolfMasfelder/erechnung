#!/bin/bash
# Create TLS Secret for Kubernetes Ingress
# Uses existing certificates from api-gateway/certs
# Part of Phase 1 Security Implementation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERT_DIR="${PROJECT_ROOT}/api-gateway/certs"
NAMESPACE="erechnung"
SECRET_NAME="erechnung-tls-cert"

echo "=================================================="
echo "Creating TLS Secret for Kubernetes Ingress"
echo "=================================================="
echo ""

# Check if certificates exist
if [[ ! -f "${CERT_DIR}/localhost.crt" ]] || [[ ! -f "${CERT_DIR}/localhost.key" ]]; then
    echo "❌ Error: Certificates not found!"
    echo "   Expected: ${CERT_DIR}/localhost.crt"
    echo "            ${CERT_DIR}/localhost.key"
    echo ""
    echo "Run the following command to generate certificates:"
    echo "  cd ${PROJECT_ROOT}/api-gateway && ./generate-certs.sh"
    exit 1
fi

echo "✓ Certificates found:"
echo "  - ${CERT_DIR}/localhost.crt"
echo "  - ${CERT_DIR}/localhost.key"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl not found!"
    echo "   Please install kubectl first."
    exit 1
fi

echo "✓ kubectl found"
echo ""

# Check if namespace exists
if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    echo "⚠️  Warning: Namespace '${NAMESPACE}' does not exist!"
    echo "   Creating namespace..."
    kubectl create namespace "${NAMESPACE}"
    echo "✓ Namespace created"
else
    echo "✓ Namespace '${NAMESPACE}' exists"
fi
echo ""

# Check if secret already exists
if kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
    echo "⚠️  Secret '${SECRET_NAME}' already exists in namespace '${NAMESPACE}'"
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete secret "${SECRET_NAME}" -n "${NAMESPACE}"
        echo "✓ Old secret deleted"
    else
        echo "❌ Aborted. Secret not updated."
        exit 1
    fi
fi
echo ""

# Create TLS secret
echo "Creating TLS secret..."
kubectl create secret tls "${SECRET_NAME}" \
    --cert="${CERT_DIR}/localhost.crt" \
    --key="${CERT_DIR}/localhost.key" \
    -n "${NAMESPACE}"

if [[ $? -eq 0 ]]; then
    echo ""
    echo "=================================================="
    echo "✅ TLS Secret created successfully!"
    echo "=================================================="
    echo ""
    echo "Secret Details:"
    kubectl describe secret "${SECRET_NAME}" -n "${NAMESPACE}"
    echo ""
    echo "Next Steps:"
    echo "1. Update ingress.yaml to use this secret"
    echo "2. Apply the ingress configuration:"
    echo "   kubectl apply -f ${SCRIPT_DIR}/ingress.yaml"
    echo "3. Test HTTPS access:"
    echo "   curl -k https://192.168.178.80/health"
else
    echo ""
    echo "❌ Failed to create TLS secret!"
    exit 1
fi
