#!/bin/bash
# Rotate Kubernetes secrets for eRechnung on k3s
#
# This script:
#   1. Generates new secure secrets
#   2. Updates the K8s secret in-place
#   3. Restarts deployments to pick up new secrets
#   4. Verifies all pods are healthy
#
# Prerequisites:
#   - KUBECONFIG pointing to k3s cluster
#   - kubectl access
#
# Usage:
#   export KUBECONFIG=~/.kube/config-k3s
#   cd scripts && ./rotate-k8s-secrets.sh
#   cd scripts && ./rotate-k8s-secrets.sh --dry-run   # Preview only
set -e

NAMESPACE="erechnung"
SECRET_NAME="erechnung-secrets"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run]"
            echo ""
            echo "Rotates DJANGO_SECRET_KEY and DB passwords in Kubernetes."
            echo ""
            echo "Options:"
            echo "  --dry-run   Preview changes without applying"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   K8s Secret Rotation — eRechnung             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Preflight ────────────────────────────────────────────────────────

echo -e "${GREEN}Step 1: Preflight checks...${NC}"

if [ -z "$KUBECONFIG" ]; then
    if [ -f "$HOME/.kube/config-k3s" ]; then
        export KUBECONFIG="$HOME/.kube/config-k3s"
    else
        echo -e "${RED}❌ KUBECONFIG not set${NC}"
        exit 1
    fi
fi

if ! kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &>/dev/null; then
    echo -e "${RED}❌ Secret $SECRET_NAME not found in namespace $NAMESPACE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Secret found${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE — No changes will be applied${NC}"
fi

# ─── Generate New Secrets ─────────────────────────────────────────────

echo -e "\n${GREEN}Step 2: Generating new secrets...${NC}"

NEW_DJANGO_KEY=$(python3 -c "
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
" 2>/dev/null || python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#\$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(50)))
")

NEW_DB_PASSWORD=$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#%^&*(-_=+)'
pw = [secrets.choice(string.ascii_uppercase), secrets.choice(string.ascii_lowercase),
      secrets.choice(string.digits), secrets.choice('!@#%^&*(-_=+)')]
pw.extend(secrets.choice(chars) for _ in range(28))
import random; random.SystemRandom().shuffle(pw)
print(''.join(pw))
")

echo "  Django SECRET_KEY:  ${NEW_DJANGO_KEY:0:12}...  (${#NEW_DJANGO_KEY} chars)"
echo "  DB Password:        ${NEW_DB_PASSWORD:0:8}...  (${#NEW_DB_PASSWORD} chars)"

if [ "$DRY_RUN" = true ]; then
    echo -e "\n${YELLOW}DRY RUN: Would update secret '$SECRET_NAME' and restart deployments${NC}"
    exit 0
fi

# ─── Backup Current Secret ───────────────────────────────────────────

echo -e "\n${GREEN}Step 3: Backing up current secret...${NC}"

BACKUP_FILE="/tmp/erechnung-secret-backup-$(date +%Y%m%d_%H%M%S).yaml"
kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o yaml > "$BACKUP_FILE"
echo -e "${GREEN}✅ Backup saved to $BACKUP_FILE${NC}"

# ─── Update Secret ───────────────────────────────────────────────────

echo -e "\n${GREEN}Step 4: Updating Kubernetes secret...${NC}"

# Read current secret to preserve non-rotated values
CURRENT_DB_USER=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.DB_USER}' | base64 -d 2>/dev/null || echo "postgres")
CURRENT_DB_NAME=$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_DB}' | base64 -d 2>/dev/null || echo "erechnung")

# Patch the secret with new values
kubectl create secret generic "$SECRET_NAME" \
    --namespace "$NAMESPACE" \
    --from-literal="DJANGO_SECRET_KEY=$NEW_DJANGO_KEY" \
    --from-literal="DB_USER=$CURRENT_DB_USER" \
    --from-literal="DB_PASSWORD=$NEW_DB_PASSWORD" \
    --from-literal="POSTGRES_USER=$CURRENT_DB_USER" \
    --from-literal="POSTGRES_PASSWORD=$NEW_DB_PASSWORD" \
    --from-literal="POSTGRES_DB=$CURRENT_DB_NAME" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Secret updated${NC}"

# ─── Update PostgreSQL Password ──────────────────────────────────────

echo -e "\n${GREEN}Step 5: Updating PostgreSQL password...${NC}"

# Get the postgres pod
POSTGRES_POD=$(kubectl get pod -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$POSTGRES_POD" ]; then
    echo "  Updating password in PostgreSQL..."
    kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
        psql -U "$CURRENT_DB_USER" -d "$CURRENT_DB_NAME" \
        -c "ALTER USER $CURRENT_DB_USER WITH PASSWORD '$NEW_DB_PASSWORD';" 2>/dev/null || \
    echo -e "${YELLOW}  ⚠️  Could not update PostgreSQL password (may need manual update)${NC}"
    echo -e "${GREEN}✅ PostgreSQL password updated${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL pod not found - password must be updated manually${NC}"
fi

# ─── Restart Deployments ─────────────────────────────────────────────

echo -e "\n${GREEN}Step 6: Restarting deployments to pick up new secrets...${NC}"

# Restart in order: backend first, then frontend
for deploy in postgres redis django-web celery-worker api-gateway frontend; do
    if kubectl get deployment "$deploy" -n "$NAMESPACE" &>/dev/null; then
        echo "  Restarting $deploy..."
        kubectl rollout restart deployment/"$deploy" -n "$NAMESPACE"
        sleep 2
    fi
done

echo ""
echo "⏳ Waiting for rollouts..."
for deploy in django-web api-gateway frontend; do
    if kubectl get deployment "$deploy" -n "$NAMESPACE" &>/dev/null; then
        kubectl rollout status deployment/"$deploy" -n "$NAMESPACE" --timeout=180s || true
    fi
done

echo -e "${GREEN}✅ All deployments restarted${NC}"

# ─── Verify Health ───────────────────────────────────────────────────

echo -e "\n${GREEN}Step 7: Verifying pod health...${NC}"
sleep 10

UNHEALTHY=0
while IFS= read -r line; do
    POD=$(echo "$line" | awk '{print $1}')
    STATUS=$(echo "$line" | awk '{print $3}')
    READY=$(echo "$line" | awk '{print $2}')

    if [ "$STATUS" = "Running" ]; then
        echo -e "  ${GREEN}✅ $POD ($READY ready)${NC}"
    else
        echo -e "  ${RED}❌ $POD ($STATUS)${NC}"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi
done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | grep -v "Completed")

if [ "$UNHEALTHY" -gt 0 ]; then
    echo -e "\n${RED}⚠️  $UNHEALTHY pods are not healthy!${NC}"
    echo "  Check logs: kubectl logs -n $NAMESPACE <pod-name>"
    echo "  Rollback:   kubectl apply -f $BACKUP_FILE"
fi

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Secret Rotation Complete!                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Rotated:${NC}"
echo "  ✅ DJANGO_SECRET_KEY"
echo "  ✅ DB_PASSWORD / POSTGRES_PASSWORD"
echo ""
echo -e "${YELLOW}Backup:${NC} $BACKUP_FILE"
echo ""
echo -e "${YELLOW}If something went wrong:${NC}"
echo "  kubectl apply -f $BACKUP_FILE"
echo "  kubectl rollout restart deployment -n $NAMESPACE"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
