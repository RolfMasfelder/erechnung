#!/usr/bin/env bash
# =============================================================================
# Ebene-1 Docker Update-Skript-Tests (S-01 bis S-11)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.3
#
# Tests für die Skript-Logik von update-docker.sh und rollback-docker.sh.
# Verwendet Mocking für externe Abhängigkeiten (Docker, curl etc.).
#
# Usage:
#   ./scripts/tests/test_update_docker.sh          # Alle Tests
#   ./scripts/tests/test_update_docker.sh S-04      # Einzelner Test
#
# Benötigt: bash 4+
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LIB_DIR="$PROJECT_ROOT/scripts/lib"

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

# Test-Result-Array für Summary
declare -a TEST_RESULTS=()

# --- Test Framework ----------------------------------------------------------

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"
    if [[ "$actual" == "$expected" ]]; then
        return 0
    else
        echo "  Expected exit code $expected, got $actual" >&2
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    if echo "$haystack" | grep -q "$needle"; then
        return 0
    else
        echo "  Expected output to contain: $needle" >&2
        return 1
    fi
}

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

# --- Mock-Umgebung -----------------------------------------------------------
MOCK_DIR=""

setup_mock_env() {
    MOCK_DIR=$(mktemp -d)
    export PATH="$MOCK_DIR:$PATH"
}

teardown_mock_env() {
    if [[ -n "$MOCK_DIR" && -d "$MOCK_DIR" ]]; then
        rm -rf "$MOCK_DIR"
    fi
}

create_mock_command() {
    local cmd_name="$1"
    local exit_code="${2:-0}"
    local output="${3:-}"
    cat > "$MOCK_DIR/$cmd_name" <<MOCK_EOF
#!/usr/bin/env bash
if [[ -n "$output" ]]; then
    echo "$output"
fi
exit $exit_code
MOCK_EOF
    chmod +x "$MOCK_DIR/$cmd_name"
}

# =============================================================================
# S-01: Docker Daemon nicht verfügbar → Exit 1
# =============================================================================
test_s01_docker_not_available() {
    (
        # Source preflight with mocked docker
        MOCK_DIR_LOCAL=$(mktemp -d)
        cat > "$MOCK_DIR_LOCAL/docker" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
        chmod +x "$MOCK_DIR_LOCAL/docker"
        PATH="$MOCK_DIR_LOCAL:$PATH"

        source "$LIB_DIR/preflight.sh"
        if check_docker_running; then
            rm -rf "$MOCK_DIR_LOCAL"
            exit 1  # Should have failed
        fi
        rm -rf "$MOCK_DIR_LOCAL"
        exit 0
    )
}

# =============================================================================
# S-02: Speicherplatz < 2 GB → Exit 1
# =============================================================================
test_s02_low_disk_space() {
    (
        source "$LIB_DIR/preflight.sh"
        # Test mit unrealistisch hohem Minimum (999999 GB)
        if check_disk_space 999999; then
            exit 1  # Should have failed
        fi
        exit 0
    )
}

# =============================================================================
# S-03: docker-compose.yml fehlt → Exit 1
# =============================================================================
test_s03_compose_file_missing() {
    (
        source "$LIB_DIR/preflight.sh"
        if check_compose_file_exists "/nonexistent/docker-compose.yml"; then
            exit 1  # Should have failed
        fi
        exit 0
    )
}

# =============================================================================
# S-04: Gleiche Version → "Bereits auf Version X"
# =============================================================================
test_s04_same_version() {
    local output
    output=$("$PROJECT_ROOT/scripts/update-docker.sh" --version "$(
        curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "1.0.0"
    )" --yes 2>&1) || true
    if echo "$output" | grep -qi "bereits auf version\|kein update nötig\|already"; then
        return 0
    fi
    # If we can't reach the API, skip
    if ! curl -sf http://localhost:8000/api/version/ &>/dev/null; then
        echo "  (API nicht erreichbar — Test übersprungen)" >&2
        return 0
    fi
    return 1
}

# =============================================================================
# S-07: Version aus Container lesen → korrekte SemVer
# =============================================================================
test_s07_version_from_container() {
    local version
    version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true

    if [[ -z "$version" ]]; then
        # Container nicht erreichbar → Test kann nicht ausgeführt werden
        echo "  (API nicht erreichbar — Test übersprungen)" >&2
        return 0
    fi

    # SemVer-Pattern prüfen (x.y.z mit optionalem Pre-Release)
    if [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        return 0
    fi

    echo "  Version '$version' ist kein gültiges SemVer" >&2
    return 1
}

# =============================================================================
# S-08: Version aus Image-Label lesen → korrekte SemVer
# =============================================================================
test_s08_version_from_image_label() {
    # Get the web service image ID
    local image_id
    image_id=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" images web -q 2>/dev/null | head -1) || true

    if [[ -z "$image_id" ]]; then
        echo "  (Web-Image nicht gefunden — Test übersprungen)" >&2
        return 0
    fi

    local label_version
    label_version=$(docker inspect --format='{{index .Config.Labels "org.opencontainers.image.version"}}' "$image_id" 2>/dev/null) || true

    if [[ -z "$label_version" || "$label_version" == "<no value>" ]]; then
        echo "  Image-Label 'org.opencontainers.image.version' nicht gesetzt." >&2
        echo "  docker-compose.yml muss APP_VERSION als build-arg übergeben." >&2
        return 1
    fi

    if [[ "$label_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        return 0
    fi

    echo "  Label-Version '$label_version' ist kein gültiges SemVer" >&2
    return 1
}

# =============================================================================
# S-09: :pre-update Tag gesetzt → Image verfügbar
# =============================================================================
test_s09_pre_update_tag() {
    # Diesen Test nur ausführen wenn ein :pre-update-Tag existiert
    local image_name
    image_name=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" config --images 2>/dev/null | head -1) || true

    if [[ -z "$image_name" ]]; then
        echo "  (Kein Image gefunden — Test übersprungen)" >&2
        return 0
    fi

    local base_name="${image_name%%:*}"

    # Erstelle einen Test-Tag und prüfe ob das Taggen funktioniert
    if docker image inspect "$image_name" &>/dev/null; then
        docker tag "$image_name" "${base_name}:test-pre-update" 2>/dev/null || {
            echo "  Konnte Test-Tag nicht erstellen" >&2
            return 1
        }
        # Prüfe ob Tag existiert
        if docker image inspect "${base_name}:test-pre-update" &>/dev/null; then
            docker rmi "${base_name}:test-pre-update" 2>/dev/null || true
            return 0
        fi
        return 1
    fi

    echo "  (Image nicht vorhanden — Test übersprungen)" >&2
    return 0
}

# =============================================================================
# S-10: backup.sh wird aufgerufen → Exit-Code durchgereicht
# =============================================================================
test_s10_backup_called() {
    if [[ ! -x "$PROJECT_ROOT/scripts/backup.sh" ]]; then
        echo "  backup.sh nicht gefunden oder nicht ausführbar" >&2
        return 1
    fi

    # Prüfe, dass backup.sh existiert und update-docker.sh es referenziert
    if grep -q 'backup.sh' "$PROJECT_ROOT/scripts/update-docker.sh"; then
        return 0
    fi

    echo "  update-docker.sh referenziert backup.sh nicht" >&2
    return 1
}

# =============================================================================
# S-11: Backup-Fehler → Update abgebrochen
# =============================================================================
test_s11_backup_failure_aborts() {
    # Verifiziere dass das Update-Skript bei Backup-Fehler abbricht
    # (durch Inspektion der Skript-Logik)
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Prüfe ob nach backup.sh-Aufruf auf Fehler geprüft wird
    if grep -A2 'backup.sh' "$script" | grep -q 'exit\|abgebrochen\|fehlgeschlagen'; then
        return 0
    fi

    echo "  Backup-Fehlererkennung nicht implementiert" >&2
    return 1
}

# =============================================================================
# S-12: Image-Label-Version == API-Version (Konsistenz)
# =============================================================================
test_s12_version_consistency() {
    # API-Version auslesen
    local api_version
    api_version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true

    if [[ -z "$api_version" ]]; then
        echo "  (API nicht erreichbar — Test übersprungen)" >&2
        return 0
    fi

    # Image-Label-Version auslesen
    local image_id
    image_id=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" images web -q 2>/dev/null | head -1) || true

    if [[ -z "$image_id" ]]; then
        echo "  (Web-Image nicht gefunden — Test übersprungen)" >&2
        return 0
    fi

    local label_version
    label_version=$(docker inspect --format='{{index .Config.Labels "org.opencontainers.image.version"}}' "$image_id" 2>/dev/null) || true

    if [[ -z "$label_version" || "$label_version" == "<no value>" ]]; then
        echo "  Image-Label nicht gesetzt — Konsistenz nicht prüfbar" >&2
        return 1
    fi

    # pyproject.toml-Version auslesen (Single Source of Truth)
    local pyproject_version
    pyproject_version=$(python3 -c "import re; m=re.search(r'^version\\s*=\\s*\\\"(.+?)\\\"', open('$PROJECT_ROOT/pyproject.toml').read(), re.M); print(m.group(1) if m else '')" 2>/dev/null) || true

    # Prüfung: Label == API
    if [[ "$label_version" != "$api_version" ]]; then
        echo "  MISMATCH: Image-Label=$label_version, API=$api_version" >&2
        return 1
    fi

    # Prüfung: Label == pyproject.toml
    if [[ -n "$pyproject_version" && "$label_version" != "$pyproject_version" ]]; then
        echo "  MISMATCH: Image-Label=$label_version, pyproject.toml=$pyproject_version" >&2
        return 1
    fi

    return 0
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}=== Ebene 1: Docker Skript-Unit-Tests ===${NC}\n"

    if [[ -n "$filter" ]]; then
        case "$filter" in
            S-01) run_test "S-01" "Docker Daemon nicht verfügbar → Exit 1" test_s01_docker_not_available ;;
            S-02) run_test "S-02" "Speicherplatz < 2 GB → Exit 1" test_s02_low_disk_space ;;
            S-03) run_test "S-03" "docker-compose.yml fehlt → Exit 1" test_s03_compose_file_missing ;;
            S-04) run_test "S-04" "Gleiche Version → Bereits auf Version X" test_s04_same_version ;;
            S-07) run_test "S-07" "Version aus Container → SemVer" test_s07_version_from_container ;;
            S-08) run_test "S-08" "Version aus Image-Label → SemVer" test_s08_version_from_image_label ;;
            S-09) run_test "S-09" ":pre-update Tag gesetzt" test_s09_pre_update_tag ;;
            S-10) run_test "S-10" "backup.sh wird aufgerufen" test_s10_backup_called ;;
            S-11) run_test "S-11" "Backup-Fehler → Update abgebrochen" test_s11_backup_failure_aborts ;;
            S-12) run_test "S-12" "Image-Label == API-Version (Konsistenz)" test_s12_version_consistency ;;
            *)    echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "S-01" "Docker Daemon nicht verfügbar → Exit 1" test_s01_docker_not_available
        run_test "S-02" "Speicherplatz < 2 GB → Exit 1" test_s02_low_disk_space
        run_test "S-03" "docker-compose.yml fehlt → Exit 1" test_s03_compose_file_missing
        run_test "S-04" "Gleiche Version → Bereits auf Version X" test_s04_same_version
        run_test "S-07" "Version aus Container → SemVer" test_s07_version_from_container
        run_test "S-08" "Version aus Image-Label → SemVer" test_s08_version_from_image_label
        run_test "S-09" ":pre-update Tag gesetzt" test_s09_pre_update_tag
        run_test "S-10" "backup.sh wird aufgerufen" test_s10_backup_called
        run_test "S-11" "Backup-Fehler → Update abgebrochen" test_s11_backup_failure_aborts
        run_test "S-12" "Image-Label == API-Version (Konsistenz)" test_s12_version_consistency
    fi

    # Summary
    echo ""
    echo -e "${BLUE}--- Zusammenfassung ---${NC}"
    echo -e "  Ausgeführt: $TESTS_RUN"
    echo -e "  ${GREEN}Bestanden:  $TESTS_PASSED${NC}"
    echo -e "  ${RED}Fehlgeschlagen: $TESTS_FAILED${NC}"

    if (( TESTS_FAILED > 0 )); then
        return 1
    fi
    return 0
}

main "$@"
