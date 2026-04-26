#!/usr/bin/env bash
# =============================================================================
# eRechnung Backup Script
# =============================================================================
# Creates a timestamped backup of:
#   1. PostgreSQL database (pg_dump, gzip compressed)
#   2. Media files (tar.gz)
#   3. Metadata JSON (for restore verification)
#
# Usage:
#   ./scripts/backup.sh                    # Full backup (DB + Media)
#   ./scripts/backup.sh --db-only          # Database only
#   ./scripts/backup.sh --media-only       # Media files only
#   ./scripts/backup.sh --retention 30     # Keep last 30 days (default)
#   ./scripts/backup.sh --backup-dir /path # Custom backup directory
#
# Requirements:
#   - Docker Compose services running (db container healthy)
#   - .env file with POSTGRES_* variables
#
# Exit codes:
#   0 = Success
#   1 = General error
#   2 = Docker/container error
#   3 = Backup verification failed
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DATE_DIR="$(date +%Y%m%d)"

# Defaults
BACKUP_BASE_DIR="${PROJECT_ROOT}/backups"
RETENTION_DAYS=30
DO_DB=true
DO_MEDIA=true

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Functions ---------------------------------------------------------------
log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*" >&2; }

usage() {
    head -25 "$0" | grep '^#' | sed 's/^# \?//'
    exit 0
}

cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Backup failed with exit code $exit_code"
        # Remove incomplete backup
        if [[ -d "${BACKUP_DIR:-}" ]]; then
            log_warn "Removing incomplete backup: $BACKUP_DIR"
            rm -rf "$BACKUP_DIR"
        fi
    fi
}
trap cleanup EXIT

# --- Parse Arguments ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-only)      DO_MEDIA=false; shift ;;
        --media-only)   DO_DB=false; shift ;;
        --retention)    RETENTION_DAYS="$2"; shift 2 ;;
        --backup-dir)   BACKUP_BASE_DIR="$2"; shift 2 ;;
        --help|-h)      usage ;;
        *)              log_error "Unknown option: $1"; usage ;;
    esac
done

# --- Pre-flight Checks -------------------------------------------------------
cd "$PROJECT_ROOT"

# Load .env for variable names
if [[ -f .env ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(POSTGRES_|DB_)' .env | xargs)
fi

DB_CONTAINER="$(docker compose ps -q db 2>/dev/null || true)"
if [[ -z "$DB_CONTAINER" ]]; then
    log_error "Database container not running. Start with: docker compose up -d db"
    exit 2
fi

# Verify DB is healthy
if ! docker compose exec -T db pg_isready -q -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-erechnung_ci}" 2>/dev/null; then
    log_error "Database is not ready"
    exit 2
fi

# --- Create Backup Directory -------------------------------------------------
BACKUP_DIR="${BACKUP_BASE_DIR}/${DATE_DIR}"
mkdir -p "$BACKUP_DIR"
log_info "Backup directory: $BACKUP_DIR"

# --- Metadata ----------------------------------------------------------------
METADATA_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.meta.json"

# Collect DB size for metadata
DB_SIZE=$(docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-erechnung_ci}" \
    -t -A -c "SELECT pg_database_size(current_database())" 2>/dev/null || echo "0")

cat > "$METADATA_FILE" <<EOF
{
    "timestamp": "${TIMESTAMP}",
    "date": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "database": {
        "name": "${POSTGRES_DB:-erechnung_ci}",
        "size_bytes": ${DB_SIZE},
        "included": ${DO_DB}
    },
    "media": {
        "included": ${DO_MEDIA}
    },
    "retention_days": ${RETENTION_DAYS},
    "backup_dir": "${BACKUP_DIR}",
    "version": "1.0"
}
EOF

# --- Database Backup ---------------------------------------------------------
if [[ "$DO_DB" == "true" ]]; then
    DB_BACKUP_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"
    log_info "Starting database backup..."

    # pg_dump with gzip compression
    docker compose exec -T db bash -c \
        "PGPASSWORD=\$POSTGRES_PASSWORD pg_dump \
            -U \$POSTGRES_USER \
            -d \$POSTGRES_DB \
            --no-owner \
            --no-privileges \
            --clean \
            --if-exists \
            --verbose" 2>/dev/null | gzip > "$DB_BACKUP_FILE"

    DB_BACKUP_SIZE=$(stat -c%s "$DB_BACKUP_FILE" 2>/dev/null || stat -f%z "$DB_BACKUP_FILE")
    log_info "Database backup: ${DB_BACKUP_FILE} ($(numfmt --to=iec "$DB_BACKUP_SIZE" 2>/dev/null || echo "${DB_BACKUP_SIZE} bytes"))"

    # Verify backup is not empty and contains valid SQL
    if [[ "$DB_BACKUP_SIZE" -lt 100 ]]; then
        log_error "Database backup file is suspiciously small (${DB_BACKUP_SIZE} bytes)"
        exit 3
    fi

    # Quick integrity check: verify gzip is valid and contains SQL
    if ! gzip -t "$DB_BACKUP_FILE" 2>/dev/null; then
        log_error "Database backup gzip integrity check failed"
        exit 3
    fi

    # Verify it contains expected content
    DUMP_HEADER=$(zcat "$DB_BACKUP_FILE" 2>/dev/null | head -10 || true)
    if ! echo "$DUMP_HEADER" | grep -qi "PostgreSQL database dump"; then
        log_error "Database backup does not contain valid PostgreSQL dump"
        exit 3
    fi

    # Generate SHA256 checksum
    sha256sum "$DB_BACKUP_FILE" > "${DB_BACKUP_FILE}.sha256"
    log_info "Database backup checksum created"

    # Update metadata with actual file info
    DB_DUMP_LINES=$(zcat "$DB_BACKUP_FILE" | wc -l)
    python3 -c "
import json
with open('$METADATA_FILE', 'r') as f:
    meta = json.load(f)
meta['database']['backup_file'] = '$(basename "$DB_BACKUP_FILE")'
meta['database']['backup_size_bytes'] = $DB_BACKUP_SIZE
meta['database']['dump_lines'] = $DB_DUMP_LINES
with open('$METADATA_FILE', 'w') as f:
    json.dump(meta, f, indent=2)
"
fi

# --- Media Backup ------------------------------------------------------------
if [[ "$DO_MEDIA" == "true" ]]; then
    MEDIA_BACKUP_FILE="${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz"
    log_info "Starting media backup..."

    # Check if media directory exists in the web container
    MEDIA_EXISTS=$(docker compose exec -T web bash -c '[[ -d /app/project_root/media ]] && echo "yes" || echo "no"' 2>/dev/null || echo "no")

    if [[ "$MEDIA_EXISTS" == "yes" ]]; then
        MEDIA_FILE_COUNT=$(docker compose exec -T web bash -c 'find /app/project_root/media -type f 2>/dev/null | wc -l' 2>/dev/null || echo "0")
        MEDIA_FILE_COUNT=$(echo "$MEDIA_FILE_COUNT" | tr -d '[:space:]')

        if [[ "$MEDIA_FILE_COUNT" -gt 0 ]]; then
            docker compose exec -T web tar czf - -C /app media > "$MEDIA_BACKUP_FILE"
            MEDIA_BACKUP_SIZE=$(stat -c%s "$MEDIA_BACKUP_FILE" 2>/dev/null || stat -f%z "$MEDIA_BACKUP_FILE")
            log_info "Media backup: ${MEDIA_BACKUP_FILE} ($(numfmt --to=iec "$MEDIA_BACKUP_SIZE" 2>/dev/null || echo "${MEDIA_BACKUP_SIZE} bytes"), ${MEDIA_FILE_COUNT} files)"

            sha256sum "$MEDIA_BACKUP_FILE" > "${MEDIA_BACKUP_FILE}.sha256"

            python3 -c "
import json
with open('$METADATA_FILE', 'r') as f:
    meta = json.load(f)
meta['media']['backup_file'] = '$(basename "$MEDIA_BACKUP_FILE")'
meta['media']['backup_size_bytes'] = $MEDIA_BACKUP_SIZE
meta['media']['file_count'] = $MEDIA_FILE_COUNT
with open('$METADATA_FILE', 'w') as f:
    json.dump(meta, f, indent=2)
"
        else
            log_warn "No media files found — skipping media backup"
            python3 -c "
import json
with open('$METADATA_FILE', 'r') as f:
    meta = json.load(f)
meta['media']['backup_file'] = None
meta['media']['file_count'] = 0
meta['media']['note'] = 'No media files found'
with open('$METADATA_FILE', 'w') as f:
    json.dump(meta, f, indent=2)
"
        fi
    else
        log_warn "Media directory does not exist in web container — skipping"
    fi
fi

# --- Retention Policy --------------------------------------------------------
if [[ "$RETENTION_DAYS" -gt 0 ]]; then
    log_info "Applying retention policy: keeping last ${RETENTION_DAYS} days..."
    DELETED_COUNT=0

    while IFS= read -r old_dir; do
        if [[ -d "$old_dir" ]]; then
            rm -rf "$old_dir"
            ((DELETED_COUNT++))
            log_info "  Deleted old backup: $(basename "$old_dir")"
        fi
    done < <(find "$BACKUP_BASE_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" 2>/dev/null || true)

    if [[ "$DELETED_COUNT" -gt 0 ]]; then
        log_info "Removed ${DELETED_COUNT} old backup(s)"
    fi
fi

# --- Summary -----------------------------------------------------------------
echo ""
log_info "========================================="
log_info "  Backup completed successfully!"
log_info "========================================="
log_info "  Directory : $BACKUP_DIR"
log_info "  Metadata  : $(basename "$METADATA_FILE")"
[[ "$DO_DB" == "true" ]] && log_info "  Database  : $(basename "${DB_BACKUP_FILE:-n/a}")"
[[ "$DO_MEDIA" == "true" ]] && log_info "  Media     : $(basename "${MEDIA_BACKUP_FILE:-skipped}")"
log_info "  Retention : ${RETENTION_DAYS} days"
echo ""

exit 0
