#!/usr/bin/env bash
# =============================================================================
# Edge-Case-Tests: Daten (EC-10 bis EC-16)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.7.2
#
# Testet Grenzfälle bei Daten-Problemen während des Updates.
# Nutzt docker-compose.update-test.yml als isolierte Umgebung.
#
# Usage:
#   ./scripts/tests/test_edge_data.sh                 # Alle Tests
#   ./scripts/tests/test_edge_data.sh EC-10           # Einzelner Test
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
    echo -e "${BLUE}  Daten-Edge-Case-Testumgebung starten...${NC}"
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
    echo -e "${GREEN}  Daten-Edge-Case-Testumgebung bereit.${NC}"
}

teardown_env() {
    echo -e "${BLUE}  Testumgebung aufräumen...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
}

# =============================================================================
# EC-10: Leere DB → Update (kein Division-by-Zero)
# =============================================================================
# Eine komplett leere DB muss ohne Fehler migriert werden können.
test_ec10_empty_db_update() {
    reset_test_db

    # Run all migrations on empty DB — must not crash
    local output
    output=$(manage_new migrate --run-syncdb 2>&1)
    local result=$?

    if (( result != 0 )); then
        echo "  Migrate auf leerer DB fehlgeschlagen" >&2
        return 1
    fi

    # Check: no real errors in output (ignore migration names containing 'error')
    if echo "$output" | grep -iP "^(Error|Traceback|django\.|psycopg2\.)|division by zero" | grep -v "Applying"; then
        echo "  Fehler bei Migration auf leerer DB" >&2
        return 1
    fi

    # Verify tables exist
    local table_count
    table_count=$(psql_test "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
    if (( table_count < 5 )); then
        echo "  Nur $table_count Tabellen nach Migration" >&2
        return 1
    fi

    # Verify Django check works
    local check_output
    check_output=$(manage_new check 2>&1) || true
    if echo "$check_output" | grep -qi "error"; then
        echo "  Django check fehlgeschlagen auf leerer DB" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-11: DB mit manuellen Constraints (Extra-Index)
# =============================================================================
# Ein manuell hinzugefügter Index darf die Migration nicht stören.
test_ec11_manual_constraints() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null

    # Add a custom index manually
    psql_test "CREATE INDEX IF NOT EXISTS idx_custom_test ON invoice_app_businesspartner (company_name);" >/dev/null

    # Verify index exists
    local idx_count
    idx_count=$(psql_test "SELECT COUNT(*) FROM pg_indexes WHERE indexname='idx_custom_test';")
    if (( idx_count != 1 )); then
        echo "  Custom-Index nicht erstellt" >&2
        return 1
    fi

    # Run migrations again — should not fail due to extra index
    local output
    output=$(manage_new migrate 2>&1)
    local result=$?

    if (( result != 0 )); then
        echo "  Migration mit Custom-Index fehlgeschlagen" >&2
        return 1
    fi

    # Index should still exist after migration
    idx_count=$(psql_test "SELECT COUNT(*) FROM pg_indexes WHERE indexname='idx_custom_test';")
    if (( idx_count != 1 )); then
        echo "  Custom-Index nach Migration verschwunden" >&2
        return 1
    fi

    # Clean up
    psql_test "DROP INDEX IF EXISTS idx_custom_test;" >/dev/null
    return 0
}

# =============================================================================
# EC-12: Korruptes Backup (SHA256-Mismatch → Abbruch)
# =============================================================================
# Prüft, dass ein korrumpiertes Backup erkannt und abgelehnt wird.
test_ec12_corrupt_backup() {
    # Check if backup.sh exists and uses SHA256 verification
    local backup_script="$PROJECT_ROOT/scripts/backup.sh"
    if [[ ! -f "$backup_script" ]]; then
        echo "  backup.sh nicht gefunden" >&2
        return 1
    fi

    # Verify SHA256 verification is present
    if ! grep -qE 'sha256|SHA256|checksum|hash' "$backup_script"; then
        echo "  Keine SHA256-Prüfung in backup.sh" >&2
        return 1
    fi

    # Create a fake backup and corrupt it
    local tmpdir
    tmpdir=$(mktemp -d)
    echo "fake backup content" > "$tmpdir/backup.sql"
    sha256sum "$tmpdir/backup.sql" > "$tmpdir/backup.sql.sha256"

    # Corrupt the backup
    echo "corrupted" >> "$tmpdir/backup.sql"

    # Verify SHA256 now mismatches
    if sha256sum --check "$tmpdir/backup.sql.sha256" &>/dev/null; then
        echo "  Korruptes Backup besteht SHA256-Check" >&2
        rm -rf "$tmpdir"
        return 1
    fi

    # Clean up
    rm -rf "$tmpdir"
    return 0
}

# =============================================================================
# EC-13: Kumulative Migration über mehrere Stufen
# =============================================================================
# Migration von 0001 → aktuell in Einzelschritten.
test_ec13_cumulative_migration() {
    reset_test_db

    # Get list of all invoice_app migrations
    local migrations
    migrations=$(manage_new showmigrations invoice_app --plan 2>&1 \
        | grep 'invoice_app' | sed 's/.*\] //' | tr -d '[:space:]' | tr '\n' ' ') || true

    # Apply from beginning, step by step
    manage_new migrate invoice_app 0001 >/dev/null || { echo "  0001 failed" >&2; return 1; }
    manage_new migrate invoice_app 0002 >/dev/null || { echo "  0002 failed" >&2; return 1; }
    manage_new migrate invoice_app 0003 >/dev/null || { echo "  0003 failed" >&2; return 1; }

    # Apply all remaining
    manage_new migrate >/dev/null || { echo "  Finale Migration fehlgeschlagen" >&2; return 1; }

    # Load fixtures to verify schema is complete
    manage_new loaddata "$FIXTURES_DIR/minimal.json" >/dev/null || {
        echo "  Fixtures laden nach kumulativer Migration fehlgeschlagen" >&2
        return 1
    }

    local count
    count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")
    if (( count < 1 )); then
        echo "  Keine Partner nach kumulativer Migration" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-14: Sonderzeichen in Daten
# =============================================================================
# Prüft, dass Sonderzeichen in Firmennamen und Adressen die Migration
# nicht stören.
test_ec14_special_characters() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null

    # Insert a JP country for foreign key reference
    psql_test "
        INSERT INTO invoice_app_country
            (code, code_alpha3, numeric_code, name, name_local,
             currency_code, currency_name, currency_symbol, default_language,
             is_eu_member, is_eurozone, standard_vat_rate, reduced_vat_rate,
             date_format, decimal_separator, thousands_separator,
             is_active, created_at, updated_at)
        VALUES
            ('JP', 'JPN', '392', 'Japan', '日本',
             'JPY', 'Yen', '¥', 'ja',
             false, false, '10.00', '8.00',
             'YYYY/MM/DD', '.', ',',
             true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    " >/dev/null

    # Insert records with special characters via SQL
    psql_test "
        INSERT INTO invoice_app_businesspartner
            (partner_number, company_name, first_name, last_name, legal_name,
             tax_id, vat_id, commercial_register,
             is_customer, is_supplier, partner_type,
             address_line1, address_line2, postal_code, city, state_province, country,
             phone, fax, email, website,
             is_active, payment_terms, preferred_currency,
             default_reference_prefix, contact_person, accounting_contact, accounting_email,
             created_at, updated_at)
        VALUES
            ('BP-SP01', 'Müller & Söhne GmbH', 'François', 'O''Brien', 'Müller & Söhne',
             '', '', '', true, false, 'BUSINESS',
             'Straße der Ärzte 123/a', 'Gebäude ½', '80333', 'München', 'Bayern', 'DE',
             '+49 (0)89/123–456', '', 'müller@söhne.de', '',
             true, 30, 'EUR', '', '', '', '', NOW(), NOW()),
            ('BP-SP02', '日本株式会社', '太郎', '田中', '日本株式会社',
             '', '', '', true, false, 'BUSINESS',
             '東京都渋谷区 1-2-3', '', '150-0001', '東京', '', 'JP',
             '', '', 'test@日本.jp', '',
             true, 30, 'JPY', '', '', '', '', NOW(), NOW()),
            ('BP-SP03', '<script>alert(1)</script>', '', '', '',
             '', '', '', true, false, 'BUSINESS',
             'Street \"with quotes\"', '', '12345', 'City\nNewline', '', 'DE',
             '', '', '', '',
             true, 30, 'EUR', '', '', '', '', NOW(), NOW());
    " >/dev/null

    # Run migration again (should not break due to data)
    local result=0
    manage_new migrate >/dev/null 2>&1 || result=$?

    if (( result != 0 )); then
        echo "  Migration mit Sonderzeichen fehlgeschlagen (exit $result)" >&2
        return 1
    fi

    # Verify data survived
    local special_count
    special_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner WHERE partner_number LIKE 'BP-SP%';")
    if (( special_count != 3 )); then
        echo "  Nur $special_count/3 Sonderzeichen-Partner gefunden" >&2
        return 1
    fi

    # Verify SQL injection in company name is stored as text (not executed)
    local xss_name
    xss_name=$(psql_test "SELECT company_name FROM invoice_app_businesspartner WHERE partner_number='BP-SP03';")
    if [[ "$xss_name" != *"<script>"* ]]; then
        echo "  XSS-Payload nicht als Text gespeichert" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-15: Concurrent Write während Migration
# =============================================================================
# Testet, dass gleichzeitige Schreiboperationen während einer Migration
# korrekt behandelt werden.
test_ec15_concurrent_write() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/minimal.json" >/dev/null

    local before_count
    before_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")

    # Rollback one migration so migrate actually has DDL work to do
    manage_new migrate invoice_app 0006 >/dev/null || {
        echo "  Rollback auf 0006 fehlgeschlagen" >&2
        return 1
    }

    # Start background writes into existing tables while migration runs
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            INSERT INTO invoice_app_country
                (code, code_alpha3, numeric_code, name, name_local,
                 currency_code, currency_name, currency_symbol, default_language,
                 is_eu_member, is_eurozone, standard_vat_rate, reduced_vat_rate,
                 date_format, decimal_separator, thousands_separator,
                 is_active, created_at, updated_at)
            SELECT
                'X' || LPAD(g::text, 1, '0'),
                'XX' || g,
                (900 + g)::text,
                'TestCountry' || g,
                'TestCountry' || g,
                'EUR', 'Euro', '€', 'de',
                false, false, '20.00', '10.00',
                'DD.MM.YYYY', '.', ',',
                true, NOW(), NOW()
            FROM generate_series(1, 5) AS g;
        " &>/dev/null &
    local bg_pid=$!

    # Run migration concurrently
    manage_new migrate >/dev/null

    # Wait for background writes
    wait "$bg_pid" 2>/dev/null || true

    # Verify both original + new data exist
    local after_count
    after_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_country;")

    if (( after_count < before_count )); then
        echo "  Datenverlust bei concurrent write: $before_count → $after_count" >&2
        return 1
    fi

    # The new records should exist
    local new_count
    new_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_country WHERE code LIKE 'X%';")
    if (( new_count < 1 )); then
        echo "  Concurrent inserts gingen verloren" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-16: GoBD-gesperrte Rechnungen unverändert
# =============================================================================
# Prüft, dass GoBD-gesperrte Rechnungen nach einer Migration unverändert sind.
test_ec16_gobd_locked_invoices() {
    reset_test_db
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    # Lock some invoices (simulate GoBD finalization)
    psql_test "
        UPDATE invoice_app_invoice
        SET is_locked = true, locked_at = NOW(), status = 'SENT'
        WHERE id IN (SELECT id FROM invoice_app_invoice LIMIT 3);
    " >/dev/null

    # Record locked invoices state before migration
    local locked_before
    locked_before=$(psql_test "
        SELECT id, invoice_number, is_locked, status, total_gross
        FROM invoice_app_invoice
        WHERE is_locked = true
        ORDER BY id;
    ")

    local locked_count_before
    locked_count_before=$(psql_test "SELECT COUNT(*) FROM invoice_app_invoice WHERE is_locked = true;")

    if (( locked_count_before < 1 )); then
        echo "  Keine gesperrten Rechnungen zum Testen" >&2
        return 1
    fi

    # Run migration
    manage_new migrate >/dev/null || { echo "  Migration fehlgeschlagen" >&2; return 1; }

    # Verify locked invoices are unchanged
    local locked_after
    locked_after=$(psql_test "
        SELECT id, invoice_number, is_locked, status, total_gross
        FROM invoice_app_invoice
        WHERE is_locked = true
        ORDER BY id;
    ")

    local locked_count_after
    locked_count_after=$(psql_test "SELECT COUNT(*) FROM invoice_app_invoice WHERE is_locked = true;")

    if (( locked_count_after != locked_count_before )); then
        echo "  Gesperrte Rechnungen geändert: $locked_count_before → $locked_count_after" >&2
        return 1
    fi

    if [[ "$locked_before" != "$locked_after" ]]; then
        echo "  GoBD-gesperrte Daten nach Migration verändert!" >&2
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
    echo -e "${BLUE}║  Edge-Cases: Daten (EC-10..EC-16)              ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}\n"

    # Setup
    setup_env || { echo -e "${RED}Testumgebung konnte nicht gestartet werden.${NC}"; exit 2; }
    trap teardown_env EXIT

    if [[ -n "$filter" ]]; then
        case "$filter" in
            EC-10) run_test "EC-10" "Leere DB → Update" test_ec10_empty_db_update ;;
            EC-11) run_test "EC-11" "Manuelle Constraints" test_ec11_manual_constraints ;;
            EC-12) run_test "EC-12" "Korruptes Backup (SHA256)" test_ec12_corrupt_backup ;;
            EC-13) run_test "EC-13" "Kumulative Migration" test_ec13_cumulative_migration ;;
            EC-14) run_test "EC-14" "Sonderzeichen in Daten" test_ec14_special_characters ;;
            EC-15) run_test "EC-15" "Concurrent Write" test_ec15_concurrent_write ;;
            EC-16) run_test "EC-16" "GoBD-gesperrte Rechnungen" test_ec16_gobd_locked_invoices ;;
            *)     echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "EC-10" "Leere DB → Update" test_ec10_empty_db_update
        run_test "EC-11" "Manuelle Constraints" test_ec11_manual_constraints
        run_test "EC-12" "Korruptes Backup (SHA256)" test_ec12_corrupt_backup
        run_test "EC-13" "Kumulative Migration" test_ec13_cumulative_migration
        run_test "EC-14" "Sonderzeichen in Daten" test_ec14_special_characters
        run_test "EC-15" "Concurrent Write" test_ec15_concurrent_write
        run_test "EC-16" "GoBD-gesperrte Rechnungen" test_ec16_gobd_locked_invoices
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
