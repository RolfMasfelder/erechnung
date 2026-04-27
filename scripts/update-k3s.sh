#!/usr/bin/env bash
# =============================================================================
# eRechnung K3s Update Script
# =============================================================================
# Aktualisiert eine K3s-Installation von eRechnung mit Zero-Downtime.
#
# Ablauf:
#   1. Pre-Flight Checks (Cluster-Health, Nodes Ready)
#   2. Backup (pg_dump aus Postgres-Pod)
#   3. Images bauen, taggen und in Registry pushen
#   4. kustomization.yaml aktualisieren
#   5. Migrations-Job deployen + warten
#   6. Bei Migration-Fehler: ABBRUCH
#   7. kubectl apply -k (Rolling Update)
#   8. Rollout-Status überwachen (Timeout 300s)
#   9. Post-Update Verification
#  10. Cleanup (alte Jobs, dangling Images)
#
# Usage:
#   ./scripts/update-k3s.sh                      # Interaktiv
#   ./scripts/update-k3s.sh --version 1.1.0      # Bestimmte Version
#   ./scripts/update-k3s.sh --build-only          # Nur Images bauen
#   ./scripts/update-k3s.sh --dry-run             # Nur Plan zeigen
#   ./scripts/update-k3s.sh --skip-backup         # Backup überspringen
#   ./scripts/update-k3s.sh --yes                 # Keine Bestätigung
#
# Exit-Codes:
#   0 = Update erfolgreich
#   1 = Update fehlgeschlagen
#   2 = Pre-Flight-Check fehlgeschlagen
#   3 = Backup fehlgeschlagen
#   4 = Image-Build/Push fehlgeschlagen
#   5 = Migration fehlgeschlagen
#   6 = Rollout fehlgeschlagen
#   7 = Post-Update Verification fehlgeschlagen
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KUSTOMIZATION="$PROJECT_ROOT/infra/k8s/k3s/kustomization.yaml"
MIGRATE_JOB="$PROJECT_ROOT/infra/k8s/k3s/manifests/41-job-django-migrate-template.yaml"
NAMESPACE="erechnung"
REGISTRY="${K3S_REGISTRY:-192.168.178.80:5000}"
ROLLOUT_TIMEOUT=300
HEALTH_CHECK_TIMEOUT=120
HEALTH_CHECK_INTERVAL=5

# Source pre-flight library
# shellcheck source=lib/preflight.sh
source "$SCRIPT_DIR/lib/preflight.sh"

# --- Defaults ----------------------------------------------------------------
TARGET_VERSION=""
DRY_RUN=false
YES_MODE=false
BUILD_ONLY=false
SKIP_BACKUP=false
SKIP_BUILD=false

# --- Colors ------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# --- Kubeconfig --------------------------------------------------------------
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-k3s}"

# =============================================================================
# Usage
# =============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Optionen:
  --version <TAG>   Bestimmte Version (Standard: auto aus pyproject.toml + git sha)
  --build-only      Nur Images bauen und pushen (kein Deploy)
  --dry-run         Nur Plan zeigen, keine Änderungen
  --skip-backup     Backup überspringen (nur für Testumgebung)
  --skip-build      Build überspringen (Images müssen bereits in Registry sein)
  --yes             Keine Bestätigungsabfrage
  -h, --help        Diese Hilfe anzeigen

Exit-Codes:
  0  Update erfolgreich
  1  Allgemeiner Fehler
  2  Pre-Flight-Check fehlgeschlagen
  3  Backup fehlgeschlagen
  4  Image-Build/Push fehlgeschlagen
  5  Migration fehlgeschlagen
  6  Rollout fehlgeschlagen
  7  Post-Update Verification fehlgeschlagen
EOF
    exit 0
}

# =============================================================================
# Argument-Parsing
# =============================================================================
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)     TARGET_VERSION="$2"; shift 2 ;;
        --build-only)  BUILD_ONLY=true; shift ;;
        --dry-run)     DRY_RUN=true; shift ;;
        --skip-backup) SKIP_BACKUP=true; shift ;;
        --skip-build)  SKIP_BUILD=true; shift ;;
        --yes)         YES_MODE=true; shift ;;
        -h|--help)     usage ;;
        *)
            echo -e "${RED}Unbekannte Option: $1${NC}" >&2
            usage
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }
step()  { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

confirm() {
    if [[ "$YES_MODE" == true || "$DRY_RUN" == true ]]; then
        return 0
    fi
    echo ""
    read -r -p "Fortfahren? [j/N] " response
    case "$response" in
        [jJyY]*) return 0 ;;
        *) echo "Abgebrochen."; exit 0 ;;
    esac
}

get_image_tag() {
    if [[ -n "$TARGET_VERSION" ]]; then
        echo "v${TARGET_VERSION}"
    else
        local version git_sha
        version=$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
        git_sha=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)
        echo "v${version}-${git_sha}"
    fi
}

get_current_k3s_version() {
    kubectl exec -n "$NAMESPACE" deploy/django-web -c django-web -- \
        python -c "from importlib.metadata import version; print(version('erechnung'))" 2>/dev/null || echo "unknown"
}

cleanup_on_exit() {
    release_update_lock 2>/dev/null || true
}
trap cleanup_on_exit EXIT

# =============================================================================
# Step 0: Banner + Version Info
# =============================================================================
IMAGE_TAG=$(get_image_tag)

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      eRechnung K3s Update                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Image-Tag:    ${BLUE}${IMAGE_TAG}${NC}"
echo -e "  Registry:     ${REGISTRY}"
echo -e "  Namespace:    ${NAMESPACE}"
echo -e "  Kubeconfig:   ${KUBECONFIG}"
echo -e "  Dry-Run:      ${DRY_RUN}"

# =============================================================================
# Step 1: Pre-Flight Checks
# =============================================================================
step "Step 1: Pre-Flight Checks"

if ! run_k3s_preflight; then
    error "Pre-Flight-Checks fehlgeschlagen."
    exit 2
fi

# Registry check
if ! curl -k -s "https://$REGISTRY/v2/" > /dev/null 2>&1; then
    error "Registry nicht erreichbar: $REGISTRY"
    exit 2
fi
info "Registry erreichbar: $REGISTRY"

# Kubeconfig check
if [[ ! -f "$KUBECONFIG" ]]; then
    error "Kubeconfig nicht gefunden: $KUBECONFIG"
    exit 2
fi
info "Kubeconfig vorhanden: $KUBECONFIG"

# Acquire update lock
if ! acquire_update_lock; then
    exit 2
fi

# Show current version
CURRENT_VERSION=$(get_current_k3s_version)
echo ""
echo -e "  Aktuelle Version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "  Ziel-Tag:         ${GREEN}${IMAGE_TAG}${NC}"

if [[ "$DRY_RUN" == true ]]; then
    echo ""
    info "Dry-Run: Keine Änderungen werden vorgenommen."
    echo ""
    echo "Geplante Aktionen:"
    echo "  1. Backup der PostgreSQL-Datenbank"
    echo "  2. Images bauen und pushen (Tag: $IMAGE_TAG)"
    echo "  3. kustomization.yaml aktualisieren"
    echo "  4. Migrations-Job ausführen"
    echo "  5. Rolling Update deployen"
    echo "  6. Rollout überwachen"
    echo "  7. Post-Update Verification"
    release_update_lock
    exit 0
fi

confirm

# =============================================================================
# Step 2: Backup
# =============================================================================
step "Step 2: PostgreSQL Backup"

if [[ "$SKIP_BACKUP" == true ]]; then
    warn "Backup übersprungen (--skip-backup)."
else
    BACKUP_DIR="$PROJECT_ROOT/test-artifacts/k3s-backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre-update-$(date +%Y%m%d-%H%M%S).sql.gz"

    POSTGRES_POD=$(kubectl get pod -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -z "$POSTGRES_POD" ]]; then
        error "Kein Postgres-Pod gefunden."
        exit 3
    fi

    info "Erstelle Backup von Pod: $POSTGRES_POD"
    if kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" -- \
        sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip' \
        > "$BACKUP_FILE" 2>/dev/null; then

        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        info "Backup erstellt: $BACKUP_FILE ($BACKUP_SIZE)"

        # SHA256 verification
        BACKUP_SHA=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)
        echo "$BACKUP_SHA  $BACKUP_FILE" > "${BACKUP_FILE}.sha256"
        info "SHA256: $BACKUP_SHA"
    else
        error "Backup fehlgeschlagen."
        exit 3
    fi
fi

# =============================================================================
# Step 3: Build & Push Images
# =============================================================================
step "Step 3: Images bauen und pushen"

if [[ "$SKIP_BUILD" == true ]]; then
    warn "Build übersprungen (--skip-build)."
else
    cd "$PROJECT_ROOT"

    # Build all images
    info "Baue Application Images..."
    docker compose build web init

    info "Baue Frontend..."
    docker build -f frontend/Dockerfile.prod -t erechnung-frontend:build frontend

    info "Baue API-Gateway..."
    docker build -f infra/api-gateway/Dockerfile -t erechnung-api-gateway:build infra/api-gateway

    info "Baue Postgres (mit pgTAP)..."
    docker build -t erechnung-postgres:build infra/postgres

    # Tag and push
    info "Tagge und pushe Images (Tag: $IMAGE_TAG)..."
    COMPOSE_PROJECT_NAME=$(grep -oP '(?<=^name: ).*' docker-compose.yml 2>/dev/null || echo "erechnung")

    tag_and_push() {
        local name="$1" local_tag="$2"
        docker tag "$local_tag" "$REGISTRY/$name:$IMAGE_TAG"
        docker tag "$local_tag" "$REGISTRY/$name:latest"
        docker push "$REGISTRY/$name:$IMAGE_TAG"
        docker push "$REGISTRY/$name:latest"
        echo -e "    ${GREEN}→${NC} $name:$IMAGE_TAG"
    }

    tag_and_push "erechnung-web"         "${COMPOSE_PROJECT_NAME}-web:latest"
    tag_and_push "erechnung-init"        "${COMPOSE_PROJECT_NAME}-init:latest"
    tag_and_push "erechnung-celery"      "${COMPOSE_PROJECT_NAME}-web:latest"
    tag_and_push "erechnung-frontend"    "erechnung-frontend:build"
    tag_and_push "erechnung-api-gateway" "erechnung-api-gateway:build"
    tag_and_push "erechnung-postgres"    "erechnung-postgres:build"

    info "Alle Images gepusht."
fi

if [[ "$BUILD_ONLY" == true ]]; then
    info "Build-Only Modus — Deploy wird übersprungen."
    release_update_lock
    exit 0
fi

# =============================================================================
# Step 4: Update kustomization.yaml
# =============================================================================
step "Step 4: kustomization.yaml aktualisieren"

python3 - "$KUSTOMIZATION" "$IMAGE_TAG" <<'PYEOF'
import sys, re

kustomization_file = sys.argv[1]
new_tag = sys.argv[2]

with open(kustomization_file, 'r') as f:
    content = f.read()

self_built_images = [
    'erechnung-web', 'erechnung-init', 'erechnung-celery',
    'erechnung-frontend', 'erechnung-api-gateway', 'erechnung-postgres',
]

for img in self_built_images:
    pattern = r'(- name: [^\n]*/{}[^\n]*\n    newTag: )[^\n]+'.format(re.escape(img))
    replacement = r'\g<1>' + new_tag
    content = re.sub(pattern, replacement, content)

with open(kustomization_file, 'w') as f:
    f.write(content)

print(f"  Updated kustomization.yaml → {new_tag}")
PYEOF

info "kustomization.yaml aktualisiert auf $IMAGE_TAG"

# =============================================================================
# Step 5: Migrations-Job
# =============================================================================
step "Step 5: Migrations-Job ausführen"

# Delete old migration job (jobs are immutable)
kubectl delete job django-migrate -n "$NAMESPACE" --ignore-not-found=true

# Apply the migration job (kustomize will set the image tag)
kubectl apply -f "$MIGRATE_JOB"

info "Warte auf Migrations-Job (Timeout: 300s)..."
if ! kubectl wait --for=condition=complete job/django-migrate -n "$NAMESPACE" --timeout=300s; then
    error "Migrations-Job fehlgeschlagen oder Timeout!"
    echo ""
    echo -e "${RED}Migration-Logs:${NC}"
    kubectl logs -n "$NAMESPACE" -l component=migration --tail=50 2>/dev/null || true
    echo ""
    error "Update abgebrochen. Datenbank wurde NICHT verändert (Transaktionsschutz)."
    error "Backup verfügbar unter: ${BACKUP_FILE:-'(kein Backup)'}"
    exit 5
fi

info "Migrationen erfolgreich abgeschlossen."

# =============================================================================
# Step 6: Rolling Update deployen
# =============================================================================
step "Step 6: Rolling Update deployen"

# Delete init job (will be recreated with new image)
kubectl delete job django-init -n "$NAMESPACE" --ignore-not-found=true

# Apply all manifests via kustomize
kubectl apply -k "$PROJECT_ROOT/infra/k8s/k3s/"

# Wait for init job (collectstatic + optional bootstrap)
info "Warte auf Init-Job..."
kubectl wait --for=condition=complete job/django-init -n "$NAMESPACE" --timeout=120s || {
    warn "Init-Job fehlgeschlagen — prüfe Logs:"
    kubectl logs -n "$NAMESPACE" -l job-name=django-init --tail=20 2>/dev/null || true
}

# =============================================================================
# Step 7: Rollout überwachen
# =============================================================================
step "Step 7: Rollout überwachen (Timeout: ${ROLLOUT_TIMEOUT}s)"

ROLLOUT_FAILED=false

for deployment in django-web celery-worker frontend api-gateway; do
    echo -ne "  ${BLUE}→${NC} $deployment ... "
    if kubectl rollout status "deployment/$deployment" -n "$NAMESPACE" --timeout="${ROLLOUT_TIMEOUT}s" 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        ROLLOUT_FAILED=true
    fi
done

if [[ "$ROLLOUT_FAILED" == true ]]; then
    error "Mindestens ein Rollout ist fehlgeschlagen."
    echo ""
    echo -e "${YELLOW}Rollback-Optionen:${NC}"
    echo "  kubectl rollout undo deployment/django-web -n $NAMESPACE"
    echo "  kubectl rollout undo deployment/celery-worker -n $NAMESPACE"
    echo "  kubectl rollout undo deployment/frontend -n $NAMESPACE"
    echo "  kubectl rollout undo deployment/api-gateway -n $NAMESPACE"
    exit 6
fi

info "Alle Rollouts erfolgreich."

# =============================================================================
# Step 8: Post-Update Verification
# =============================================================================
step "Step 8: Post-Update Verification"

VERIFY_FAILED=false

# Check that all pods are running
NOT_READY=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Succeeded -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.phase}{"\n"}{end}' 2>/dev/null | grep -v "Running" | grep -v "^$" || true)
if [[ -n "$NOT_READY" ]]; then
    warn "Nicht alle Pods sind Running:"
    echo "$NOT_READY"
    VERIFY_FAILED=true
else
    info "Alle Pods sind Running."
fi

# Health check via API Gateway
echo -ne "  Health-Check (API Gateway) ... "
HEALTH_OK=false
for ((i=0; i<HEALTH_CHECK_TIMEOUT/HEALTH_CHECK_INTERVAL; i++)); do
    # Try both via ingress and direct service
    if kubectl exec -n "$NAMESPACE" deploy/api-gateway -- \
        wget -qO- --timeout=5 "http://localhost:8080/gateway-health" &>/dev/null; then
        HEALTH_OK=true
        break
    fi
    sleep "$HEALTH_CHECK_INTERVAL"
done

if [[ "$HEALTH_OK" == true ]]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    VERIFY_FAILED=true
fi

# Version check
echo -ne "  Version-Check ... "
NEW_VERSION=$(get_current_k3s_version)
if [[ "$NEW_VERSION" != "unknown" ]]; then
    echo -e "${GREEN}$NEW_VERSION${NC}"
else
    echo -e "${YELLOW}konnte nicht ermittelt werden${NC}"
fi

if [[ "$VERIFY_FAILED" == true ]]; then
    warn "Post-Update Verification: Einige Checks fehlgeschlagen."
    warn "Prüfen Sie die Logs: kubectl logs -n $NAMESPACE -l app=django-web --tail=20"
    exit 7
fi

# =============================================================================
# Step 9: Cleanup
# =============================================================================
step "Step 9: Cleanup"

# Clean up completed migration jobs (keep last 2)
COMPLETED_JOBS=$(kubectl get jobs -n "$NAMESPACE" -l component=migration \
    --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
JOB_COUNT=$(echo "$COMPLETED_JOBS" | wc -w)
if (( JOB_COUNT > 2 )); then
    OLD_JOBS=$(echo "$COMPLETED_JOBS" | tr ' ' '\n' | head -n $((JOB_COUNT - 2)))
    for job in $OLD_JOBS; do
        kubectl delete job "$job" -n "$NAMESPACE" --ignore-not-found=true
        echo -e "  ${YELLOW}→${NC} Alter Job gelöscht: $job"
    done
fi

info "Cleanup abgeschlossen."

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Update erfolgreich abgeschlossen!        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Version:   ${GREEN}${NEW_VERSION:-$IMAGE_TAG}${NC}"
echo -e "  Image-Tag: ${BLUE}${IMAGE_TAG}${NC}"
echo ""
echo -e "${BLUE}📊 Status:${NC}"
kubectl get pods -n "$NAMESPACE"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo "  kubectl logs -n $NAMESPACE -l app=django-web --tail=20 -f"
echo ""
echo -e "${YELLOW}Rollback bei Problemen:${NC}"
echo "  kubectl rollout undo deployment/django-web -n $NAMESPACE"
echo "  kubectl rollout undo deployment/celery-worker -n $NAMESPACE"
echo "  kubectl rollout undo deployment/frontend -n $NAMESPACE"
echo "  kubectl rollout undo deployment/api-gateway -n $NAMESPACE"
