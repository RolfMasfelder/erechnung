#!/usr/bin/env bash
# =============================================================================
# eRechnung Docker Update Script
# =============================================================================
# Aktualisiert eine Docker-Compose-Installation von eRechnung.
#
# Ablauf:
#   1. Pre-Flight Checks
#   2. Backup erzwingen + SHA256-Verifizierung
#   3. Alte Images taggen (:pre-update)
#   4. Neue Images ziehen oder lokal bauen
#   5. Graceful Shutdown (10s Grace Period)
#   6. Neustarten: DB/Redis → Init → Web/Celery → Frontend
#   7. Health Check (/health/ + /api/version/)
#   8. Ergebnis-Ausgabe
#
# Usage:
#   ./scripts/update-docker.sh                    # Interaktiv
#   ./scripts/update-docker.sh --version 1.1.0    # Bestimmte Version
#   ./scripts/update-docker.sh --dry-run           # Nur Plan zeigen
#   ./scripts/update-docker.sh --yes               # Keine Bestätigung
#   ./scripts/update-docker.sh --local-build       # Lokal bauen statt pull
#
# Exit-Codes:
#   0 = Update erfolgreich
#   1 = Update fehlgeschlagen
#   2 = Pre-Flight-Check fehlgeschlagen
#   3 = Backup fehlgeschlagen
#   4 = Image-Pull/Build fehlgeschlagen
#   5 = Health-Check fehlgeschlagen
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
GRACE_PERIOD=10
HEALTH_CHECK_TIMEOUT=120
HEALTH_CHECK_INTERVAL=5

# Source pre-flight library
# shellcheck source=lib/preflight.sh
source "$SCRIPT_DIR/lib/preflight.sh"

# --- Defaults ----------------------------------------------------------------
TARGET_VERSION=""
DRY_RUN=false
YES_MODE=false
LOCAL_BUILD=false
SKIP_BACKUP=false

# --- Colors ------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' NC=''
fi

# --- Logging -----------------------------------------------------------------
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/update-$(date +%Y%m%d-%H%M%S).log"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" >> "$LOG_FILE"
}

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; log "INFO: $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; log "WARN: $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; log "ERROR: $*"; }
step()  { echo -e "${CYAN}[STEP]${NC}  ${BOLD}$*${NC}"; log "STEP: $*"; }

# --- Usage -------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Optionen:
  --version <TAG>    Bestimmte Version installieren
  --dry-run          Nur prüfen, keine Änderungen
  --yes              Keine Bestätigungsabfrage
  --local-build      Lokaler Build statt Image-Pull
  --skip-backup      Backup überspringen (nur für Tests!)
  -h, --help         Diese Hilfe anzeigen

Beispiele:
  $(basename "$0") --dry-run              Plan anzeigen
  $(basename "$0") --yes --version 1.1.0  Update auf 1.1.0 ohne Rückfrage
  $(basename "$0") --local-build          Lokalen Build verwenden
EOF
    exit 0
}

# --- Parse Arguments ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)     TARGET_VERSION="$2"; shift 2 ;;
        --dry-run)     DRY_RUN=true; shift ;;
        --yes)         YES_MODE=true; shift ;;
        --local-build) LOCAL_BUILD=true; shift ;;
        --skip-backup) SKIP_BACKUP=true; shift ;;
        -h|--help)     usage ;;
        *)             error "Unbekannte Option: $1"; usage ;;
    esac
done

# --- Cleanup on exit ---------------------------------------------------------
cleanup() {
    local exit_code=$?
    release_update_lock 2>/dev/null || true
    if (( exit_code != 0 )); then
        echo ""
        error "Update fehlgeschlagen (Exit-Code: $exit_code)."
        echo -e "${YELLOW}Zum Zurückrollen: ./scripts/rollback-docker.sh${NC}"
        echo -e "${YELLOW}Log-Datei: ${LOG_FILE}${NC}"
    fi
}
trap cleanup EXIT

# =============================================================================
# Hilfsfunktionen
# =============================================================================

get_current_version() {
    local version
    version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true
    if [[ -z "$version" ]]; then
        version="unknown"
    fi
    echo "$version"
}

get_image_names() {
    # Ermittelt die Image-Namen aller build-basierten Services
    docker compose -f "$COMPOSE_FILE" config --images 2>/dev/null | sort -u
}

tag_pre_update_images() {
    step "Alte Images mit :pre-update taggen..."
    local images
    images=$(get_image_names)
    for image in $images; do
        if docker image inspect "$image" &>/dev/null; then
            local base_name
            base_name="${image%%:*}"
            docker tag "$image" "${base_name}:pre-update" 2>/dev/null && \
                info "  Tagged: ${base_name}:pre-update" || \
                warn "  Konnte $image nicht taggen"
        fi
    done
}

confirm_update() {
    if [[ "$YES_MODE" == true ]]; then
        return 0
    fi
    echo ""
    echo -e "${YELLOW}Soll das Update durchgeführt werden? [j/N]${NC} "
    read -r answer
    case "$answer" in
        [jJyY]) return 0 ;;
        *)
            info "Update abgebrochen."
            exit 0
            ;;
    esac
}

wait_for_health() {
    local url="$1"
    local name="$2"
    local timeout="$3"
    local interval="${4:-$HEALTH_CHECK_INTERVAL}"
    local elapsed=0

    while (( elapsed < timeout )); do
        if curl -sf "$url" &>/dev/null; then
            info "  $name: OK"
            return 0
        fi
        sleep "$interval"
        ((elapsed += interval))
    done

    error "  $name: Timeout nach ${timeout}s"
    return 1
}

enable_maintenance_mode() {
    local maintenance_file="${PROJECT_ROOT}/infra/api-gateway/maintenance.html"
    if [[ -f "$maintenance_file" ]]; then
        info "Wartungsseite ist verfügbar (maintenance.html)"
    fi
}

disable_maintenance_mode() {
    info "Wartungsmodus beendet."
}

# =============================================================================
# Hauptablauf
# =============================================================================
main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         eRechnung Docker Update                 ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    log "=== Update gestartet ==="

    cd "$PROJECT_ROOT"

    # -----------------------------------------------------------------
    # Schritt 1: Pre-Flight Checks
    # -----------------------------------------------------------------
    step "1/8 Pre-Flight Checks..."

    if ! run_docker_preflight "$COMPOSE_FILE"; then
        error "Pre-Flight-Checks fehlgeschlagen. Update abgebrochen."
        exit 2
    fi

    # Lock erwerben
    if ! acquire_update_lock; then
        exit 2
    fi

    # Aktuelle Version ermitteln
    CURRENT_VERSION=$(get_current_version)
    info "Aktuelle Version: $CURRENT_VERSION"

    if [[ -n "$TARGET_VERSION" ]]; then
        info "Ziel-Version: $TARGET_VERSION"
        if [[ "$CURRENT_VERSION" == "$TARGET_VERSION" ]]; then
            info "Bereits auf Version $TARGET_VERSION. Kein Update nötig."
            exit 0
        fi
    else
        info "Ziel-Version: neueste (HEAD/latest)"
    fi

    # -----------------------------------------------------------------
    # Dry-Run: Nur Plan zeigen
    # -----------------------------------------------------------------
    if [[ "$DRY_RUN" == true ]]; then
        echo ""
        echo -e "${BLUE}=== Dry-Run: Update-Plan ===${NC}"
        echo -e "  Aktuelle Version:  ${CURRENT_VERSION}"
        echo -e "  Ziel-Version:      ${TARGET_VERSION:-latest}"
        echo -e "  Build-Methode:     $(if $LOCAL_BUILD; then echo "Lokaler Build"; else echo "Image Pull"; fi)"
        echo -e "  Compose-Datei:     ${COMPOSE_FILE}"
        echo -e "  Backup:            $(if $SKIP_BACKUP; then echo "Übersprungen"; else echo "Ja"; fi)"
        echo -e "  Grace Period:      ${GRACE_PERIOD}s"
        echo ""
        echo -e "  ${YELLOW}Keine Änderungen vorgenommen (--dry-run).${NC}"
        exit 0
    fi

    # Bestätigung einholen
    echo ""
    echo -e "  ${BOLD}Update-Plan:${NC}"
    echo -e "    Von:     ${CURRENT_VERSION}"
    echo -e "    Nach:    ${TARGET_VERSION:-latest}"
    echo -e "    Methode: $(if $LOCAL_BUILD; then echo "Lokaler Build"; else echo "Image Pull"; fi)"
    confirm_update

    # -----------------------------------------------------------------
    # Schritt 2: Backup
    # -----------------------------------------------------------------
    if [[ "$SKIP_BACKUP" == true ]]; then
        warn "Backup wird übersprungen (--skip-backup)."
    else
        step "2/8 Backup erstellen..."
        if ! "$SCRIPT_DIR/backup.sh" --all 2>&1 | tee -a "$LOG_FILE"; then
            error "Backup fehlgeschlagen. Update abgebrochen."
            exit 3
        fi

        # SHA256-Verifizierung des neuesten Backups
        local latest_backup
        latest_backup=$(find "${PROJECT_ROOT}/backups" -name "*.sha256" -type f 2>/dev/null \
            | sort -r | head -1)
        if [[ -n "$latest_backup" ]]; then
            local backup_dir
            backup_dir=$(dirname "$latest_backup")
            if (cd "$backup_dir" && sha256sum -c "$(basename "$latest_backup")" &>/dev/null); then
                info "Backup-Prüfsumme verifiziert."
            else
                error "Backup-Prüfsumme fehlerhaft! Update abgebrochen."
                exit 3
            fi
        fi
        info "Backup erfolgreich erstellt."
    fi

    # -----------------------------------------------------------------
    # Schritt 3: Alte Images taggen
    # -----------------------------------------------------------------
    step "3/8 Alte Images sichern..."
    tag_pre_update_images

    # -----------------------------------------------------------------
    # Schritt 4: Neue Images holen/bauen
    # -----------------------------------------------------------------
    step "4/8 Neue Images $(if $LOCAL_BUILD; then echo "bauen"; else echo "ziehen"; fi)..."
    if [[ "$LOCAL_BUILD" == true ]]; then
        # Version aus pyproject.toml lesen und als Build-Arg übergeben
        local build_version
        build_version=$(python3 -c "import re; m=re.search(r'^version\s*=\s*\"(.+?)\"', open('pyproject.toml').read(), re.M); print(m.group(1) if m else '0.0.0')" 2>/dev/null || echo "0.0.0")
        local build_date
        build_date=$(date -Iseconds)
        local git_sha
        git_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

        info "Build-Version: $build_version (SHA: $git_sha)"
        export APP_VERSION="$build_version"
        export BUILD_DATE="$build_date"
        export GIT_SHA="$git_sha"

        if ! docker compose -f "$COMPOSE_FILE" build --no-cache 2>&1 | tee -a "$LOG_FILE"; then
            error "Lokaler Build fehlgeschlagen."
            exit 4
        fi
        info "Lokaler Build abgeschlossen."
    else
        if ! docker compose -f "$COMPOSE_FILE" pull 2>&1 | tee -a "$LOG_FILE"; then
            error "Image-Pull fehlgeschlagen."
            exit 4
        fi
        info "Images gezogen."
    fi

    # -----------------------------------------------------------------
    # Schritt 5: Graceful Shutdown
    # -----------------------------------------------------------------
    step "5/8 Graceful Shutdown (${GRACE_PERIOD}s Grace Period)..."
    enable_maintenance_mode

    # Frontend und Web zuerst stoppen (die Anwendungsebene)
    info "Stoppe Anwendungs-Container..."
    docker compose -f "$COMPOSE_FILE" stop -t "$GRACE_PERIOD" frontend celery web 2>&1 | tee -a "$LOG_FILE" || true

    # Dann Init stoppen (ist normalerweise schon beendet)
    docker compose -f "$COMPOSE_FILE" stop init 2>&1 | tee -a "$LOG_FILE" || true

    info "Anwendungs-Container gestoppt."

    # -----------------------------------------------------------------
    # Schritt 6: Neustarten in korrekter Reihenfolge
    # -----------------------------------------------------------------
    step "6/8 Container neu starten..."

    # DB und Redis bleiben laufen (oder werden auch neu gestartet bei Image-Änderung)
    info "Starte Infrastruktur (DB, Redis)..."
    docker compose -f "$COMPOSE_FILE" up -d db redis 2>&1 | tee -a "$LOG_FILE"

    # Warten bis DB + Redis healthy
    info "Warte auf Infrastruktur-Health..."
    local db_ready=false
    local redis_ready=false
    for i in $(seq 1 30); do
        if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -q 2>/dev/null; then
            db_ready=true
        fi
        if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
            redis_ready=true
        fi
        if $db_ready && $redis_ready; then
            break
        fi
        sleep 2
    done

    if ! $db_ready; then
        error "Datenbank nicht erreichbar nach 60s."
        exit 5
    fi
    if ! $redis_ready; then
        error "Redis nicht erreichbar nach 60s."
        exit 5
    fi
    info "Infrastruktur bereit."

    # Init-Container (Migrationen, collectstatic)
    info "Starte Init-Container (Migrationen)..."
    docker compose -f "$COMPOSE_FILE" up init 2>&1 | tee -a "$LOG_FILE"
    local init_exit
    init_exit=$(docker compose -f "$COMPOSE_FILE" ps init --format '{{.ExitCode}}' 2>/dev/null || echo "1")
    if [[ "$init_exit" != "0" ]]; then
        error "Init-Container fehlgeschlagen (Exit: $init_exit). Migration fehlerhaft?"
        error "Zum Zurückrollen: ./scripts/rollback-docker.sh"
        exit 5
    fi
    info "Migrationen abgeschlossen."

    # Web + Celery starten
    info "Starte Web + Celery..."
    docker compose -f "$COMPOSE_FILE" up -d web celery 2>&1 | tee -a "$LOG_FILE"

    # Frontend starten
    info "Starte Frontend..."
    docker compose -f "$COMPOSE_FILE" up -d frontend 2>&1 | tee -a "$LOG_FILE"

    disable_maintenance_mode

    # -----------------------------------------------------------------
    # Schritt 7: Health Checks
    # -----------------------------------------------------------------
    step "7/8 Health Checks..."

    info "Warte auf Backend..."
    if ! wait_for_health "http://localhost:8000/health/" "Backend Health" "$HEALTH_CHECK_TIMEOUT"; then
        error "Backend-Health-Check fehlgeschlagen."
        exit 5
    fi

    if ! wait_for_health "http://localhost:8000/api/version/" "Version API" 30; then
        error "Version-API nicht erreichbar."
        exit 5
    fi

    # Neue Version auslesen
    NEW_VERSION=$(get_current_version)
    info "Neue Version: $NEW_VERSION"

    # -----------------------------------------------------------------
    # Schritt 8: Ergebnis
    # -----------------------------------------------------------------
    step "8/8 Ergebnis"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Update erfolgreich!                     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Vorherige Version: ${CURRENT_VERSION}"
    echo -e "  Neue Version:      ${NEW_VERSION}"
    echo -e "  Log-Datei:         ${LOG_FILE}"
    echo ""
    echo -e "  ${YELLOW}Bei Problemen: ./scripts/rollback-docker.sh${NC}"
    echo ""

    log "=== Update erfolgreich: $CURRENT_VERSION → $NEW_VERSION ==="
}

main "$@"
