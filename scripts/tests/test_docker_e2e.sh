#!/usr/bin/env bash
# =============================================================================
# Ebene-4 Docker E2E-Tests (E2E-D-01 bis E2E-D-05)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.6.1
#
# End-to-End-Tests für den gesamten Docker-Update-Zyklus.
# Nutzt docker-compose.update-test.yml als isolierte Umgebung.
#
# Usage:
#   ./scripts/tests/test_docker_e2e.sh                   # Alle Tests
#   ./scripts/tests/test_docker_e2e.sh E2E-D-01           # Einzelner Test
#
# Benötigt: docker-compose.update-test.yml + Fixtures
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.update-test.yml"
MAIN_COMPOSE="$PROJECT_ROOT/docker-compose.yml"
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

# Run manage.py against the test environment (web-old profile)
manage_old() {
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
        web-old python project_root/manage.py "$@" 2>&1
}

# Run manage.py with web-new image
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

# Run psql against the test DB
psql_test() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -t -A -c "$1" 2>/dev/null
}

# Reset test DB
reset_test_db() {
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO erechnung_test;
        " &>/dev/null
}

# --- Setup / Teardown --------------------------------------------------------

setup_e2e_env() {
    echo -e "${BLUE}  E2E-Testumgebung starten...${NC}"
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
    echo -e "${GREEN}  E2E-Testumgebung bereit.${NC}"
}

teardown_e2e_env() {
    echo -e "${BLUE}  E2E-Testumgebung aufräumen...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
}

# =============================================================================
# E2E-D-01: Standard-Update — Migrieren + Daten bleiben erhalten
# =============================================================================
test_e2e_d01_standard_update() {
    reset_test_db

    # 1. Setup: "old" image runs migrations + loads fixtures
    manage_old migrate --run-syncdb >/dev/null
    manage_old loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    # 2. Verify data before update
    local before_partners
    before_partners=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    local before_countries
    before_countries=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")

    if (( before_partners < 3 )); then
        echo "  Setup fehlgeschlagen: nur $before_partners Partner" >&2
        return 1
    fi

    # 3. "Update": new image runs migrations
    manage_new migrate --run-syncdb >/dev/null

    # 4. Verify data after update
    local after_partners
    after_partners=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    local after_countries
    after_countries=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")

    if (( after_partners != before_partners )); then
        echo "  Partner-Verlust: $before_partners → $after_partners" >&2
        return 1
    fi

    if (( after_countries < before_countries )); then
        echo "  Länder-Verlust: $before_countries → $after_countries" >&2
        return 1
    fi

    # 5. Verify the DB is queryable with new code
    local check_output
    check_output=$(manage_new check --database default 2>&1) || true
    if echo "$check_output" | grep -qi "error"; then
        echo "  Check nach Update fehlgeschlagen" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# E2E-D-02: Update + Rollback — Daten nach Rollback zurück
# =============================================================================
test_e2e_d02_update_rollback() {
    reset_test_db

    # 1. Old image: full setup
    manage_old migrate --run-syncdb >/dev/null
    manage_old loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    local before_partners
    before_partners=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")

    # 2. "Update" with new image
    manage_new migrate --run-syncdb >/dev/null

    # 3. Simulate rollback: rollback to 0006
    manage_new migrate invoice_app 0006 >/dev/null || {
        echo "  Rollback auf 0006 fehlgeschlagen" >&2
        return 1
    }

    # 4. Forward again with old image (simulating using old code after rollback)
    manage_old migrate --run-syncdb >/dev/null

    # 5. Verify data still intact
    local after_partners
    after_partners=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")

    if (( after_partners < before_partners )); then
        echo "  Datenverlust nach Rollback: $before_partners → $after_partners" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# E2E-D-03: Multi-Step — Sequentielle Migration alle Schritte
# =============================================================================
test_e2e_d03_multi_step() {
    reset_test_db

    # Apply migrations one at a time from initial to current
    manage_new migrate invoice_app 0001 >/dev/null || { echo "  0001 failed" >&2; return 1; }
    manage_new migrate invoice_app 0002 >/dev/null || { echo "  0002 failed" >&2; return 1; }
    manage_new migrate invoice_app 0003 >/dev/null || { echo "  0003 failed" >&2; return 1; }
    manage_new migrate invoice_app 0004 >/dev/null || { echo "  0004 failed" >&2; return 1; }
    manage_new migrate invoice_app 0005 >/dev/null || { echo "  0005 failed" >&2; return 1; }
    manage_new migrate invoice_app 0006 >/dev/null || { echo "  0006 failed" >&2; return 1; }
    manage_new migrate invoice_app 0007 >/dev/null || { echo "  0007 failed" >&2; return 1; }

    # Apply all remaining (auth, contenttypes etc.)
    manage_new migrate >/dev/null

    # Load fixtures and verify
    manage_new loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    local count
    count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    if (( count < 3 )); then
        echo "  Nur $count Partner nach Multi-Step" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# E2E-D-04: Großer Datenbestand — Performance mit vielen Records
# =============================================================================
test_e2e_d04_large_dataset() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    # Insert additional records via SQL for performance testing
    # Insert 900 business partners (all NOT NULL columns must be included)
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            INSERT INTO invoice_app_businesspartner
                (partner_number, company_name, first_name, last_name, legal_name,
                 tax_id, vat_id, commercial_register,
                 is_customer, is_supplier, partner_type,
                 address_line1, address_line2, postal_code, city, state_province, country,
                 phone, fax, email, website,
                 is_active, payment_terms, preferred_currency,
                 default_reference_prefix, contact_person, accounting_contact, accounting_email,
                 created_at, updated_at)
            SELECT
                'BP-' || LPAD(g::text, 6, '0'),
                'Test Partner ' || g, '', '', '',
                '', '', '',
                true, false, 'BUSINESS',
                'Str. ' || g, '', LPAD(g::text, 5, '0'), 'Stadt ' || g, '', 'DE',
                '', '', 'test' || g || '@test.local', '',
                true, 30, 'EUR',
                '', '', '', '',
                NOW(), NOW()
            FROM generate_series(100, 999) AS g;
        " &>/dev/null

    local total
    total=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")

    # Check total
    if (( total < 100 )); then
        echo "  Nur $total Partner eingefügt" >&2
        return 1
    fi

    # Rollback and re-migrate — measure time
    local start_time
    start_time=$(date +%s)

    manage_new migrate invoice_app 0005 >/dev/null
    manage_new migrate >/dev/null

    local end_time
    end_time=$(date +%s)
    local duration=$(( end_time - start_time ))

    # Should complete in < 60s even with many records
    if (( duration > 60 )); then
        echo "  Migration mit großem Datenbestand dauerte ${duration}s (max 60s)" >&2
        return 1
    fi

    # Verify data survived
    local after_total
    after_total=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    if (( after_total < 100 )); then
        echo "  Datenverlust: $total → $after_total" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# E2E-D-05: Update bei laufendem Celery-Task (Simulation)
# =============================================================================
test_e2e_d05_update_with_celery() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/minimal.json" >/dev/null

    # Simulate a long-running task by inserting a record, then migrating
    # while "work" is happening. We just verify DB ops work during migration.

    # Start a background psql session that inserts records
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            INSERT INTO invoice_app_country
                (code, code_alpha3, numeric_code, name, name_local,
                 currency_code, currency_name, currency_symbol, default_language,
                 is_eu_member, is_eurozone, standard_vat_rate, reduced_vat_rate,
                 is_active, created_at, updated_at)
            VALUES
                ('TL', 'TLD', '999', 'Testland', 'Testland',
                 'EUR', 'Euro', '€', 'de',
                 false, false, '20.00', '10.00',
                 true, NOW(), NOW());
        " &>/dev/null &
    local bg_pid=$!

    # Run migration at the same time
    manage_new migrate >/dev/null

    # Wait for background insert
    wait "$bg_pid" 2>/dev/null || true

    # Verify both the original and new data exist
    local total
    total=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")
    if (( total < 2 )); then
        echo "  Nur $total Länder (erwartet >= 2)" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}=== Ebene 4: Docker E2E-Tests ===${NC}\n"

    # Setup
    setup_e2e_env || { echo -e "${RED}E2E-Testumgebung konnte nicht gestartet werden.${NC}"; exit 2; }
    trap teardown_e2e_env EXIT

    if [[ -n "$filter" ]]; then
        case "$filter" in
            E2E-D-01) run_test "E2E-D-01" "Standard-Update (Daten erhalten)" test_e2e_d01_standard_update ;;
            E2E-D-02) run_test "E2E-D-02" "Update + Rollback" test_e2e_d02_update_rollback ;;
            E2E-D-03) run_test "E2E-D-03" "Multi-Step Migration" test_e2e_d03_multi_step ;;
            E2E-D-04) run_test "E2E-D-04" "Großer Datenbestand" test_e2e_d04_large_dataset ;;
            E2E-D-05) run_test "E2E-D-05" "Update bei laufendem Task" test_e2e_d05_update_with_celery ;;
            *)        echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "E2E-D-01" "Standard-Update (Daten erhalten)" test_e2e_d01_standard_update
        run_test "E2E-D-02" "Update + Rollback" test_e2e_d02_update_rollback
        run_test "E2E-D-03" "Multi-Step Migration" test_e2e_d03_multi_step
        run_test "E2E-D-04" "Großer Datenbestand" test_e2e_d04_large_dataset
        run_test "E2E-D-05" "Update bei laufendem Task" test_e2e_d05_update_with_celery
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
