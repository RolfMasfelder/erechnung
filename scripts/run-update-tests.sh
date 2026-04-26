#!/usr/bin/env bash
# =============================================================================
# Update-Test-Orchestrierung für eRechnung
# =============================================================================
#
# Führt Update-Tests in einer isolierten Umgebung aus.
#
# Usage:
#   ./scripts/run-update-tests.sh --all
#   ./scripts/run-update-tests.sh --level 1
#   ./scripts/run-update-tests.sh --level 1 --docker-only
#   ./scripts/run-update-tests.sh --test S-01
#   ./scripts/run-update-tests.sh --edge-cases
#
# Exit-Codes:
#   0 = Alle Tests bestanden
#   1 = Mindestens ein Test fehlgeschlagen
#   2 = Infrastruktur-Fehler (Setup/Teardown)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/test-artifacts/update-tests/logs"
REPORT_DIR="$PROJECT_ROOT/test-artifacts/update-tests"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.update-test.yml"

# Source test reporter
# shellcheck source=lib/test_reporter.sh
source "$SCRIPT_DIR/lib/test_reporter.sh"

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

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
RUN_ALL=false
TEST_LEVEL=""
TEST_ID=""
DOCKER_ONLY=false
K3S_ONLY=false
VERBOSE=false
EDGE_CASES=false

# Zähler
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Optionen:
  --all           Alle Tests ausführen (Level 1-4)
  --level N       Nur Tests der Ebene N (1-5)
  --test ID       Einzelnen Test ausführen (z.B. S-01, M-01, D-01)
  --edge-cases    Edge-Case-Tests (EC-*, SV-*) — Level 5
  --docker-only   Nur Docker-bezogene Tests
  --k3s-only      Nur K3s-bezogene Tests
  --verbose       Ausführliche Ausgabe
  -h, --help      Diese Hilfe anzeigen

Ebenen:
  1  Skript-Unit-Tests (S-*)
  2  Migrations-Tests (M-*)
  3  Komponententests (D-*/K-*)
  4  End-to-End-Tests (E2E-*)
  5  Edge-Cases & Selbstvalidierung (EC-*/SV-*)

Exit-Codes:
  0  Alle Tests bestanden
  1  Tests fehlgeschlagen
  2  Infrastruktur-Fehler
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument-Parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)       RUN_ALL=true; shift ;;
        --level)     TEST_LEVEL="$2"; shift 2 ;;
        --test)      TEST_ID="$2"; shift 2 ;;
        --edge-cases) EDGE_CASES=true; shift ;;
        --docker-only) DOCKER_ONLY=true; shift ;;
        --k3s-only)  K3S_ONLY=true; shift ;;
        --verbose)   VERBOSE=true; shift ;;
        -h|--help)   usage ;;
        *)
            echo -e "${RED}Unbekannte Option: $1${NC}" >&2
            usage
            ;;
    esac
done

# Validierung
if [[ "$DOCKER_ONLY" == true && "$K3S_ONLY" == true ]]; then
    echo -e "${RED}--docker-only und --k3s-only können nicht gleichzeitig gesetzt werden.${NC}" >&2
    exit 2
fi

if [[ "$RUN_ALL" == false && "$EDGE_CASES" == false && -z "$TEST_LEVEL" && -z "$TEST_ID" ]]; then
    echo -e "${YELLOW}Kein Test ausgewählt. Verwende --all, --level N oder --test ID.${NC}" >&2
    usage
fi

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="$LOG_DIR/update-test-${TIMESTAMP}.log"

log() {
    local msg="[$(date '+%H:%M:%S')] $*"
    echo "$msg" >> "$LOG_FILE"
    if [[ "$VERBOSE" == true ]]; then
        echo -e "$msg"
    fi
}

# ---------------------------------------------------------------------------
# Test-Framework-Funktionen
# ---------------------------------------------------------------------------
run_test() {
    local test_id="$1"
    local test_name="$2"
    local test_func="$3"

    ((TESTS_RUN++))
    echo -ne "${BLUE}  [$test_id]${NC} $test_name ... "
    log "START: $test_id - $test_name"

    if $test_func >> "$LOG_FILE" 2>&1; then
        ((TESTS_PASSED++))
        echo -e "${GREEN}PASS${NC}"
        log "PASS: $test_id"
    else
        ((TESTS_FAILED++))
        echo -e "${RED}FAIL${NC}"
        log "FAIL: $test_id"
    fi
}

skip_test() {
    local test_id="$1"
    local test_name="$2"
    local reason="$3"

    ((TESTS_SKIPPED++)) || true
    echo -e "${YELLOW}  [$test_id]${NC} $test_name ... ${YELLOW}SKIP${NC} ($reason)"
    log "SKIP: $test_id - $reason"
}

# ---------------------------------------------------------------------------
# Test-Umgebung Setup/Teardown
# ---------------------------------------------------------------------------
setup_test_env() {
    log "Setting up test environment..."
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker compose -f "$COMPOSE_FILE" up -d db-update-test redis-update-test 2>> "$LOG_FILE" || {
            echo -e "${RED}Fehler beim Starten der Testumgebung.${NC}" >&2
            return 1
        }
        log "Test environment started."
    fi
}

teardown_test_env() {
    log "Tearing down test environment..."
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker compose -f "$COMPOSE_FILE" down -v 2>> "$LOG_FILE" || true
    fi
    log "Test environment stopped."
}

# ---------------------------------------------------------------------------
# Ebene 1: Skript-Unit-Tests (Docker: S-01..S-11, K3s: S-05,S-06,S-12)
# ---------------------------------------------------------------------------
run_level_1() {
    echo -e "\n${BLUE}=== Ebene 1: Skript-Unit-Tests ===${NC}"

    # Docker-Skript-Tests (S-01..S-11)
    if [[ "$K3S_ONLY" != true ]]; then
        local docker_test_script="$SCRIPT_DIR/tests/test_update_docker.sh"
        if [[ -x "$docker_test_script" ]]; then
            log "Level 1: Running Docker script unit tests..."
            if "$docker_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 1: All Docker script tests passed."
            else
                log "Level 1: Some Docker script tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $docker_test_script${NC}" >&2
            log "Level 1: test_update_docker.sh not found"
        fi
    else
        skip_test "S-01..S-11" "Docker-Skript-Tests" "K3s-only Modus"
    fi

    # K3s-Skript-Tests (S-05, S-06, S-12)
    if [[ "$DOCKER_ONLY" != true ]]; then
        local k3s_test_script="$SCRIPT_DIR/tests/test_update_k3s.sh"
        if [[ -x "$k3s_test_script" ]]; then
            log "Level 1: Running K3s script unit tests..."
            if "$k3s_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 1: All K3s script tests passed."
            else
                log "Level 1: Some K3s script tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $k3s_test_script${NC}" >&2
            log "Level 1: test_update_k3s.sh not found"
        fi
    else
        skip_test "S-05,S-06,S-12" "K3s-Skript-Tests" "Docker-only Modus"
    fi
}

# ---------------------------------------------------------------------------
# Ebene 2: Migrations-Tests (M-01 bis M-23)
# ---------------------------------------------------------------------------
run_level_2() {
    echo -e "\n${BLUE}=== Ebene 2: Migrations-Tests ===${NC}"

    local test_script="$SCRIPT_DIR/tests/test_migrations.sh"
    if [[ ! -x "$test_script" ]]; then
        echo -e "  ${RED}Test-Skript nicht gefunden: $test_script${NC}" >&2
        log "Level 2: test_migrations.sh not found"
        return 1
    fi

    log "Level 2: Running migration tests..."
    if "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        log "Level 2: All migration tests passed."
    else
        log "Level 2: Some migration tests failed."
        ((TESTS_FAILED++))
    fi
}

# ---------------------------------------------------------------------------
# Ebene 3: Docker-Komponententests (D-01 bis D-08)
# ---------------------------------------------------------------------------
run_level_3() {
    echo -e "\n${BLUE}=== Ebene 3: Komponententests ===${NC}"

    # Docker-Komponententests (D-01..D-08)
    if [[ "$K3S_ONLY" != true ]]; then
        local docker_test_script="$SCRIPT_DIR/tests/test_docker_components.sh"
        if [[ -x "$docker_test_script" ]]; then
            log "Level 3: Running Docker component tests..."
            if "$docker_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 3: All Docker component tests passed."
            else
                log "Level 3: Some Docker component tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $docker_test_script${NC}" >&2
            log "Level 3: test_docker_components.sh not found"
        fi
    else
        skip_test "D-*" "Docker-Komponententests" "K3s-only Modus"
    fi

    # K3s-Komponententests (K-01..K-08)
    if [[ "$DOCKER_ONLY" != true ]]; then
        local k3s_test_script="$SCRIPT_DIR/tests/test_k3s_components.sh"
        if [[ -x "$k3s_test_script" ]]; then
            log "Level 3: Running K3s component tests..."
            if "$k3s_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 3: All K3s component tests passed."
            else
                log "Level 3: Some K3s component tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $k3s_test_script${NC}" >&2
            log "Level 3: test_k3s_components.sh not found"
        fi
    else
        skip_test "K-*" "K3s-Komponententests" "Docker-only Modus"
    fi
}

# ---------------------------------------------------------------------------
# Ebene 4: Docker E2E-Tests (E2E-D-01 bis E2E-D-05)
# ---------------------------------------------------------------------------
run_level_4() {
    echo -e "\n${BLUE}=== Ebene 4: End-to-End-Tests ===${NC}"

    # Docker-E2E-Tests (E2E-D-01..E2E-D-05)
    if [[ "$K3S_ONLY" != true ]]; then
        local docker_test_script="$SCRIPT_DIR/tests/test_docker_e2e.sh"
        if [[ -x "$docker_test_script" ]]; then
            log "Level 4: Running Docker E2E tests..."
            if "$docker_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 4: All Docker E2E tests passed."
            else
                log "Level 4: Some Docker E2E tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $docker_test_script${NC}" >&2
            log "Level 4: test_docker_e2e.sh not found"
        fi
    else
        skip_test "E2E-D-*" "Docker-E2E-Tests" "K3s-only Modus"
    fi

    # K3s-E2E-Tests (E2E-K-01..E2E-K-05)
    if [[ "$DOCKER_ONLY" != true ]]; then
        local k3s_test_script="$SCRIPT_DIR/tests/test_k3s_e2e.sh"
        if [[ -x "$k3s_test_script" ]]; then
            log "Level 4: Running K3s E2E tests..."
            if "$k3s_test_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 4: All K3s E2E tests passed."
            else
                log "Level 4: Some K3s E2E tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $k3s_test_script${NC}" >&2
            log "Level 4: test_k3s_e2e.sh not found"
        fi
    else
        skip_test "E2E-K-*" "K3s-E2E-Tests" "Docker-only Modus"
    fi
}

# ---------------------------------------------------------------------------
# Ebene 5: Edge-Cases & Selbstvalidierung (EC-*, SV-*)
# ---------------------------------------------------------------------------
run_level_5() {
    echo -e "\n${BLUE}=== Ebene 5: Edge-Cases & Selbstvalidierung ===${NC}"

    # Infrastruktur-Edge-Cases (EC-01..EC-07)
    if [[ "$K3S_ONLY" != true ]]; then
        local infra_script="$SCRIPT_DIR/tests/test_edge_infra.sh"
        if [[ -x "$infra_script" ]]; then
            log "Level 5: Running infrastructure edge-case tests..."
            if "$infra_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 5: Infrastructure edge-case tests passed."
            else
                log "Level 5: Some infrastructure edge-case tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $infra_script${NC}" >&2
            log "Level 5: test_edge_infra.sh not found"
        fi
    fi

    # Daten-Edge-Cases (EC-10..EC-16)
    if [[ "$K3S_ONLY" != true ]]; then
        local data_script="$SCRIPT_DIR/tests/test_edge_data.sh"
        if [[ -x "$data_script" ]]; then
            log "Level 5: Running data edge-case tests..."
            if "$data_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 5: Data edge-case tests passed."
            else
                log "Level 5: Some data edge-case tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $data_script${NC}" >&2
            log "Level 5: test_edge_data.sh not found"
        fi
    fi

    # Versions-Edge-Cases (EC-20..EC-24)
    local version_script="$SCRIPT_DIR/tests/test_edge_version.sh"
    if [[ -x "$version_script" ]]; then
        log "Level 5: Running version edge-case tests..."
        if "$version_script" 2>&1 | tee -a "$LOG_FILE"; then
            log "Level 5: Version edge-case tests passed."
        else
            log "Level 5: Some version edge-case tests failed."
            ((TESTS_FAILED++))
        fi
    else
        echo -e "  ${RED}Test-Skript nicht gefunden: $version_script${NC}" >&2
        log "Level 5: test_edge_version.sh not found"
    fi

    # Testsuite-Selbstvalidierung (SV-01..SV-04)
    if [[ "$K3S_ONLY" != true ]]; then
        local self_script="$SCRIPT_DIR/tests/test_self_validation.sh"
        if [[ -x "$self_script" ]]; then
            log "Level 5: Running self-validation tests..."
            if "$self_script" 2>&1 | tee -a "$LOG_FILE"; then
                log "Level 5: Self-validation tests passed."
            else
                log "Level 5: Some self-validation tests failed."
                ((TESTS_FAILED++))
            fi
        else
            echo -e "  ${RED}Test-Skript nicht gefunden: $self_script${NC}" >&2
            log "Level 5: test_self_validation.sh not found"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Hauptlogik
# ---------------------------------------------------------------------------
main() {
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     eRechnung Update-Test-Suite          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Log: $LOG_FILE"
    log "=== Update-Test-Suite gestartet ==="
    log "Optionen: all=$RUN_ALL level=$TEST_LEVEL test=$TEST_ID edge=$EDGE_CASES docker_only=$DOCKER_ONLY k3s_only=$K3S_ONLY"

    # Einzeltest
    if [[ -n "$TEST_ID" ]]; then
        echo -e "\n${YELLOW}Einzeltest-Modus ist noch nicht implementiert (Test: $TEST_ID)${NC}"
        log "Single test mode not yet implemented: $TEST_ID"
        exit 0
    fi

    # Level oder alle
    if [[ "$RUN_ALL" == true || "$TEST_LEVEL" == "1" ]]; then
        run_level_1
    fi
    if [[ "$RUN_ALL" == true || "$TEST_LEVEL" == "2" ]]; then
        run_level_2
    fi
    if [[ "$RUN_ALL" == true || "$TEST_LEVEL" == "3" ]]; then
        run_level_3
    fi
    if [[ "$RUN_ALL" == true || "$TEST_LEVEL" == "4" ]]; then
        run_level_4
    fi
    if [[ "$RUN_ALL" == true || "$EDGE_CASES" == true || "$TEST_LEVEL" == "5" ]]; then
        run_level_5
    fi

    # Report generieren aus Log
    if [[ -f "$LOG_FILE" ]]; then
        log "Generating reports..."
        "$SCRIPT_DIR/lib/test_reporter.sh" \
            --from-log "$LOG_FILE" \
            --junit "$REPORT_DIR/junit.xml" \
            --html "$REPORT_DIR/report.html" 2>/dev/null || true
        if [[ -f "$REPORT_DIR/junit.xml" ]]; then
            echo -e "  JUnit:  $REPORT_DIR/junit.xml"
        fi
        if [[ -f "$REPORT_DIR/report.html" ]]; then
            echo -e "  HTML:   $REPORT_DIR/report.html"
        fi
    fi

    # Zusammenfassung — aggregate from sub-script output in Log
    # Sub-scripts print "  Ausgeführt: N" and "  Fehlgeschlagen: N"
    if [[ -f "$LOG_FILE" ]]; then
        TESTS_RUN=$(grep -oP '(?:Ausgeführt|Gesamt):\s+\K[0-9]+' "$LOG_FILE" 2>/dev/null | awk '{s+=$1} END {print s+0}' || echo "0")
        TESTS_PASSED=$(grep -oP 'Bestanden:\s+\K[0-9]+' "$LOG_FILE" 2>/dev/null | awk '{s+=$1} END {print s+0}' || echo "0")
        TESTS_FAILED=$(grep -oP 'Fehlgeschlagen:\s+\K[0-9]+' "$LOG_FILE" 2>/dev/null | awk '{s+=$1} END {print s+0}' || echo "0")
    fi
    echo ""
    echo -e "${BLUE}=== Zusammenfassung ===${NC}"
    echo -e "  Ausgeführt:  $TESTS_RUN"
    echo -e "  ${GREEN}Bestanden:   $TESTS_PASSED${NC}"
    echo -e "  ${RED}Fehlgeschlagen: $TESTS_FAILED${NC}"
    echo -e "  ${YELLOW}Übersprungen:  $TESTS_SKIPPED${NC}"
    echo ""
    log "=== Summary: run=$TESTS_RUN passed=$TESTS_PASSED failed=$TESTS_FAILED skipped=$TESTS_SKIPPED ==="

    if (( TESTS_FAILED > 0 )); then
        echo -e "${RED}Update-Tests FEHLGESCHLAGEN.${NC}"
        exit 1
    fi

    echo -e "${GREEN}Update-Tests bestanden.${NC}"
    exit 0
}

main
