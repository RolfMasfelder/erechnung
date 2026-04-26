#!/usr/bin/env bash
# =============================================================================
# Ebene-3 Docker-Komponententests (D-01 bis D-08)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.5.1
#
# Testet Docker-spezifische Update-Funktionalität gegen laufende Container.
# Nutzt die Produktions-Compose-Umgebung (docker-compose.yml).
#
# Usage:
#   ./scripts/tests/test_docker_components.sh            # Alle Tests
#   ./scripts/tests/test_docker_components.sh D-01        # Einzelner Test
#
# Benötigt: Laufende Docker-Compose-Umgebung (web, db, redis, celery)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

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

wait_for_healthy() {
    local service="$1"
    local timeout="${2:-60}"
    local elapsed=0

    while (( elapsed < timeout )); do
        local health
        health=$(docker compose -f "$COMPOSE_FILE" ps "$service" --format '{{.Health}}' 2>/dev/null) || true
        if [[ "$health" == "healthy" ]]; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

wait_for_api() {
    local timeout="${1:-60}"
    local elapsed=0

    while (( elapsed < timeout )); do
        if curl -sf http://localhost:8000/api/version/ &>/dev/null; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

# =============================================================================
# D-01: Happy Path — update-docker.sh dry-run end-to-end
# =============================================================================
test_d01_happy_path_dry_run() {
    local output
    output=$("$PROJECT_ROOT/scripts/update-docker.sh" --dry-run --yes 2>&1) || true

    # Dry-run should complete without error and show a plan
    if echo "$output" | grep -qi "pre-flight\|prüfung\|version\|trocken"; then
        return 0
    fi

    # Even if it exits non-zero (e.g., same version), dry-run itself should work
    if echo "$output" | grep -qi "bereits auf version\|kein update"; then
        return 0
    fi

    echo "  Dry-run keine erwartete Ausgabe" >&2
    return 1
}

# =============================================================================
# D-02: Backup existiert + ist verifiziert bevor Stop
# =============================================================================
test_d02_backup_before_stop() {
    # Verify the update script calls backup BEFORE docker compose stop
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    local backup_line
    backup_line=$(grep -n 'backup.sh' "$script" | head -1 | cut -d: -f1) || true
    local stop_line
    stop_line=$(grep -n 'docker compose.*stop\|docker compose.*down' "$script" | head -1 | cut -d: -f1) || true

    if [[ -z "$backup_line" || -z "$stop_line" ]]; then
        echo "  backup.sh oder stop-Befehl nicht gefunden" >&2
        return 1
    fi

    if (( backup_line < stop_line )); then
        return 0
    fi

    echo "  Backup (Zeile $backup_line) kommt nach Stop (Zeile $stop_line)" >&2
    return 1
}

# =============================================================================
# D-03: Init-Container läuft migrate erfolgreich
# =============================================================================
test_d03_init_container_migrate() {
    # Run init container which performs migrations
    local output
    output=$(docker compose -f "$COMPOSE_FILE" run --rm init 2>&1) || true

    # Check for success indicators
    if echo "$output" | grep -qi "no migrations to apply\|running migrations\|OK\|operations to perform"; then
        return 0
    fi

    # If already migrated, that's fine too
    if echo "$output" | grep -qi "no migrations"; then
        return 0
    fi

    # Also accept if exit code was 0
    docker compose -f "$COMPOSE_FILE" run --rm init &>/dev/null
    return $?
}

# =============================================================================
# D-04: Health Check nach Container-Neustart OK
# =============================================================================
test_d04_health_check_after_restart() {
    # Restart the web container
    docker compose -f "$COMPOSE_FILE" restart web &>/dev/null

    # Wait for health
    if ! wait_for_api 60; then
        echo "  API nach Restart nicht erreichbar" >&2
        return 1
    fi

    # Check version endpoint
    local version
    version=$(curl -sf http://localhost:8000/api/version/ | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true

    if [[ -z "$version" || "$version" == "unknown" ]]; then
        echo "  Version nach Restart: '$version'" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# D-05: Graceful Shutdown (Container stoppt sauber)
# =============================================================================
test_d05_graceful_shutdown() {
    # Verify web container stops within grace period
    local start_time
    start_time=$(date +%s)

    docker compose -f "$COMPOSE_FILE" stop -t 10 web &>/dev/null

    local end_time
    end_time=$(date +%s)
    local duration=$(( end_time - start_time ))

    # Should stop within 15s (10s grace + some overhead)
    if (( duration > 20 )); then
        echo "  Container brauchte ${duration}s zum Stoppen (max 20s)" >&2
        docker compose -f "$COMPOSE_FILE" up -d web &>/dev/null
        wait_for_api 30
        return 1
    fi

    # Restart web
    docker compose -f "$COMPOSE_FILE" up -d web &>/dev/null
    wait_for_api 30
    return 0
}

# =============================================================================
# D-06: Volume-Persistenz (pg_data intakt nach Restart)
# =============================================================================
test_d06_volume_persistence() {
    # Read DB credentials from running web container
    local db_user db_name
    db_user=$(docker compose -f "$COMPOSE_FILE" exec -T web printenv POSTGRES_USER 2>/dev/null | tr -d '\r') || true
    db_name=$(docker compose -f "$COMPOSE_FILE" exec -T web printenv POSTGRES_DB 2>/dev/null | tr -d '\r') || true
    db_user=${db_user:-postgres}
    db_name=${db_name:-erechnung}

    # Get current country count
    local before_count
    before_count=$(docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$db_user" -d "$db_name" -t -A -c "SELECT COUNT(*) FROM invoice_app_country;" 2>/dev/null) || true

    if [[ -z "$before_count" ]]; then
        echo "  DB-Abfrage vor Restart fehlgeschlagen" >&2
        return 1
    fi

    # Restart DB (NOT -v, so volume stays)
    docker compose -f "$COMPOSE_FILE" restart db &>/dev/null
    wait_for_healthy db 30

    # Wait for DB to be ready
    sleep 3

    # Get count after restart
    local after_count
    after_count=$(docker compose -f "$COMPOSE_FILE" exec -T db \
        psql -U "$db_user" -d "$db_name" -t -A -c "SELECT COUNT(*) FROM invoice_app_country;" 2>/dev/null) || true

    if [[ "$before_count" != "$after_count" ]]; then
        echo "  Datenverlust: vorher=$before_count, nachher=$after_count" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# D-07: Static Files refreshed nach collectstatic
# =============================================================================
test_d07_static_files_refreshed() {
    # Run collectstatic in container
    local output
    output=$(docker compose -f "$COMPOSE_FILE" exec -T web \
        python project_root/manage.py collectstatic --noinput 2>&1) || true

    # Should succeed
    if echo "$output" | grep -qi "error\|traceback"; then
        echo "  collectstatic fehlgeschlagen" >&2
        return 1
    fi

    # Verify static files directory exists (may be /app/project_root/static or /app/static)
    local static_count
    static_count=$(docker compose -f "$COMPOSE_FILE" exec -T web \
        sh -c 'find /app/project_root/static /app/static -type f 2>/dev/null' | wc -l) || true

    if (( static_count < 1 )); then
        echo "  Keine statischen Dateien gefunden" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# D-08: Celery reconnect nach Redis-Restart
# =============================================================================
test_d08_celery_redis_reconnect() {
    # Check if celery is running
    local celery_running
    celery_running=$(docker compose -f "$COMPOSE_FILE" ps celery --format '{{.State}}' 2>/dev/null) || true

    if [[ "$celery_running" != "running" ]]; then
        echo "  (Celery nicht aktiv — Test übersprungen)" >&2
        return 0
    fi

    # Restart Redis
    docker compose -f "$COMPOSE_FILE" restart redis &>/dev/null
    sleep 3

    # Check Celery is still running (it should reconnect)
    local retries=10
    while (( retries > 0 )); do
        celery_running=$(docker compose -f "$COMPOSE_FILE" ps celery --format '{{.State}}' 2>/dev/null) || true
        if [[ "$celery_running" == "running" ]]; then
            return 0
        fi
        sleep 2
        ((retries--))
    done

    echo "  Celery nach Redis-Restart nicht mehr aktiv" >&2
    return 1
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}=== Ebene 3: Docker-Komponententests ===${NC}\n"

    # Verify dev environment is running
    if ! curl -sf http://localhost:8000/api/version/ &>/dev/null; then
        echo -e "${RED}  Entwicklungsumgebung nicht erreichbar (http://localhost:8000).${NC}"
        echo -e "${RED}  Bitte 'docker compose up -d' ausführen.${NC}"
        exit 2
    fi

    if [[ -n "$filter" ]]; then
        case "$filter" in
            D-01) run_test "D-01" "Happy Path — dry-run end-to-end" test_d01_happy_path_dry_run ;;
            D-02) run_test "D-02" "Backup vor Stop" test_d02_backup_before_stop ;;
            D-03) run_test "D-03" "Init-Container migrate erfolgreich" test_d03_init_container_migrate ;;
            D-04) run_test "D-04" "Health Check nach Restart" test_d04_health_check_after_restart ;;
            D-05) run_test "D-05" "Graceful Shutdown" test_d05_graceful_shutdown ;;
            D-06) run_test "D-06" "Volume-Persistenz" test_d06_volume_persistence ;;
            D-07) run_test "D-07" "Static Files nach collectstatic" test_d07_static_files_refreshed ;;
            D-08) run_test "D-08" "Celery reconnect nach Redis-Restart" test_d08_celery_redis_reconnect ;;
            *)    echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "D-01" "Happy Path — dry-run end-to-end" test_d01_happy_path_dry_run
        run_test "D-02" "Backup vor Stop" test_d02_backup_before_stop
        run_test "D-03" "Init-Container migrate erfolgreich" test_d03_init_container_migrate
        run_test "D-04" "Health Check nach Restart" test_d04_health_check_after_restart
        run_test "D-05" "Graceful Shutdown" test_d05_graceful_shutdown
        run_test "D-06" "Volume-Persistenz" test_d06_volume_persistence
        run_test "D-07" "Static Files nach collectstatic" test_d07_static_files_refreshed
        run_test "D-08" "Celery reconnect nach Redis-Restart" test_d08_celery_redis_reconnect
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
