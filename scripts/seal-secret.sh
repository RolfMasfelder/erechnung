#!/usr/bin/env bash
# seal-secret.sh — Wrapper for kubeseal (Bitnami Sealed Secrets)
#
# Usage:
#   scripts/seal-secret.sh <secret-name> <namespace> <key> <value>
#
# Example (Alertmanager SMTP password):
#   scripts/seal-secret.sh alertmanager-smtp monitoring smtp_password 'MyP@ssw0rd'
#
# Output:
#   infra/k8s/k3s/secrets/<secret-name>.sealed.yaml
#
# Prerequisites:
#   - kubeseal CLI installed (https://github.com/bitnami-labs/sealed-secrets#kubeseal)
#   - kubectl configured for target cluster
#   - sealed-secrets-controller running in kube-system namespace
#
# See: docs/arc42/adrs/ADR-012-secrets-management-strategy.md

set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <secret-name> <namespace> <key> <value>" >&2
  exit 1
fi

SECRET_NAME="$1"
NAMESPACE="$2"
KEY="$3"
VALUE="$4"
OUTPUT="infra/k8s/k3s/secrets/${SECRET_NAME}.sealed.yaml"

# Check kubeseal is available
if ! command -v kubeseal &>/dev/null; then
  echo "ERROR: kubeseal is not installed." >&2
  echo "Install from: https://github.com/bitnami-labs/sealed-secrets/releases" >&2
  echo "" >&2
  echo "On Linux (amd64):" >&2
  echo "  KUBESEAL_VERSION=0.27.0" >&2
  echo "  curl -Lo kubeseal https://github.com/bitnami-labs/sealed-secrets/releases/download/v\${KUBESEAL_VERSION}/kubeseal-\${KUBESEAL_VERSION}-linux-amd64.tar.gz" >&2
  echo "  # or: sudo apt-get install kubeseal  (if repo is configured)" >&2
  exit 1
fi

echo "Sealing secret '${SECRET_NAME}' in namespace '${NAMESPACE}'..."
kubectl create secret generic "${SECRET_NAME}" \
  --namespace="${NAMESPACE}" \
  --from-literal="${KEY}=${VALUE}" \
  --dry-run=client \
  -o yaml \
  | kubeseal \
      --controller-namespace kube-system \
      --controller-name sealed-secrets-controller \
      -o yaml \
  > "${OUTPUT}"

echo "Written to: ${OUTPUT}"
echo "Add to git: git add ${OUTPUT} && git commit -m 'feat(secrets): seal ${SECRET_NAME}'"
echo "NEVER commit the plaintext value!"
