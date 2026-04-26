#!/usr/bin/env bash
# =============================================================================
# eRechnung Backup & Restore Verification Test
# =============================================================================
# Automated test that:
#   1. Creates a fresh backup of the current database
#   2. Spins up a temporary PostgreSQL container (tmpfs/RAM)
#   3. Restores the backup into the temporary container
#   4. Verifies data integrity (row counts, checksums, schema)
#   5. Tears down the temporary container
#
# Usage:
#   ./scripts/backup_restore_test.sh                # Full test
#   ./scripts/backup_restore_test.sh --keep         # Keep test container for debug
#   ./scripts/backup_restore_test.sh --skip-backup  # Use latest existing backup
#
# Exit codes:
#   0 = All tests passed
#   1 = Test failed
#   2 = Infrastructure error
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_BASE_DIR="${PROJECT_ROOT}/backups"
COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.backup-test.yml"
RESTORE_CONTAINER="db-restore-test"

# Options
KEEP_CONTAINER=false
SKIP_BACKUP=false
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Functions ---------------------------------------------------------------
log_info()  { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[FAIL]${NC}  $(date '+%H:%M:%S') $*" >&2; }
log_test()  { echo -e "${CYAN}[TEST]${NC}  $(date '+%H:%M:%S') $*"; }

assert_eq() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    if [[ "$expected" == "$actual" ]]; then
        log_info "  ✓ $description (expected=$expected, got=$actual)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "  ✗ $description (expected=$expected, got=$actual)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

assert_ge() {
    local description="$1"
    local minimum="$2"
    local actual="$3"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    if [[ "$actual" -ge "$minimum" ]]; then
        log_info "  ✓ $description (minimum=$minimum, got=$actual)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "  ✗ $description (minimum=$minimum, got=$actual)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

assert_not_empty() {
    local description="$1"
    local value="$2"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    if [[ -n "$value" && "$value" != "0" ]]; then
        log_info "  ✓ $description (value=$value)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_error "  ✗ $description (empty or zero)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

cleanup() {
    local exit_code=$?
    if [[ "$KEEP_CONTAINER" == "false" ]]; then
        log_info "Cleaning up test container..."
        cd "$PROJECT_ROOT"
        $COMPOSE_CMD rm -sf "$RESTORE_CONTAINER" 2>/dev/null || true
    else
        log_warn "Keeping test container running (--keep flag)"
    fi

    # Clean up test backup
    if [[ -d "${TEST_BACKUP_DIR:-}" && "$SKIP_BACKUP" == "false" ]]; then
        rm -rf "$TEST_BACKUP_DIR"
    fi

    if [[ $exit_code -ne 0 && $exit_code -ne 1 ]]; then
        log_error "Test script failed with infrastructure error (exit code: $exit_code)"
    fi
}
trap cleanup EXIT

# --- Parse Arguments ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep)        KEEP_CONTAINER=true; shift ;;
        --skip-backup) SKIP_BACKUP=true; shift ;;
        --help|-h)     head -20 "$0" | grep '^#' | sed 's/^# \?//'; exit 0 ;;
        *)             log_error "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Pre-flight --------------------------------------------------------------
cd "$PROJECT_ROOT"

# Load .env
if [[ -f .env ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(POSTGRES_|DB_)' .env | xargs)
fi

PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-erechnung_ci}"

# Verify source DB is running
if ! docker compose exec -T db pg_isready -q -U "$PG_USER" -d "$PG_DB" 2>/dev/null; then
    log_error "Source database is not running"
    exit 2
fi

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  eRechnung Backup & Restore Verification Test    ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# Phase 1: Collect Source Data Fingerprint
# =============================================================================
log_test "Phase 1: Collecting source database fingerprint..."

query_source() {
    docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -t -A -c "$1" 2>/dev/null | tr -d '[:space:]'
}

SRC_TABLE_COUNT=$(query_source "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND (table_name LIKE 'invoice_app_%' OR table_name LIKE 'auth_%' OR table_name LIKE 'django_%')")
SRC_INVOICE_COUNT=$(query_source "SELECT COUNT(*) FROM invoice_app_invoice")
SRC_AUDITLOG_COUNT=$(query_source "SELECT COUNT(*) FROM invoice_app_auditlog")
SRC_PARTNER_COUNT=$(query_source "SELECT COUNT(*) FROM invoice_app_businesspartner")
SRC_LINE_COUNT=$(query_source "SELECT COUNT(*) FROM invoice_app_invoiceline")
SRC_MIGRATION_COUNT=$(query_source "SELECT COUNT(*) FROM django_migrations")

log_info "Source fingerprint:"
log_info "  Tables: $SRC_TABLE_COUNT | Invoices: $SRC_INVOICE_COUNT | AuditLogs: $SRC_AUDITLOG_COUNT"
log_info "  Partners: $SRC_PARTNER_COUNT | Lines: $SRC_LINE_COUNT | Migrations: $SRC_MIGRATION_COUNT"

# =============================================================================
# Phase 2: Create Backup
# =============================================================================
if [[ "$SKIP_BACKUP" == "true" ]]; then
    log_test "Phase 2: Using latest existing backup (--skip-backup)..."
    TEST_BACKUP_DIR=$(find "$BACKUP_BASE_DIR" -mindepth 1 -maxdepth 1 -type d ! -name 'pre_restore_*' 2>/dev/null | sort -r | head -1)
    if [[ -z "$TEST_BACKUP_DIR" ]]; then
        log_error "No existing backup found"
        exit 2
    fi
    log_info "Using backup: $TEST_BACKUP_DIR"
else
    log_test "Phase 2: Creating fresh backup..."
    TEST_BACKUP_DIR="${BACKUP_BASE_DIR}/restore_test_$(date +%Y%m%d_%H%M%S)"
    bash "$SCRIPT_DIR/backup.sh" --db-only --backup-dir "$TEST_BACKUP_DIR" --retention 0
fi

# Find the dump file
DB_DUMP=$(find "$TEST_BACKUP_DIR" -name "db_*.sql.gz" -type f | sort -r | head -1)
if [[ -z "$DB_DUMP" ]]; then
    # If --skip-backup, look in subdirectories
    DB_DUMP=$(find "$TEST_BACKUP_DIR" -name "db_*.sql.gz" -type f | sort -r | head -1)
fi
if [[ -z "$DB_DUMP" ]]; then
    log_error "No database dump found in $TEST_BACKUP_DIR"
    exit 2
fi
log_info "Dump file: $(basename "$DB_DUMP")"

# =============================================================================
# Phase 3: Start Restore Container
# =============================================================================
log_test "Phase 3: Starting temporary restore container..."

# Stop any existing test container
$COMPOSE_CMD rm -sf "$RESTORE_CONTAINER" 2>/dev/null || true

# Start fresh
$COMPOSE_CMD up -d "$RESTORE_CONTAINER"

# Wait for healthy
log_info "Waiting for restore container to be ready..."
RETRIES=30
while [[ $RETRIES -gt 0 ]]; do
    if $COMPOSE_CMD exec -T "$RESTORE_CONTAINER" pg_isready -q -U "$PG_USER" -d "$PG_DB" 2>/dev/null; then
        break
    fi
    sleep 1
    ((RETRIES--))
done

if [[ $RETRIES -eq 0 ]]; then
    log_error "Restore container failed to start"
    exit 2
fi
log_info "Restore container is ready"

# =============================================================================
# Phase 4: Restore Backup into Test Container
# =============================================================================
log_test "Phase 4: Restoring backup into test container..."

query_restore() {
    $COMPOSE_CMD exec -T "$RESTORE_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -t -A -c "$1" 2>/dev/null | tr -d '[:space:]'
}

# Restore the dump (ignore errors from --clean --if-exists on fresh DB)
zcat "$DB_DUMP" | $COMPOSE_CMD exec -T "$RESTORE_CONTAINER" psql \
    -U "$PG_USER" \
    -d "$PG_DB" \
    --quiet \
    --set ON_ERROR_STOP=off \
    >/dev/null 2>&1 || true

log_info "Restore completed"

# =============================================================================
# Phase 5: Verify Restored Data
# =============================================================================
log_test "Phase 5: Verifying restored data..."

echo ""
log_test "5a. Schema verification"
RST_TABLE_COUNT=$(query_restore "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND (table_name LIKE 'invoice_app_%' OR table_name LIKE 'auth_%' OR table_name LIKE 'django_%')")
assert_eq "Table count matches" "$SRC_TABLE_COUNT" "$RST_TABLE_COUNT"

echo ""
log_test "5b. Row count verification"
RST_INVOICE_COUNT=$(query_restore "SELECT COUNT(*) FROM invoice_app_invoice")
RST_AUDITLOG_COUNT=$(query_restore "SELECT COUNT(*) FROM invoice_app_auditlog")
RST_PARTNER_COUNT=$(query_restore "SELECT COUNT(*) FROM invoice_app_businesspartner")
RST_LINE_COUNT=$(query_restore "SELECT COUNT(*) FROM invoice_app_invoiceline")
RST_MIGRATION_COUNT=$(query_restore "SELECT COUNT(*) FROM django_migrations")

assert_eq "Invoice count" "$SRC_INVOICE_COUNT" "$RST_INVOICE_COUNT"
assert_eq "AuditLog count" "$SRC_AUDITLOG_COUNT" "$RST_AUDITLOG_COUNT"
assert_eq "BusinessPartner count" "$SRC_PARTNER_COUNT" "$RST_PARTNER_COUNT"
assert_eq "InvoiceLine count" "$SRC_LINE_COUNT" "$RST_LINE_COUNT"
assert_eq "Migration count" "$SRC_MIGRATION_COUNT" "$RST_MIGRATION_COUNT"

echo ""
log_test "5c. Data integrity verification"

# Verify invoice numbers are intact
SRC_FIRST_INVOICE=$(query_source "SELECT invoice_number FROM invoice_app_invoice ORDER BY id LIMIT 1")
RST_FIRST_INVOICE=$(query_restore "SELECT invoice_number FROM invoice_app_invoice ORDER BY id LIMIT 1")
assert_eq "First invoice number" "$SRC_FIRST_INVOICE" "$RST_FIRST_INVOICE"

# Verify audit log chain integrity (hash chain)
RST_AUDIT_HASH=$(query_restore "SELECT entry_hash FROM invoice_app_auditlog ORDER BY id DESC LIMIT 1")
assert_not_empty "Audit log integrity hash present" "$RST_AUDIT_HASH"

echo ""
log_test "5d. Constraint verification"

# Verify foreign keys are intact
RST_FK_COUNT=$(query_restore "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema='public'")
SRC_FK_COUNT=$(query_source "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema='public'")
assert_eq "Foreign key count" "$SRC_FK_COUNT" "$RST_FK_COUNT"

# Verify indexes
RST_IDX_COUNT=$(query_restore "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public'")
SRC_IDX_COUNT=$(query_source "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public'")
assert_eq "Index count" "$SRC_IDX_COUNT" "$RST_IDX_COUNT"

echo ""
log_test "5e. Backup file integrity"
CHECKSUM_FILE="${DB_DUMP}.sha256"
TESTS_TOTAL=$((TESTS_TOTAL + 1))
if [[ -f "$CHECKSUM_FILE" ]] && sha256sum -c "$CHECKSUM_FILE" --quiet 2>/dev/null; then
    log_info "  ✓ SHA256 checksum verification passed"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    if [[ ! -f "$CHECKSUM_FILE" ]]; then
        log_warn "  - SHA256 checksum file not found (skipped)"
    else
        log_error "  ✗ SHA256 checksum verification failed"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "═══════════════════════════════════════════════════"
echo "  RESTORE VERIFICATION RESULTS"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Tests total  : $TESTS_TOTAL"
echo -e "  Tests passed : ${GREEN}$TESTS_PASSED${NC}"
if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "  Tests failed : ${RED}$TESTS_FAILED${NC}"
else
    echo -e "  Tests failed : ${GREEN}0${NC}"
fi
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}  ✓ ALL TESTS PASSED — Backup & Restore verified!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}  ✗ SOME TESTS FAILED — Backup may be corrupt!${NC}"
    echo ""
    exit 1
fi
