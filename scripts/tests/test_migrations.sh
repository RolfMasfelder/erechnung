#!/usr/bin/env bash
# =============================================================================
# Ebene-2 Migrations-Tests (M-01 bis M-23)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.4
#
# Testet Django-Migrationen in einer isolierten Testumgebung:
#   - Forward-Migrationen (M-01 bis M-08)
#   - Backward-Migrationen (M-10 bis M-14)
#   - Kompatibilitäts-Tests (M-20 bis M-23)
#
# Usage:
#   ./scripts/tests/test_migrations.sh              # Alle Tests
#   ./scripts/tests/test_migrations.sh M-01          # Einzelner Test
#
# Benötigt: docker-compose.update-test.yml (db-update-test + redis-update-test)
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

# --- Test-DB Helper ----------------------------------------------------------

# Run manage.py command against the test DB
manage_test() {
    docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
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

# Run arbitrary Python against test DB
python_test() {
    docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
        -e POSTGRES_HOST=db-update-test \
        -e POSTGRES_DB=erechnung_update_test \
        -e POSTGRES_USER=erechnung_test \
        -e POSTGRES_PASSWORD=test_password_only_for_update_tests \
        -e POSTGRES_PORT=5432 \
        -e REDIS_URL=redis://redis-update-test:6379/0 \
        -e DJANGO_SECRET_KEY=update-test-secret-key-not-for-production \
        -e DJANGO_ALLOWED_HOSTS='*' \
        -e DEBUG=True \
        web-new python -c "$1" 2>&1
}

# Run psql against the test DB
psql_test() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -t -A -c "$1" 2>/dev/null
}

# Reset test DB to clean state
reset_test_db() {
    # Drop and recreate the schema
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO erechnung_test;
        " &>/dev/null
}

# --- Setup / Teardown --------------------------------------------------------

setup_test_env() {
    echo -e "${BLUE}  Testumgebung starten...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d db-update-test redis-update-test 2>/dev/null

    # Wait for DB to be healthy
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
    echo -e "${GREEN}  Testumgebung bereit.${NC}"
}

teardown_test_env() {
    echo -e "${BLUE}  Testumgebung aufräumen...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
}

# =============================================================================
# M-01: Forward-Migration — Schema-Vollständigkeit
# =============================================================================
test_m01_schema_completeness() {
    reset_test_db

    # Run all migrations
    manage_test migrate --run-syncdb >/dev/null

    # Verify key tables exist
    local tables
    tables=$(psql_test "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")

    local required_tables=(
        "invoice_app_invoice"
        "invoice_app_invoiceline"
        "invoice_app_businesspartner"
        "invoice_app_company"
        "invoice_app_country"
        "invoice_app_product"
        "auth_user"
    )

    for tbl in "${required_tables[@]}"; do
        if ! echo "$tables" | grep -q "^${tbl}$"; then
            echo "  Tabelle fehlt: $tbl" >&2
            return 1
        fi
    done
    return 0
}

# =============================================================================
# M-02: Forward-Migration — Datenintegrität nach Fixture-Load
# =============================================================================
test_m02_data_integrity() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Load standard fixtures
    manage_test loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    # Verify data counts
    local user_count
    user_count=$(psql_test "SELECT COUNT(*) FROM auth_user;")
    if (( user_count < 2 )); then
        echo "  Erwartet >= 2 User, gefunden: $user_count" >&2
        return 1
    fi

    local partner_count
    partner_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    if (( partner_count < 3 )); then
        echo "  Erwartet >= 3 Partner, gefunden: $partner_count" >&2
        return 1
    fi

    local country_count
    country_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")
    if (( country_count < 3 )); then
        echo "  Erwartet >= 3 Länder, gefunden: $country_count" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-03: Forward-Migration — Minimal-Fixtures überleben Migration
# =============================================================================
test_m03_minimal_fixtures_survive() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null
    manage_test loaddata "$FIXTURES_DIR/minimal.json" >/dev/null

    # Verify min data survives
    local company_count
    company_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_company;")
    if (( company_count < 1 )); then
        echo "  Keine Company nach Migration" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-04: Forward-Migration — Performance (< 30s für alle Migrationen)
# =============================================================================
test_m04_migration_performance() {
    reset_test_db

    local start_time
    start_time=$(date +%s)

    manage_test migrate --run-syncdb >/dev/null

    local end_time
    end_time=$(date +%s)
    local duration=$(( end_time - start_time ))

    if (( duration > 30 )); then
        echo "  Migration dauerte ${duration}s (max 30s)" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-05: Forward-Migration — Idempotenz (migrate zweimal hintereinander)
# =============================================================================
test_m05_migration_idempotent() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Zweites migrate soll keine Fehler werfen
    local output
    output=$(manage_test migrate --run-syncdb 2>&1) || {
        echo "  Zweites migrate fehlgeschlagen" >&2
        return 1
    }

    # Should say "No migrations to apply" or similar
    if echo "$output" | grep -qi "error\|exception\|traceback"; then
        echo "  Fehler bei zweitem migrate:" >&2
        echo "  $output" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-06: Forward-Migration — Index-Existenz
# =============================================================================
test_m06_indexes_exist() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Check that indexes exist on frequently queried columns
    local index_count
    index_count=$(psql_test "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public';")

    if (( index_count < 5 )); then
        echo "  Nur $index_count Indexes gefunden (erwartet >= 5)" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-07: Forward-Migration — Constraint-Prüfung
# =============================================================================
test_m07_constraints_exist() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Check that foreign key constraints exist
    local fk_count
    fk_count=$(psql_test "
        SELECT COUNT(*)
        FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
          AND table_schema = 'public'
          AND table_name LIKE 'invoice_app_%';
    ")

    if (( fk_count < 1 )); then
        echo "  Keine Foreign Keys auf invoice_app-Tabellen" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-08: Forward-Migration — GoBD-Tabellen vorhanden
# =============================================================================
test_m08_gobd_tables() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # 0005_gobd_compliance adds audit-related fields/tables
    local tables
    tables=$(psql_test "SELECT tablename FROM pg_tables WHERE schemaname='public';")

    # Check that GoBD-related table exists (auditlog or similar)
    # The 0005 migration adds fields to existing tables, so we check columns
    local gobd_columns
    gobd_columns=$(psql_test "
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='invoice_app_invoice'
          AND column_name IN ('created_at', 'updated_at', 'created_by_id');
    ")

    if [[ -z "$gobd_columns" ]]; then
        echo "  GoBD-Audit-Felder nicht gefunden in invoice_app_invoice" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-10: Backward-Migration — Rollback letzte Migration
# =============================================================================
test_m10_rollback_last() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Rollback to 0006
    local output
    output=$(manage_test migrate invoice_app 0006 2>&1) || {
        echo "  Rollback auf 0006 fehlgeschlagen" >&2
        return 1
    }

    if echo "$output" | grep -qi "error\|exception\|traceback"; then
        echo "  Fehler beim Rollback:" >&2
        return 1
    fi

    # Verify we're on 0006
    local applied
    applied=$(manage_test showmigrations invoice_app 2>&1)
    if echo "$applied" | grep -q '\[X\] 0007'; then
        echo "  0007 ist noch angewendet nach Rollback" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-11: Backward-Migration — Rollback auf 0005
# =============================================================================
test_m11_rollback_to_0005() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    local output
    output=$(manage_test migrate invoice_app 0005 2>&1) || {
        echo "  Rollback auf 0005 fehlgeschlagen" >&2
        return 1
    }

    if echo "$output" | grep -qi "error\|traceback"; then
        echo "  Fehler beim Rollback auf 0005" >&2
        return 1
    fi

    # Forward again to make sure no data loss
    output=$(manage_test migrate 2>&1) || {
        echo "  Forward nach Rollback fehlgeschlagen" >&2
        return 1
    }
    return 0
}

# =============================================================================
# M-12: Backward-Migration — Transaktionssicherheit
# =============================================================================
test_m12_rollback_transactional() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null
    manage_test loaddata "$FIXTURES_DIR/minimal.json" >/dev/null

    # Count before rollback
    local before_count
    before_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_company;")

    # Rollback to 0006, then forward again
    manage_test migrate invoice_app 0006 >/dev/null
    manage_test migrate >/dev/null

    # Count after — data from fixtures independent of 0007 should remain
    local after_count
    after_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_company;")

    if (( after_count < before_count )); then
        echo "  Datenverlust nach Rollback+Forward: $before_count → $after_count" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-13: Backward — Ping-Pong (migrate forward, back, forward)
# =============================================================================
test_m13_ping_pong() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # Forward → Back → Forward
    manage_test migrate invoice_app 0005 >/dev/null || { echo "  Back to 0005 failed" >&2; return 1; }
    manage_test migrate >/dev/null || { echo "  Forward from 0005 failed" >&2; return 1; }
    manage_test migrate invoice_app 0006 >/dev/null || { echo "  Back to 0006 failed" >&2; return 1; }
    manage_test migrate >/dev/null || { echo "  Forward from 0006 failed" >&2; return 1; }

    # Final schema check
    local tables
    tables=$(psql_test "SELECT COUNT(tablename) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'invoice_app_%';")
    if (( tables < 5 )); then
        echo "  Nur $tables invoice_app-Tabellen nach Ping-Pong" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-14: Backward — Rollback auf Zero (alle Migrationen rückgängig)
# =============================================================================
test_m14_rollback_zero() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    local output
    output=$(manage_test migrate invoice_app zero 2>&1) || {
        echo "  Rollback auf zero fehlgeschlagen" >&2
        return 1
    }

    if echo "$output" | grep -qi "error\|traceback"; then
        echo "  Fehler beim Rollback auf zero" >&2
        return 1
    fi

    # invoice_app tables should be gone
    local tables
    tables=$(psql_test "SELECT COUNT(tablename) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'invoice_app_%';")
    if (( tables > 0 )); then
        echo "  Noch $tables invoice_app-Tabellen nach zero" >&2
        return 1
    fi

    # Forward again — should work!
    manage_test migrate >/dev/null || { echo "  Forward nach zero failed" >&2; return 1; }
    return 0
}

# =============================================================================
# M-20: Kompatibilität — migrate --plan zeigt keine Konflikte
# =============================================================================
test_m20_migrate_plan() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # --plan on an already-migrated DB should show nothing to do
    local output
    output=$(manage_test showmigrations --plan 2>&1) || {
        echo "  showmigrations --plan fehlgeschlagen" >&2
        return 1
    }

    # All migrations should be applied (no [ ] entries)
    if echo "$output" | grep -q '^\[ \]'; then
        echo "  Unangewendete Migrationen gefunden" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-21: Kompatibilität — migrate --check (keine unangewendeten)
# =============================================================================
test_m21_migrate_check() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # --check should return 0 when all applied
    manage_test migrate --check >/dev/null || {
        echo "  migrate --check meldet unangewendete Migrationen" >&2
        return 1
    }
    return 0
}

# =============================================================================
# M-22: Kompatibilität — makemigrations --check (kein Modell-Drift)
# =============================================================================
test_m22_no_model_drift() {
    reset_test_db
    manage_test migrate --run-syncdb >/dev/null

    # makemigrations --check should not detect new migrations needed
    local output
    output=$(manage_test makemigrations --check --dry-run 2>&1)
    local rc=$?

    if [[ "$rc" != "0" ]]; then
        echo "  Modell-Drift erkannt — neue Migrationen nötig" >&2
        echo "  $output" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# M-23: Kompatibilität — Sequentielle Migration von 0001 bis aktuell
# =============================================================================
test_m23_sequential_migration() {
    reset_test_db

    # Get list of invoice_app migrations
    local migrations
    migrations=$(manage_test showmigrations invoice_app --plan 2>&1 \
        | grep 'invoice_app' | sed 's/.*invoice_app\.//' | sed 's/\s.*//')

    # Apply migrations one-by-one
    for mig in $migrations; do
        local mig_name="${mig%%$'\r'}"  # strip carriage return
        manage_test migrate invoice_app "$mig_name" >/dev/null || {
            echo "  Migration $mig_name fehlgeschlagen" >&2
            return 1
        }
    done
    return 0
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}=== Ebene 2: Migrations-Tests ===${NC}\n"

    # Setup
    setup_test_env || { echo -e "${RED}Testumgebung konnte nicht gestartet werden.${NC}"; exit 2; }
    trap teardown_test_env EXIT

    if [[ -n "$filter" ]]; then
        case "$filter" in
            M-01) run_test "M-01" "Schema-Vollständigkeit nach Migration" test_m01_schema_completeness ;;
            M-02) run_test "M-02" "Datenintegrität nach Fixture-Load" test_m02_data_integrity ;;
            M-03) run_test "M-03" "Minimal-Fixtures überleben Migration" test_m03_minimal_fixtures_survive ;;
            M-04) run_test "M-04" "Migration-Performance < 30s" test_m04_migration_performance ;;
            M-05) run_test "M-05" "Migration idempotent" test_m05_migration_idempotent ;;
            M-06) run_test "M-06" "Indexes vorhanden" test_m06_indexes_exist ;;
            M-07) run_test "M-07" "Constraints vorhanden" test_m07_constraints_exist ;;
            M-08) run_test "M-08" "GoBD-Tabellen vorhanden" test_m08_gobd_tables ;;
            M-10) run_test "M-10" "Rollback letzte Migration" test_m10_rollback_last ;;
            M-11) run_test "M-11" "Rollback auf 0005" test_m11_rollback_to_0005 ;;
            M-12) run_test "M-12" "Transaktionssicherheit bei Rollback" test_m12_rollback_transactional ;;
            M-13) run_test "M-13" "Ping-Pong Forward-Back-Forward" test_m13_ping_pong ;;
            M-14) run_test "M-14" "Rollback auf Zero + Forward" test_m14_rollback_zero ;;
            M-20) run_test "M-20" "migrate --plan zeigt keine Konflikte" test_m20_migrate_plan ;;
            M-21) run_test "M-21" "migrate --check OK" test_m21_migrate_check ;;
            M-22) run_test "M-22" "Kein Modell-Drift" test_m22_no_model_drift ;;
            M-23) run_test "M-23" "Sequentielle Migration 0001→aktuell" test_m23_sequential_migration ;;
            *)    echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        # Forward-Migrations (M-01 bis M-08)
        run_test "M-01" "Schema-Vollständigkeit nach Migration" test_m01_schema_completeness
        run_test "M-02" "Datenintegrität nach Fixture-Load" test_m02_data_integrity
        run_test "M-03" "Minimal-Fixtures überleben Migration" test_m03_minimal_fixtures_survive
        run_test "M-04" "Migration-Performance < 30s" test_m04_migration_performance
        run_test "M-05" "Migration idempotent" test_m05_migration_idempotent
        run_test "M-06" "Indexes vorhanden" test_m06_indexes_exist
        run_test "M-07" "Constraints vorhanden" test_m07_constraints_exist
        run_test "M-08" "GoBD-Tabellen vorhanden" test_m08_gobd_tables

        # Backward-Migrations (M-10 bis M-14)
        run_test "M-10" "Rollback letzte Migration" test_m10_rollback_last
        run_test "M-11" "Rollback auf 0005" test_m11_rollback_to_0005
        run_test "M-12" "Transaktionssicherheit bei Rollback" test_m12_rollback_transactional
        run_test "M-13" "Ping-Pong Forward-Back-Forward" test_m13_ping_pong
        run_test "M-14" "Rollback auf Zero + Forward" test_m14_rollback_zero

        # Kompatibilität (M-20 bis M-23)
        run_test "M-20" "migrate --plan zeigt keine Konflikte" test_m20_migrate_plan
        run_test "M-21" "migrate --check OK" test_m21_migrate_check
        run_test "M-22" "Kein Modell-Drift" test_m22_no_model_drift
        run_test "M-23" "Sequentielle Migration 0001→aktuell" test_m23_sequential_migration
    fi

    # Summary
    echo ""
    echo -e "${BLUE}--- Zusammenfassung ---${NC}"
    echo -e "  Ausgeführt: $TESTS_RUN"
    echo -e "  ${GREEN}Bestanden:  $TESTS_PASSED${NC}"
    echo -e "  ${RED}Fehlgeschlagen: $TESTS_FAILED${NC}"

    if (( TESTS_FAILED > 0 )); then
        exit 1
    fi
    exit 0
}

main "$@"
