#!/usr/bin/env bash
# =============================================================================
# Testsuite-Selbstvalidierung
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.11
#
# Prüft, dass die Testsuite echte Probleme erkennt:
# - Negativ-Test: Absichtlich fehlerhaftes Update → Tests schlagen fehl
# - Mutationstest: Manipulierte Migration → Tests erkennen Bruch
# - False-Positive: Korrektes Update → kein Test schlägt fälschlicherweise fehl
# - Stress-Benchmark: Migration mit 10.000 Rechnungen < 60s
#
# Usage:
#   ./scripts/tests/test_self_validation.sh           # Alle Tests
#   ./scripts/tests/test_self_validation.sh SV-01     # Einzelner Test
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.update-test.yml"
FIXTURES_DIR="/app/test-artifacts/update-tests/fixtures"

# Farben
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# Zähler
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

declare -a TEST_RESULTS=()

# --- Test Framework ----------------------------------------------------------

run_test() {
    local test_id="$1"
    local test_name="$2"
    local test_func="$3"

    ((TESTS_RUN++)) || true
    echo -ne "${BLUE}  [$test_id]${NC} $test_name ... "

    local result=0
    $test_func 2>/dev/null || result=$?

    if [[ "$result" == "0" ]]; then
        ((TESTS_PASSED++)) || true
        echo -e "${GREEN}PASS${NC}"
        TEST_RESULTS+=("PASS $test_id $test_name")
    else
        ((TESTS_FAILED++)) || true
        echo -e "${RED}FAIL${NC}"
        TEST_RESULTS+=("FAIL $test_id $test_name")
    fi
}

# --- Helpers -----------------------------------------------------------------

manage_new() {
    docker compose -f "$COMPOSE_FILE" run --rm \
        -e POSTGRES_HOST=db-update-test \
        -e POSTGRES_DB=erechnung_update_test \
        -e POSTGRES_USER=erechnung_test \
        -e POSTGRES_PASSWORD=test_password_only_for_update_tests \
        -e POSTGRES_PORT=5432 \
        -e REDIS_URL=redis://redis-update-test:6379/0 \
        -e DJANGO_SECRET_KEY=update-test-secret-key-not-for-production \
        -e DJANGO_ALLOWED_HOSTS='*' \
        -e DEBUG=True \
        web-new python project_root/manage.py "$@" 2>&1
}

psql_test() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -t -A -c "$1" 2>/dev/null
}

reset_test_db() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO erechnung_test;
        " &>/dev/null
}

# --- Setup / Teardown --------------------------------------------------------

setup_env() {
    echo -e "${BLUE}  Selbstvalidierung-Testumgebung starten...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d db-update-test redis-update-test 2>/dev/null

    local retries=30
    while (( retries > 0 )); do
        if docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
            pg_isready -d erechnung_update_test -U erechnung_test &>/dev/null; then
            break
        fi
        sleep 1
        ((retries--))
    done

    if (( retries == 0 )); then
        echo -e "${RED}  DB nicht bereit nach 30s${NC}" >&2
        return 1
    fi
    echo -e "${GREEN}  Selbstvalidierung-Testumgebung bereit.${NC}"
}

teardown_env() {
    echo -e "${BLUE}  Testumgebung aufräumen...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
}

# =============================================================================
# SV-01: Negativ-Test — Kaputtes Schema erkennen
# =============================================================================
# Absichtlich ein Schema brechen → Django check muss fehlschlagen.
test_sv01_negative_broken_schema() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null

    # Break the schema: drop a required column
    psql_test "ALTER TABLE invoice_app_businesspartner DROP COLUMN IF EXISTS company_name;" >/dev/null

    # Django should detect the broken schema
    local result=0
    manage_new check --database default 2>&1 || result=$?

    # Try query that should fail
    local query_result=0
    manage_new shell -c "
from invoice_app.models import BusinessPartner
try:
    list(BusinessPartner.objects.values('company_name')[:1])
except Exception:
    exit(1)
" 2>&1 || query_result=$?

    if (( query_result == 0 )); then
        echo "  Kaputtes Schema nicht erkannt" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# SV-02: Mutationstest — Fehlende Tabelle erkennen
# =============================================================================
# Eine Tabelle entfernen → loaddata muss fehlschlagen.
test_sv02_mutation_missing_table() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null

    # Drop an important table
    psql_test "DROP TABLE IF EXISTS invoice_app_product CASCADE;" >/dev/null

    # loaddata should fail because the table is missing
    local result=0
    manage_new loaddata "$FIXTURES_DIR/standard.json" 2>&1 || result=$?

    if (( result == 0 )); then
        echo "  loaddata auf fehlende Tabelle hätte scheitern sollen" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# SV-03: False-Positive-Check — Korrektes Update ohne Fehler
# =============================================================================
# Ein sauberes Update darf keine Fehler produzieren.
test_sv03_false_positive_clean() {
    reset_test_db

    # Clean migration
    manage_new migrate --run-syncdb >/dev/null
    local migrate_result=$?

    if (( migrate_result != 0 )); then
        echo "  Saubere Migration fehlgeschlagen" >&2
        return 1
    fi

    # Load fixtures
    manage_new loaddata "$FIXTURES_DIR/standard.json" >/dev/null
    local load_result=$?

    if (( load_result != 0 )); then
        echo "  Sauberes Fixture-Loading fehlgeschlagen" >&2
        return 1
    fi

    # Django check
    local check_output
    check_output=$(manage_new check 2>&1) || true

    if echo "$check_output" | grep -qi "error"; then
        echo "  False-Positive: Django check meldet Fehler bei sauberem System" >&2
        return 1
    fi

    # Verify data
    local count
    count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    if (( count < 1 )); then
        echo "  Keine Daten nach sauberem Setup" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# SV-04: Stress-Benchmark — 10.000 Rechnungen Migration < 60s
# =============================================================================
# Migration mit Stress-Daten muss unter 60 Sekunden bleiben.
test_sv04_stress_benchmark() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/minimal.json" >/dev/null

    # Generate stress data via SQL
    local stress_script="$SCRIPT_DIR/generate_stress_data.sh"
    if [[ ! -x "$stress_script" ]]; then
        echo "  generate_stress_data.sh nicht gefunden" >&2
        return 1
    fi

    "$stress_script" "$COMPOSE_FILE"

    # Verify data was created
    local invoice_count
    invoice_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_invoice;")
    if (( invoice_count < 10000 )); then
        echo "  Nur $invoice_count Rechnungen (erwartet >= 10.000)" >&2
        return 1
    fi

    # Measure migration time: rollback to 0004 (before gobd_compliance) and re-migrate
    # Migration 0005 (gobd_compliance) adds ~10 columns to invoice table — this
    # is the migration that actually stresses the DB with 10k invoices present.
    local start_time
    start_time=$(date +%s%N)

    manage_new migrate invoice_app 0004 >/dev/null || {
        echo "  Rollback auf 0004 fehlgeschlagen" >&2
        return 1
    }
    manage_new migrate >/dev/null || {
        echo "  Re-Migration fehlgeschlagen" >&2
        return 1
    }

    local end_time
    end_time=$(date +%s%N)
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    local duration=$(( duration_ms / 1000 ))

    echo "  Migration 0005-0007 mit $invoice_count Rechnungen: ${duration_ms}ms" >&2

    if (( duration > 60 )); then
        echo "  Migration dauerte ${duration}s (max 60s)" >&2
        return 1
    fi

    # Verify data survived
    local after_count
    after_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_invoice;")
    if (( after_count < 10000 )); then
        echo "  Datenverlust nach Migration: $invoice_count → $after_count" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Testsuite-Selbstvalidierung (SV-01..SV-04)    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}\n"

    # Setup
    setup_env || { echo -e "${RED}Testumgebung konnte nicht gestartet werden.${NC}"; exit 2; }
    trap teardown_env EXIT

    if [[ -n "$filter" ]]; then
        case "$filter" in
            SV-01) run_test "SV-01" "Negativ-Test: Kaputtes Schema" test_sv01_negative_broken_schema ;;
            SV-02) run_test "SV-02" "Mutationstest: Fehlende Tabelle" test_sv02_mutation_missing_table ;;
            SV-03) run_test "SV-03" "False-Positive: Sauberes Update" test_sv03_false_positive_clean ;;
            SV-04) run_test "SV-04" "Stress-Benchmark: 10k Rechnungen" test_sv04_stress_benchmark ;;
            *)     echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "SV-01" "Negativ-Test: Kaputtes Schema" test_sv01_negative_broken_schema
        run_test "SV-02" "Mutationstest: Fehlende Tabelle" test_sv02_mutation_missing_table
        run_test "SV-03" "False-Positive: Sauberes Update" test_sv03_false_positive_clean
        run_test "SV-04" "Stress-Benchmark: 10k Rechnungen" test_sv04_stress_benchmark
    fi

    # Summary
    echo ""
    echo -e "${BLUE}--- Zusammenfassung ---${NC}"
    echo -e "  Gesamt:       $TESTS_RUN"
    echo -e "  ${GREEN}Bestanden:   $TESTS_PASSED${NC}"
    echo -e "  ${RED}Fehlgeschlagen: $TESTS_FAILED${NC}"

    if (( TESTS_FAILED > 0 )); then
        exit 1
    fi
    exit 0
}

main "$@"
