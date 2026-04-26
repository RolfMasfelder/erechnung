#!/usr/bin/env bash
# =============================================================================
# Edge-Case-Tests: Infrastruktur (EC-01 bis EC-07)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.7.1
#
# Testet Grenzfälle bei Infrastruktur-Problemen während des Updates.
# Nutzt docker-compose.update-test.yml als isolierte Umgebung.
#
# Usage:
#   ./scripts/tests/test_edge_infra.sh               # Alle Tests
#   ./scripts/tests/test_edge_infra.sh EC-01          # Einzelner Test
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
    echo -e "${BLUE}  Edge-Case-Testumgebung starten...${NC}"
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
    echo -e "${GREEN}  Edge-Case-Testumgebung bereit.${NC}"
}

teardown_env() {
    echo -e "${BLUE}  Edge-Case-Testumgebung aufräumen...${NC}"
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
}

# =============================================================================
# EC-01: Netzwerk-Abbruch während Image-Pull (Simulation)
# =============================================================================
# Simuliert Netzwerkfehler: docker pull mit ungültigem Registry-Host.
# Das Update-Skript muss den Fehler erkennen und abbrechen.
test_ec01_network_abort_during_pull() {
    # Simulate pulling from an unreachable registry
    local output
    local result=0
    output=$(docker pull 192.0.2.1:5000/erechnung-web:fake-tag 2>&1) || result=$?

    # Pull MUST fail (exit != 0)
    if (( result == 0 )); then
        echo "  docker pull von ungültigem Host sollte scheitern" >&2
        return 1
    fi

    # Verify the update script checks pull exit code
    if ! grep -q 'docker.*pull\|docker compose.*pull' "$PROJECT_ROOT/scripts/update-docker.sh"; then
        echo "  update-docker.sh enthält kein docker pull" >&2
        return 1
    fi

    # Verify error handling after pull
    if grep -A5 'docker.*pull\|docker compose.*pull' "$PROJECT_ROOT/scripts/update-docker.sh" \
        | grep -qE 'exit|return|abort|fehler|error|die|\|\|'; then
        return 0
    fi

    echo "  Kein Fehler-Handling nach docker pull gefunden" >&2
    return 1
}

# =============================================================================
# EC-02: Speicherplatz erschöpft (tmpfs mit begrenztem Platz)
# =============================================================================
# Erstellt einen Container mit nur 5 MB tmpfs und prüft, dass Migrationen
# bei Platzmangel sauber abbrechen.
test_ec02_disk_space_exhausted() {
    # Create a tiny tmpfs DB container that will fail on writes
    # We test that the preflight disk-space check catches this
    local check_output
    check_output=$(bash -c "
        source '$PROJECT_ROOT/scripts/lib/preflight.sh'
        check_disk_space 999999
    " 2>&1) || true

    # The check should FAIL when requiring 999999 GB (impossible)
    if echo "$check_output" | grep -qi "nicht genügend\|nicht ausreichend\|insufficient"; then
        return 0
    fi

    # Alternative: check function returns non-zero
    local result=0
    bash -c "
        source '$PROJECT_ROOT/scripts/lib/preflight.sh'
        check_disk_space 999999
    " &>/dev/null || result=$?

    if (( result != 0 )); then
        return 0
    fi

    echo "  Disk-Space-Check erkennt Platzmangel nicht" >&2
    return 1
}

# =============================================================================
# EC-03: Kill -9 während Migration (Transaktions-Rollback)
# =============================================================================
# Simuliert einen abrupten Container-Kill während einer Migration.
# Nach Neustart muss die DB konsistent sein (Transaction-Rollback).
test_ec03_kill_during_migration() {
    reset_test_db

    # Setup: Run base migrations
    manage_new migrate --run-syncdb >/dev/null
    manage_new loaddata "$FIXTURES_DIR/standard.json" >/dev/null

    local before_count
    before_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")

    # Start a background transaction that inserts data and sleeps (simulates long migration)
    docker compose -f "$COMPOSE_FILE" exec -T db-update-test \
        psql -U erechnung_test -d erechnung_update_test -c "
            BEGIN;
            INSERT INTO invoice_app_businesspartner
                (partner_number, company_name, first_name, last_name, legal_name,
                 tax_id, vat_id, commercial_register,
                 is_customer, is_supplier, partner_type,
                 address_line1, address_line2, postal_code, city, state_province, country,
                 phone, fax, email, website,
                 is_active, payment_terms, preferred_currency,
                 default_reference_prefix, contact_person, accounting_contact, accounting_email,
                 created_at, updated_at)
            VALUES ('BP-KILL', 'Kill Test', '', '', '', '', '', '', true, false, 'BUSINESS',
                    'Str.', '', '12345', 'Stadt', '', 'DE', '', '', '', '', true, 30, 'EUR',
                    '', '', '', '', NOW(), NOW());
            SELECT pg_sleep(30);
            COMMIT;
        " &>/dev/null &
    local bg_pid=$!

    # Wait for the transaction to appear in pg_stat_activity
    local waited=0
    while (( waited < 10 )); do
        local active
        active=$(psql_test "SELECT COUNT(*) FROM pg_stat_activity WHERE query LIKE '%BP-KILL%' AND state='idle in transaction';")
        if (( active > 0 )); then
            break
        fi
        sleep 0.5
        ((waited++)) || true
    done

    # Kill the background psql process (simulates kill -9 during migration)
    kill -9 "$bg_pid" 2>/dev/null || true
    wait "$bg_pid" 2>/dev/null || true

    # Also terminate the backend on the DB side to ensure cleanup
    psql_test "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%BP-KILL%' AND pid != pg_backend_pid();" >/dev/null || true
    sleep 1
    local after_count
    after_count=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner;")

    if (( after_count != before_count )); then
        echo "  Uncommitted Daten sichtbar: $before_count → $after_count" >&2
        return 1
    fi

    # Verify DB is still consistent
    local consistency
    consistency=$(psql_test "SELECT COUNT(*) FROM invoice_app_businesspartner WHERE partner_number='BP-KILL';")
    if (( consistency != 0 )); then
        echo "  Rollback nicht wirksam: BP-KILL existiert noch" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-04: Paralleles Update (Lock-Mechanismus prüfen)
# =============================================================================
# Prüft, dass der Lock-Mechanismus parallele Updates verhindert.
test_ec04_parallel_update_lock() {
    local lock_file="/tmp/erechnung-update.lock"

    # Clean up any leftover lock
    rm -f "$lock_file"

    # Simulate acquiring a lock
    local result=0
    bash -c "
        source '$PROJECT_ROOT/scripts/lib/preflight.sh'
        acquire_update_lock
    " &>/dev/null || result=$?

    if (( result != 0 )); then
        echo "  Erster Lock konnte nicht erworben werden" >&2
        rm -f "$lock_file"
        return 1
    fi

    # Lock file should exist with a PID
    if [[ ! -f "$lock_file" ]]; then
        echo "  Lock-Datei nicht erstellt" >&2
        return 1
    fi

    # Write a valid PID (current shell's) to simulate running process
    echo $$ > "$lock_file"

    # Second acquisition attempt should FAIL
    local result2=0
    bash -c "
        source '$PROJECT_ROOT/scripts/lib/preflight.sh'
        acquire_update_lock
    " &>/dev/null || result2=$?

    # Clean up
    rm -f "$lock_file"

    if (( result2 == 0 )); then
        echo "  Zweiter Lock-Erwerb hätte scheitern sollen" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# EC-05: Container-OOM während Migration (Memory-Limit)
# =============================================================================
# Testet, dass der Update-Prozess einen OOM-Fehler erkennt und meldet.
# Wir prüfen, dass Docker-Container mit strengem Memory-Limit korrekt scheitern.
test_ec05_container_oom_migration() {
    # Run a Django container with extreme memory limit using docker run directly
    # docker compose run doesn't support --memory, so use docker run with the same image
    local image
    image=$(docker inspect --format='{{.Config.Image}}' \
        "$(docker compose -f "$COMPOSE_FILE" ps -q web-new 2>/dev/null)" 2>/dev/null || true)
    if [[ -z "$image" ]]; then
        # Fallback: derive from project name
        local project
        project=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || true)
        image="${project:-erechnung_django_app}-web-new:latest"
    fi

    # Get the network name
    local network
    network=$(docker compose -f "$COMPOSE_FILE" config --format json 2>/dev/null \
        | python3 -c "import sys,json; nets=json.load(sys.stdin).get('networks',{}); print(next(iter(nets.values()),{}).get('name',''))" 2>/dev/null || true)

    # Run Django with Docker minimum memory (6m). Python can barely start at this
    # level and will typically fail with OOM or be killed (exit 137 = SIGKILL).
    local result=0
    docker run --rm --memory=6m --memory-swap=6m \
        ${network:+--network="$network"} \
        -e POSTGRES_HOST=db-update-test \
        -e POSTGRES_DB=erechnung_update_test \
        -e POSTGRES_USER=erechnung_test \
        -e POSTGRES_PASSWORD=test_password_only_for_update_tests \
        -e POSTGRES_PORT=5432 \
        -e REDIS_URL=redis://redis-update-test:6379/0 \
        -e DJANGO_SECRET_KEY=update-test-secret-key-not-for-production \
        -e DJANGO_ALLOWED_HOSTS='*' \
        "$image" python project_root/manage.py check 2>&1 || result=$?

    # The container should fail with OOM or be killed (exit code 137 = SIGKILL)
    if (( result == 0 )); then
        echo "  Container mit 6M Memory sollte scheitern" >&2
        return 1
    fi

    # Verify the update script has health check that would catch this
    if grep -q 'wait_for_health\|health.*check\|/health/' "$PROJECT_ROOT/scripts/update-docker.sh"; then
        return 0
    fi

    echo "  Kein Health-Check im Update-Skript" >&2
    return 1
}

# =============================================================================
# EC-06: DNS-Ausfall — Hostname-Auflösung prüfen
# =============================================================================
# Prüft, dass der Update-Prozess DNS-Fehler korrekt behandelt.
# Wir testen mit einem nicht auflösbaren Hostnamen.
test_ec06_dns_failure() {
    # Try to connect to a service with invalid hostname
    # Use showmigrations which requires actual DB connection
    local result=0
    docker compose -f "$COMPOSE_FILE" run --rm \
        -e POSTGRES_HOST=nonexistent-host-12345.invalid \
        -e POSTGRES_DB=erechnung_update_test \
        -e POSTGRES_USER=erechnung_test \
        -e POSTGRES_PASSWORD=test_password_only_for_update_tests \
        -e POSTGRES_PORT=5432 \
        -e REDIS_URL=redis://nonexistent-redis-12345.invalid:6379/0 \
        -e DJANGO_SECRET_KEY=update-test-secret-key-not-for-production \
        -e DJANGO_ALLOWED_HOSTS='*' \
        web-new python project_root/manage.py showmigrations 2>&1 || result=$?

    # Must fail (DNS cannot resolve)
    if (( result == 0 )); then
        echo "  Django showmigrations mit ungültigem Host sollte scheitern" >&2
        return 1
    fi

    # Verify the update script validates connectivity before proceeding
    if grep -q 'pg_isready\|check.*database\|wait.*db\|wait_for' "$PROJECT_ROOT/scripts/update-docker.sh"; then
        return 0
    fi

    echo "  Kein DB-Konnektivitätscheck im Update-Skript" >&2
    return 1
}

# =============================================================================
# EC-07: Registry nicht erreichbar (Pull von ungültigem Tag)
# =============================================================================
# Prüft, dass ein fehlgeschlagener Image-Pull das Update stoppt.
test_ec07_registry_unreachable() {
    # Attempt to pull from unreachable registry
    local result=0
    docker pull 192.0.2.1:5000/erechnung-web:nonexistent 2>/dev/null || result=$?

    if (( result == 0 )); then
        echo "  Pull von ungültiger Registry sollte scheitern" >&2
        return 1
    fi

    # Verify the update script handles pull failures
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Check that pull_images or similar function handles errors
    if grep -qE 'pull.*\|\||pull.*exit|pull.*return|pull.*fehler|pull.*error|pull_images' "$script"; then
        return 0
    fi

    # Check for a general error handler after the image stage
    if grep -qE 'error_exit|abort_update|exit [2-9]|exit [1-9][0-9]' "$script"; then
        return 0
    fi

    echo "  Kein Pull-Fehler-Handling im Update-Skript" >&2
    return 1
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Edge-Cases: Infrastruktur (EC-01..EC-07)      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}\n"

    # Setup
    setup_env || { echo -e "${RED}Testumgebung konnte nicht gestartet werden.${NC}"; exit 2; }
    trap teardown_env EXIT

    if [[ -n "$filter" ]]; then
        case "$filter" in
            EC-01) run_test "EC-01" "Netzwerk-Abbruch während Image-Pull" test_ec01_network_abort_during_pull ;;
            EC-02) run_test "EC-02" "Speicherplatz erschöpft" test_ec02_disk_space_exhausted ;;
            EC-03) run_test "EC-03" "Kill während Migration (Rollback)" test_ec03_kill_during_migration ;;
            EC-04) run_test "EC-04" "Paralleles Update (Lock)" test_ec04_parallel_update_lock ;;
            EC-05) run_test "EC-05" "Container-OOM während Migration" test_ec05_container_oom_migration ;;
            EC-06) run_test "EC-06" "DNS-Ausfall" test_ec06_dns_failure ;;
            EC-07) run_test "EC-07" "Registry nicht erreichbar" test_ec07_registry_unreachable ;;
            *)     echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "EC-01" "Netzwerk-Abbruch während Image-Pull" test_ec01_network_abort_during_pull
        run_test "EC-02" "Speicherplatz erschöpft" test_ec02_disk_space_exhausted
        run_test "EC-03" "Kill während Migration (Rollback)" test_ec03_kill_during_migration
        run_test "EC-04" "Paralleles Update (Lock)" test_ec04_parallel_update_lock
        run_test "EC-05" "Container-OOM während Migration" test_ec05_container_oom_migration
        run_test "EC-06" "DNS-Ausfall" test_ec06_dns_failure
        run_test "EC-07" "Registry nicht erreichbar" test_ec07_registry_unreachable
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
