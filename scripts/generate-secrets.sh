#!/bin/bash
# Generate secure secrets for eRechnung deployment
#
# Creates properly randomized secrets for:
#   - Django SECRET_KEY
#   - Database passwords
#   - Redis password (optional)
#
# Outputs:
#   - .env file for Docker Compose
#   - k8s secret YAML for Kubernetes
#
# Usage:
#   cd scripts && ./generate-secrets.sh           # Generate .env
#   cd scripts && ./generate-secrets.sh --k8s     # Also generate K8s secret
#   cd scripts && ./generate-secrets.sh --rotate  # Rotate existing secrets
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_TEMPLATE="$PROJECT_ROOT/.env.example"
K8S_SECRET_FILE="$PROJECT_ROOT/infra/infra/k8s/k3s/manifests/11-secret-erechnung-secrets.yaml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
GENERATE_K8S=false
GENERATE_DOCKER_SECRETS=false
ROTATE_MODE=false
for arg in "$@"; do
    case "$arg" in
        --k8s) GENERATE_K8S=true ;;
        --docker-secrets) GENERATE_DOCKER_SECRETS=true ;;
        --rotate) ROTATE_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--k8s] [--docker-secrets] [--rotate]"
            echo ""
            echo "Options:"
            echo "  --k8s              Also generate Kubernetes secret manifest"
            echo "  --docker-secrets   Also generate secrets/ files for docker-compose.production.yml"
            echo "  --rotate           Rotate secrets (backup existing, generate new)"
            echo ""
            exit 0
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   eRechnung Secure Secret Generator           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Generate Secure Random Values ───────────────────────────────────

generate_secret() {
    local length="${1:-50}"
    # Use /dev/urandom for cryptographically secure randomness
    python3 -c "
import secrets
import string
chars = string.ascii_letters + string.digits + '!@#%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range($length)))
"
}

generate_django_key() {
    python3 -c "
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
" 2>/dev/null || generate_secret 50
}

generate_password() {
    local length="${1:-32}"
    # Password-safe characters (no quotes, no backslash, no dollar)
    python3 -c "
import secrets
import string
chars = string.ascii_letters + string.digits + '!@#%^&*(-_=+)'
# Ensure at least one of each type
pw = [
    secrets.choice(string.ascii_uppercase),
    secrets.choice(string.ascii_lowercase),
    secrets.choice(string.digits),
    secrets.choice('!@#%^&*(-_=+)')
]
pw.extend(secrets.choice(chars) for _ in range($length - 4))
import random
random.SystemRandom().shuffle(pw)
print(''.join(pw))
"
}

echo -e "${GREEN}Generating secure random secrets...${NC}"

DJANGO_SECRET_KEY=$(generate_django_key)
DB_PASSWORD=$(generate_password 32)
REDIS_PASSWORD=$(generate_password 24)

echo -e "${GREEN}✅ Secrets generated${NC}"

# ─── Backup Existing Secrets ─────────────────────────────────────────

if [ "$ROTATE_MODE" = true ] && [ -f "$ENV_FILE" ]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo -e "${YELLOW}📋 Existing .env backed up to: $BACKUP_FILE${NC}"
fi

# ─── Check for Existing .env ─────────────────────────────────────────

if [ -f "$ENV_FILE" ] && [ "$ROTATE_MODE" != true ]; then
    echo -e "${YELLOW}⚠️  .env already exists: $ENV_FILE${NC}"

    # Check if it contains placeholder values
    if grep -q "CHANGE_ME" "$ENV_FILE" 2>/dev/null; then
        echo "  Contains placeholder values - will be replaced."
    elif grep -q "ci-dummy" "$ENV_FILE" 2>/dev/null || grep -q "insecure" "$ENV_FILE" 2>/dev/null; then
        echo "  Contains insecure development values."
        read -p "  Replace with secure values? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
    else
        read -p "  Overwrite? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
    fi
fi

# ─── Generate .env ───────────────────────────────────────────────────

echo -e "\n${GREEN}Generating .env file...${NC}"

cat > "$ENV_FILE" << ENVEOF
# eRechnung Environment Configuration
# Generated: $(date -Iseconds)
# ⚠️  DO NOT COMMIT THIS FILE TO GIT!

# Django Configuration
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,0.0.0.0
APP_VERSION=dev

# Database Configuration (Docker Compose)
DB_NAME=erechnung
DB_USER=erechnung_user
DB_PASSWORD=$DB_PASSWORD
DB_HOST=db
DB_PORT=5432

# PostgreSQL Configuration (Container)
POSTGRES_DB=erechnung
POSTGRES_USER=erechnung_user
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0

# Docker Environment
IS_DOCKER=true
BEHIND_GATEWAY=false
PYTHONPATH=/app/project_root

# External Tools
GHOSTSCRIPT_PATH=/usr/bin/gs

# Testing (only for development)
TESTING_MODE=false
ENVEOF

chmod 600 "$ENV_FILE"
echo -e "${GREEN}✅ .env generated: $ENV_FILE (permissions: 600)${NC}"

# ─── Generate Kubernetes Secret ──────────────────────────────────────

if [ "$GENERATE_K8S" = true ]; then
    echo -e "\n${GREEN}Generating Kubernetes secret manifest...${NC}"

    # Base64 encode secrets
    B64_DJANGO_KEY=$(echo -n "$DJANGO_SECRET_KEY" | base64 -w0)
    B64_DB_USER=$(echo -n "erechnung_user" | base64 -w0)
    B64_DB_PASSWORD=$(echo -n "$DB_PASSWORD" | base64 -w0)
    B64_DB_NAME=$(echo -n "erechnung" | base64 -w0)

    cat > "$K8S_SECRET_FILE" << SECRETEOF
# Secret für sensitive Daten
# Generated: $(date -Iseconds)
# ⚠️  Re-generate for production: cd scripts && ./generate-secrets.sh --k8s
apiVersion: v1
kind: Secret
metadata:
  name: erechnung-secrets
  namespace: erechnung
type: Opaque
data:
  DJANGO_SECRET_KEY: $B64_DJANGO_KEY
  DB_USER: $B64_DB_USER
  DB_PASSWORD: $B64_DB_PASSWORD
  POSTGRES_USER: $B64_DB_USER
  POSTGRES_PASSWORD: $B64_DB_PASSWORD
  POSTGRES_DB: $B64_DB_NAME
SECRETEOF

    echo -e "${GREEN}✅ K8s secret manifest generated: $K8S_SECRET_FILE${NC}"
    echo -e "${YELLOW}⚠️  Remember: This file contains real secrets!${NC}"
    echo -e "${YELLOW}    In production, use External Secrets Operator or Sealed Secrets.${NC}"
fi

# ─── Generate Docker Secrets Files ───────────────────────────────────

if [ "$GENERATE_DOCKER_SECRETS" = true ]; then
    echo -e "\n${GREEN}Generating Docker Secrets files...${NC}"

    SECRETS_DIR="$PROJECT_ROOT/secrets"
    mkdir -p "$SECRETS_DIR"

    echo -n "$DJANGO_SECRET_KEY" > "$SECRETS_DIR/django_secret_key"
    echo -n "$DB_PASSWORD"       > "$SECRETS_DIR/postgres_password"
    echo -n "erechnung_user"     > "$SECRETS_DIR/postgres_user"
    echo -n "erechnung"          > "$SECRETS_DIR/postgres_db"

    chmod 600 "$SECRETS_DIR"/*
    echo -e "${GREEN}✅ Docker Secrets files generated in: $SECRETS_DIR/${NC}"
    echo -e "${YELLOW}⚠️  These files contain real secrets — never commit them!${NC}"
    echo -e "    Use with: docker compose -f docker-compose.production.yml up"
fi

# ─── Seed K8s Secret-Store Namespace (for ESO) ──────────────────────

if [ "$GENERATE_K8S" = true ]; then
    echo -e "\n${GREEN}Seeding secret-store namespace for External Secrets Operator...${NC}"
    echo -e "${YELLOW}  (Requires: kubectl access + secret-store namespace)${NC}"

    # Create the namespace if it doesn't exist
    kubectl create namespace secret-store --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

    # Create the source secret that ESO reads from
    kubectl create secret generic erechnung-secrets \
        --namespace=secret-store \
        --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
        --from-literal=DB_USER="erechnung_user" \
        --from-literal=DB_PASSWORD="$DB_PASSWORD" \
        --from-literal=POSTGRES_USER="erechnung_user" \
        --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
        --from-literal=POSTGRES_DB="erechnung" \
        --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Secrets seeded in secret-store namespace${NC}"
        echo -e "${YELLOW}  ESO will sync these to erechnung namespace automatically.${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not seed secret-store (kubectl not available?)${NC}"
        echo -e "    Run manually: kubectl apply -f <generated-secret.yaml>"
    fi
fi

# ─── Verify .env in .gitignore ───────────────────────────────────────

echo -e "\n${GREEN}Checking .gitignore...${NC}"

GITIGNORE="$PROJECT_ROOT/.gitignore"
NEEDS_UPDATE=false

for pattern in ".env" ".env.local" ".env.production" "*.backup.*"; do
    if [ -f "$GITIGNORE" ] && ! grep -qF "$pattern" "$GITIGNORE"; then
        NEEDS_UPDATE=true
        break
    fi
done

if [ "$NEEDS_UPDATE" = true ]; then
    echo -e "${YELLOW}⚠️  Adding secret patterns to .gitignore...${NC}"
    cat >> "$GITIGNORE" << 'GITEOF'

# Secret files (never commit!)
.env.local
.env.production
*.backup.*
GITEOF
    echo -e "${GREEN}✅ .gitignore updated${NC}"
else
    echo -e "${GREEN}✅ .gitignore already covers secret files${NC}"
fi

# ─── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Secret Generation Complete!                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Generated Secrets:${NC}"
echo "  Django SECRET_KEY:  ${DJANGO_SECRET_KEY:0:12}...  (${#DJANGO_SECRET_KEY} chars)"
echo "  DB Password:        ${DB_PASSWORD:0:8}...  (${#DB_PASSWORD} chars)"
echo ""
echo -e "${GREEN}Files:${NC}"
echo "  .env            → Docker Compose secrets"
if [ "$GENERATE_K8S" = true ]; then
    echo "  infra/k8s/k3s/manifests/11-secret-erechnung-secrets.yaml → K8s secrets"
fi
if [ "$GENERATE_DOCKER_SECRETS" = true ]; then
    echo "  secrets/        → Docker Secrets files (for docker-compose.production.yml)"
fi
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "  • .env has file permissions 600 (owner read/write only)"
echo "  • Never commit .env with real secrets to Git"
echo "  • For production K8s: Use External Secrets Operator"
echo "  • Rotate secrets periodically: $0 --rotate"
echo ""
echo -e "${GREEN}✅ Done!${NC}"
