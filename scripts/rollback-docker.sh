#!/usr/bin/env bash
# =============================================================================
# eRechnung Docker Rollback Script
# =============================================================================
# Stellt eine vorherige Version der Docker-Installation wieder her.
#
# Ablauf:
#   1. Container stoppen
#   2. :pre-update Images als aktive Images taggen
#   3. DB aus Backup wiederherstellen
#   4. Container starten
#   5. Health Check
#
# Usage:
#   ./scripts/rollback-docker.sh                        # Standard-Rollback
#   ./scripts/rollback-docker.sh --backup <PFAD>        # Bestimmtes Backup
#   ./scripts/rollback-docker.sh --db-only              # Nur DB, keine Images
#   ./scripts/rollback-docker.sh --images-only          # Nur Images, keine DB
#
# Exit-Codes:
#   0 = Rollback erfolgreich
#   1 = Rollback fehlgeschlagen
#   2 = Pre-Flight fehlgeschlagen
#   3 = DB-Restore fehlgeschlagen
#   4 = Health-Check fehlgeschlagen
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
HEALTH_CHECK_TIMEOUT=120
HEALTH_CHECK_INTERVAL=5

# Source pre-flight library
# shellcheck source=lib/preflight.sh
source "$SCRIPT_DIR/lib/preflight.sh"

# --- Defaults ----------------------------------------------------------------
BACKUP_PATH=""
DB_ONLY=false
IMAGES_ONLY=false
YES_MODE=false

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
LOG_FILE="${LOG_DIR}/rollback-$(date +%Y%m%d-%H%M%S).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; log "INFO: $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; log "WARN: $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; log "ERROR: $*"; }
step()  { echo -e "${CYAN}[STEP]${NC}  ${BOLD}$*${NC}"; log "STEP: $*"; }

# --- Usage -------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Optionen:
  --backup <PFAD>    Bestimmtes Backup verwenden (statt Pre-Update)
  --db-only          Nur Datenbank zurückrollen, keine Images
  --images-only      Nur Images zurückrollen, keine DB
  --yes              Keine Bestätigungsabfrage
  -h, --help         Diese Hilfe anzeigen

Beispiele:
  $(basename "$0")                                Standard-Rollback
  $(basename "$0") --backup backups/20260317      Bestimmtes Backup
  $(basename "$0") --db-only                      Nur DB-Rollback
EOF
    exit 0
}

# --- Parse Arguments ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup)       BACKUP_PATH="$2"; shift 2 ;;
        --db-only)      DB_ONLY=true; shift ;;
        --images-only)  IMAGES_ONLY=true; shift ;;
        --yes)          YES_MODE=true; shift ;;
        -h|--help)      usage ;;
        *)              error "Unbekannte Option: $1"; usage ;;
    esac
done

# --- Hilfsfunktionen --------------------------------------------------------

confirm_rollback() {
    if [[ "$YES_MODE" == true ]]; then
        return 0
    fi
    echo ""
    echo -e "${RED}ACHTUNG: Der Rollback setzt die Anwendung auf den vorherigen Stand zurück!${NC}"
    echo -e "${YELLOW}Fortfahren? [j/N]${NC} "
    read -r answer
    case "$answer" in
        [jJyY]) return 0 ;;
        *)
            info "Rollback abgebrochen."
            exit 0
            ;;
    esac
}

restore_pre_update_images() {
    step "Images auf :pre-update zurücksetzen..."
    local images
    images=$(docker compose -f "$COMPOSE_FILE" config --images 2>/dev/null | sort -u)
    local restored=0

    for image in $images; do
        local base_name
        base_name="${image%%:*}"
        if docker image inspect "${base_name}:pre-update" &>/dev/null; then
            docker tag "${base_name}:pre-update" "$image" 2>/dev/null && \
                info "  Restored: ${base_name}:pre-update → $image" && \
                ((restored++)) || \
                warn "  Konnte ${base_name}:pre-update nicht wiederherstellen"
        else
            warn "  Kein :pre-update Tag für ${base_name}"
        fi
    done

    if (( restored == 0 )); then
        error "Keine :pre-update Images gefunden. Kann Images nicht zurücksetzen."
        return 1
    fi
    info "$restored Image(s) zurückgesetzt."
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

find_latest_backup() {
    local backup_dir="${PROJECT_ROOT}/backups"
    if [[ -d "$backup_dir" ]]; then
        find "$backup_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -r | head -1
    fi
}

# =============================================================================
# Hauptablauf
# =============================================================================
main() {
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║         eRechnung Docker Rollback               ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    log "=== Rollback gestartet ==="

    cd "$PROJECT_ROOT"

    # -----------------------------------------------------------------
    # Pre-Flight
    # -----------------------------------------------------------------
    step "1/5 Pre-Flight Checks..."
    check_docker_running || exit 2
    check_compose_file_exists "$COMPOSE_FILE" || exit 2

    # Aktuellen Stand loggen
    local current_version
    current_version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || current_version="unknown"
    info "Aktuelle Version: $current_version"

    # Backup ermitteln
    if [[ -z "$BACKUP_PATH" && "$IMAGES_ONLY" != true ]]; then
        BACKUP_PATH=$(find_latest_backup)
        if [[ -z "$BACKUP_PATH" ]]; then
            error "Kein Backup gefunden. Verwende --backup <PFAD> oder --images-only."
            exit 3
        fi
        info "Verwende neustes Backup: $BACKUP_PATH"
    fi

    confirm_rollback

    # -----------------------------------------------------------------
    # Schritt 2: Container stoppen
    # -----------------------------------------------------------------
    step "2/5 Container stoppen..."
    docker compose -f "$COMPOSE_FILE" stop -t 10 frontend celery web init 2>&1 | tee -a "$LOG_FILE" || true
    info "Anwendungs-Container gestoppt."

    # -----------------------------------------------------------------
    # Schritt 3: Images zurücksetzen
    # -----------------------------------------------------------------
    if [[ "$DB_ONLY" != true ]]; then
        step "3/5 Images zurücksetzen..."
        restore_pre_update_images || warn "Image-Rollback teilweise fehlgeschlagen."
    else
        info "3/5 Image-Rollback übersprungen (--db-only)."
    fi

    # -----------------------------------------------------------------
    # Schritt 4: Datenbank wiederherstellen
    # -----------------------------------------------------------------
    if [[ "$IMAGES_ONLY" != true ]]; then
        step "4/5 Datenbank aus Backup wiederherstellen..."
        if [[ ! -d "$BACKUP_PATH" ]]; then
            # Resolve relative path
            if [[ ! "$BACKUP_PATH" = /* ]]; then
                BACKUP_PATH="${PROJECT_ROOT}/${BACKUP_PATH}"
            fi
        fi
        if [[ ! -d "$BACKUP_PATH" ]]; then
            error "Backup-Verzeichnis nicht gefunden: $BACKUP_PATH"
            exit 3
        fi

        if ! "$SCRIPT_DIR/restore.sh" --force --skip-pre-backup --db-only "$BACKUP_PATH" 2>&1 | tee -a "$LOG_FILE"; then
            error "DB-Restore fehlgeschlagen."
            exit 3
        fi
        info "Datenbank wiederhergestellt."
    else
        info "4/5 DB-Restore übersprungen (--images-only)."
    fi

    # -----------------------------------------------------------------
    # Schritt 5: Container starten + Health Check
    # -----------------------------------------------------------------
    step "5/5 Container starten und prüfen..."

    # Sicherstellen dass DB + Redis laufen
    docker compose -f "$COMPOSE_FILE" up -d db redis 2>&1 | tee -a "$LOG_FILE"
    sleep 5

    # Init-Container (Migrationen für die alte Version)
    info "Starte Init-Container..."
    docker compose -f "$COMPOSE_FILE" up init 2>&1 | tee -a "$LOG_FILE"

    # Web + Celery + Frontend starten
    docker compose -f "$COMPOSE_FILE" up -d web celery frontend 2>&1 | tee -a "$LOG_FILE"

    # Health Check
    info "Warte auf Backend..."
    if ! wait_for_health "http://localhost:8000/health/" "Backend Health" "$HEALTH_CHECK_TIMEOUT"; then
        error "Backend-Health-Check nach Rollback fehlgeschlagen!"
        exit 4
    fi

    local rolled_back_version
    rolled_back_version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || rolled_back_version="unknown"

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Rollback erfolgreich!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Version vor Rollback: ${current_version}"
    echo -e "  Version nach Rollback: ${rolled_back_version}"
    echo -e "  Log-Datei: ${LOG_FILE}"
    echo ""

    log "=== Rollback erfolgreich: $current_version → $rolled_back_version ==="
}

main "$@"
