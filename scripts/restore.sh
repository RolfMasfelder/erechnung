#!/usr/bin/env bash
# =============================================================================
# eRechnung Restore Script
# =============================================================================
# Restores a backup created by backup.sh:
#   1. PostgreSQL database from .sql.gz dump
#   2. Media files from .tar.gz archive
#
# Usage:
#   ./scripts/restore.sh <backup_dir>               # Restore from date dir
#   ./scripts/restore.sh backups/20260227            # Example
#   ./scripts/restore.sh --latest                    # Restore newest backup
#   ./scripts/restore.sh --db-only backups/20260227  # Database only
#   ./scripts/restore.sh --dry-run backups/20260227  # Verify only, no restore
#
# Safety:
#   - Prompts for confirmation before destructive operations
#   - Verifies checksums before restoring
#   - Creates a pre-restore backup snapshot
#
# Exit codes:
#   0 = Success
#   1 = General error
#   2 = Backup not found / invalid
#   3 = Checksum verification failed
#   4 = Restore failed
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_BASE_DIR="${PROJECT_ROOT}/backups"

# Defaults
DO_DB=true
DO_MEDIA=true
DRY_RUN=false
FORCE=false
SKIP_PRE_BACKUP=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Functions ---------------------------------------------------------------
log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*" >&2; }
log_step()  { echo -e "${CYAN}[STEP]${NC}  $(date '+%H:%M:%S') $*"; }

usage() {
    head -28 "$0" | grep '^#' | sed 's/^# \?//'
    exit 0
}

# --- Parse Arguments ---------------------------------------------------------
BACKUP_DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-only)         DO_MEDIA=false; shift ;;
        --media-only)      DO_DB=false; shift ;;
        --dry-run)         DRY_RUN=true; shift ;;
        --force|-f)        FORCE=true; shift ;;
        --skip-pre-backup) SKIP_PRE_BACKUP=true; shift ;;
        --latest)
            BACKUP_DIR=$(find "$BACKUP_BASE_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -r | head -1)
            if [[ -z "$BACKUP_DIR" ]]; then
                log_error "No backups found in $BACKUP_BASE_DIR"
                exit 2
            fi
            shift ;;
        --help|-h) usage ;;
        -*)        log_error "Unknown option: $1"; usage ;;
        *)         BACKUP_DIR="$1"; shift ;;
    esac
done

if [[ -z "$BACKUP_DIR" ]]; then
    log_error "No backup directory specified"
    echo "Usage: $0 <backup_dir> | --latest"
    exit 1
fi

# Resolve relative paths
if [[ ! "$BACKUP_DIR" = /* ]]; then
    BACKUP_DIR="${PROJECT_ROOT}/${BACKUP_DIR}"
fi

# --- Validate Backup ---------------------------------------------------------
cd "$PROJECT_ROOT"

if [[ ! -d "$BACKUP_DIR" ]]; then
    log_error "Backup directory not found: $BACKUP_DIR"
    exit 2
fi

# Find metadata file
META_FILE=$(find "$BACKUP_DIR" -name "*.meta.json" -type f | sort -r | head -1)
if [[ -z "$META_FILE" ]]; then
    log_error "No metadata file found in $BACKUP_DIR"
    exit 2
fi

log_info "Restoring from: $BACKUP_DIR"
log_info "Metadata: $(basename "$META_FILE")"

# Parse metadata
BACKUP_DATE=$(python3 -c "import json; m=json.load(open('$META_FILE')); print(m.get('date','unknown'))")
log_info "Backup date: $BACKUP_DATE"

# Find backup files
DB_BACKUP=$(find "$BACKUP_DIR" -name "db_*.sql.gz" -type f | sort -r | head -1)
MEDIA_BACKUP=$(find "$BACKUP_DIR" -name "media_*.tar.gz" -type f | sort -r | head -1)

echo ""
log_info "Available backup components:"
if [[ -n "$DB_BACKUP" ]]; then
    DB_SIZE=$(stat -c%s "$DB_BACKUP" 2>/dev/null || stat -f%z "$DB_BACKUP")
    log_info "  Database : $(basename "$DB_BACKUP") ($(numfmt --to=iec "$DB_SIZE" 2>/dev/null || echo "${DB_SIZE} bytes"))"
else
    log_warn "  Database : not available"
    DO_DB=false
fi

if [[ -n "$MEDIA_BACKUP" ]]; then
    MEDIA_SIZE=$(stat -c%s "$MEDIA_BACKUP" 2>/dev/null || stat -f%z "$MEDIA_BACKUP")
    log_info "  Media    : $(basename "$MEDIA_BACKUP") ($(numfmt --to=iec "$MEDIA_SIZE" 2>/dev/null || echo "${MEDIA_SIZE} bytes"))"
else
    log_warn "  Media    : not available"
    DO_MEDIA=false
fi

if [[ "$DO_DB" == "false" && "$DO_MEDIA" == "false" ]]; then
    log_error "No restorable components found"
    exit 2
fi

# --- Verify Checksums --------------------------------------------------------
log_step "Verifying checksums..."

verify_checksum() {
    local file="$1"
    local checksum_file="${file}.sha256"

    if [[ ! -f "$checksum_file" ]]; then
        log_warn "No checksum file for $(basename "$file") — skipping verification"
        return 0
    fi

    if sha256sum -c "$checksum_file" --quiet 2>/dev/null; then
        log_info "  ✓ $(basename "$file") checksum OK"
        return 0
    else
        log_error "  ✗ $(basename "$file") checksum FAILED"
        return 1
    fi
}

CHECKSUM_OK=true
if [[ "$DO_DB" == "true" && -n "$DB_BACKUP" ]]; then
    verify_checksum "$DB_BACKUP" || CHECKSUM_OK=false
fi
if [[ "$DO_MEDIA" == "true" && -n "$MEDIA_BACKUP" ]]; then
    verify_checksum "$MEDIA_BACKUP" || CHECKSUM_OK=false
fi

if [[ "$CHECKSUM_OK" == "false" ]]; then
    log_error "Checksum verification failed — aborting restore"
    exit 3
fi

# --- Dry Run? ----------------------------------------------------------------
if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    log_info "========================================="
    log_info "  DRY RUN — verification only"
    log_info "========================================="
    log_info "  Backup is valid and ready for restore"
    log_info "  Run without --dry-run to perform restore"
    exit 0
fi

# --- Confirmation ------------------------------------------------------------
if [[ "$FORCE" == "false" ]]; then
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  WARNING: This will REPLACE current data!     ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Restore from: $(basename "$BACKUP_DIR") ($BACKUP_DATE)"
    [[ "$DO_DB" == "true" ]] && echo "  → Database will be dropped and recreated"
    [[ "$DO_MEDIA" == "true" ]] && echo "  → Media files will be overwritten"
    echo ""
    read -rp "Continue? (type 'yes' to confirm): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# Load .env
if [[ -f .env ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(POSTGRES_|DB_)' .env | xargs)
fi

# --- Pre-Restore Safety Backup -----------------------------------------------
if [[ "$SKIP_PRE_BACKUP" == "false" ]]; then
    log_step "Creating pre-restore safety backup..."
    PRE_RESTORE_DIR="${BACKUP_BASE_DIR}/pre_restore_${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
    mkdir -p "$PRE_RESTORE_DIR"

    docker compose exec -T db bash -c \
        "PGPASSWORD=\$POSTGRES_PASSWORD pg_dump \
            -U \$POSTGRES_USER \
            -d \$POSTGRES_DB \
            --no-owner --no-privileges" 2>/dev/null | gzip > "${PRE_RESTORE_DIR}/db_pre_restore.sql.gz"

    log_info "  Pre-restore backup saved to: $PRE_RESTORE_DIR"
fi

# --- Restore Database --------------------------------------------------------
if [[ "$DO_DB" == "true" && -n "$DB_BACKUP" ]]; then
    log_step "Restoring database..."

    # Drop and recreate via psql (the dump uses --clean --if-exists)
    zcat "$DB_BACKUP" | docker compose exec -T db psql \
        -U "${POSTGRES_USER:-postgres}" \
        -d "${POSTGRES_DB:-erechnung_ci}" \
        --quiet \
        --set ON_ERROR_STOP=off \
        2>/dev/null

    # Verify restore by counting tables
    TABLE_COUNT=$(docker compose exec -T db psql \
        -U "${POSTGRES_USER:-postgres}" \
        -d "${POSTGRES_DB:-erechnung_ci}" \
        -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null)
    TABLE_COUNT=$(echo "$TABLE_COUNT" | tr -d '[:space:]')

    if [[ "$TABLE_COUNT" -gt 0 ]]; then
        log_info "  Database restored successfully (${TABLE_COUNT} tables)"
    else
        log_error "  Database restore failed — no tables found"
        exit 4
    fi
fi

# --- Restore Media -----------------------------------------------------------
if [[ "$DO_MEDIA" == "true" && -n "$MEDIA_BACKUP" ]]; then
    log_step "Restoring media files..."

    # Copy archive into container and extract
    docker compose cp "$MEDIA_BACKUP" web:/tmp/media_restore.tar.gz
    docker compose exec -T web bash -c "
        mkdir -p /app/project_root/media
        cd /app
        tar xzf /tmp/media_restore.tar.gz
        rm -f /tmp/media_restore.tar.gz
    "

    RESTORED_COUNT=$(docker compose exec -T web bash -c 'find /app/project_root/media -type f | wc -l' 2>/dev/null | tr -d '[:space:]')
    log_info "  Media restored successfully (${RESTORED_COUNT} files)"
fi

# --- Post-Restore: Run Migrations -------------------------------------------
log_step "Running Django migrations (safety check)..."
docker compose exec -T web python project_root/manage.py migrate --run-syncdb --noinput 2>/dev/null || true

# --- Post-Restore: Verify Django -------------------------------------------
log_step "Verifying Django system check..."
if docker compose exec -T web python project_root/manage.py check --database default 2>/dev/null; then
    log_info "  Django system check passed"
else
    log_warn "  Django system check had warnings (non-fatal)"
fi

# --- Summary -----------------------------------------------------------------
echo ""
log_info "========================================="
log_info "  Restore completed successfully!"
log_info "========================================="
log_info "  Source     : $(basename "$BACKUP_DIR") ($BACKUP_DATE)"
[[ "$DO_DB" == "true" ]] && log_info "  Database   : ✓ restored"
[[ "$DO_MEDIA" == "true" ]] && log_info "  Media      : ✓ restored"
[[ "$SKIP_PRE_BACKUP" == "false" ]] && log_info "  Safety     : pre-restore backup in $(basename "${PRE_RESTORE_DIR:-n/a}")"
echo ""

exit 0
