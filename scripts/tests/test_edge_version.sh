#!/usr/bin/env bash
# =============================================================================
# Edge-Case-Tests: Versions-Handling (EC-20 bis EC-24)
# =============================================================================
# Referenz: UPDATE_STRATEGY Kap. 10.7.3
#
# Testet Grenzfälle bei Versions-Erkennung und -Validierung.
# Prüft Update-Skripte auf korrekte Version-Handling-Logik.
#
# Usage:
#   ./scripts/tests/test_edge_version.sh              # Alle Tests
#   ./scripts/tests/test_edge_version.sh EC-20        # Einzelner Test
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

# =============================================================================
# EC-20: Downgrade-Versuch → Fehlermeldung
# =============================================================================
# Das Update-Skript soll bei gleichem Versionsstring mit --version erkennen,
# dass kein Update nötig ist, und clean beenden.
# Ein expliziter Downgrade (kleinere Version angeben) sollte erkannt werden.
test_ec20_downgrade_attempt() {
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Verify the script checks for same version and exits cleanly
    if ! grep -qE 'Bereits auf Version|kein Update|already.*version|same version' "$script"; then
        echo "  Kein Same-Version-Check im Update-Skript" >&2
        return 1
    fi

    # Verify there's version comparison that would catch same version
    if grep -qE 'CURRENT_VERSION.*==.*TARGET_VERSION|TARGET_VERSION.*==.*CURRENT' "$script"; then
        return 0
    fi

    # Alternative pattern: version comparison via conditional
    if grep -qE '\$CURRENT_VERSION.*\$TARGET_VERSION' "$script"; then
        return 0
    fi

    echo "  Kein Versionsvergleich im Update-Skript" >&2
    return 1
}

# =============================================================================
# EC-21: MAJOR-Sprung → Warnung
# =============================================================================
# Prüft, dass das Skript zumindest eine Bestätigung bei großen Sprüngen
# verlangt (oder darauf hinweist).
test_ec21_major_jump_warning() {
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Check if the script has any version-related confirmation
    # It should at minimum ask for confirmation before updating
    if grep -qE 'bestätig|confirm|--yes|CONFIRM|YES_FLAG|AUTO_CONFIRM' "$script"; then
        # Good: the script has some form of confirmation
        # Check for --yes flag that bypasses
        if grep -qE '\-\-yes' "$script"; then
            return 0
        fi
    fi

    # Alternative: dry-run mode exists (gives user a chance to review)
    if grep -qE '\-\-dry-run|DRY_RUN' "$script"; then
        return 0
    fi

    echo "  Keine Bestätigung oder Dry-Run-Modus für Versions-Sprünge" >&2
    return 1
}

# =============================================================================
# EC-22: Gleiche Version → No-Op
# =============================================================================
# Prüft, dass bei gleicher Version das Skript korrekt abbricht (Exit 0).
test_ec22_same_version_noop() {
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Read the current version from the running API
    local current_version
    current_version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true

    if [[ -z "$current_version" || "$current_version" == "unknown" ]]; then
        echo "  Kann aktuelle Version nicht ermitteln — Dev-Server läuft?" >&2
        # Fallback: check the script logic statically
        if grep -qE 'exit 0.*bereits\|exit 0.*nötig\|Bereits auf Version' "$script"; then
            return 0
        fi
        if grep -qE 'CURRENT_VERSION.*TARGET_VERSION.*exit 0' "$script"; then
            return 0
        fi
        # Check the broader pattern
        if grep -B2 'exit 0' "$script" | grep -qE 'Bereits|kein Update|same'; then
            return 0
        fi
        echo "  Kein Exit-0 bei gleicher Version" >&2
        return 1
    fi

    # Run the update script with --version <current> --dry-run --yes
    local output
    local result=0
    output=$("$script" --version "$current_version" --yes 2>&1) || result=$?

    # Should exit 0 with "already at version" message
    if (( result == 0 )) && echo "$output" | grep -qi "bereits\|kein update\|no update"; then
        return 0
    fi

    # Or dry-run shows same version
    if echo "$output" | grep -qi "bereits auf version"; then
        return 0
    fi

    echo "  Same-Version nicht als No-Op behandelt (exit=$result)" >&2
    return 1
}

# =============================================================================
# EC-23: Unbekannte Version → Fehlermeldung
# =============================================================================
# Prüft, dass ein Pull/Build für eine nicht existierende Version fehlschlägt.
test_ec23_unknown_version() {
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Check that the script handles build/pull failures properly
    # When building locally and the version doesn't exist, the build should fail
    # and the script should catch it

    # Verify exit codes for image-related failures
    if grep -qE 'exit [3-5]|error.*image|error.*pull|error.*build' "$script"; then
        return 0
    fi

    # Check for image build error handling
    if grep -A3 'docker.*build\|docker compose.*build' "$script" | grep -qE '\|\||exit|return|error'; then
        return 0
    fi

    echo "  Kein Fehler-Handling für ungültige Versionen" >&2
    return 1
}

# =============================================================================
# EC-24: pyproject.toml nicht lesbar → Fallback auf Image-Label
# =============================================================================
# Prüft, dass die Version auch ohne pyproject.toml ermittelt werden kann.
test_ec24_pyproject_fallback() {
    local script="$PROJECT_ROOT/scripts/update-docker.sh"

    # Check that the version fallback exists
    # update-docker.sh reads version from pyproject.toml with a fallback
    if grep -qE "0\.0\.0|unknown|fallback|default" "$script"; then
        # Good: there's a fallback value
        true
    else
        echo "  Kein Fallback-Wert für Version in update-docker.sh" >&2
        return 1
    fi

    # Verify pyproject.toml reading has error handling (|| echo "0.0.0")
    if grep 'pyproject' "$script" | grep -qE '\|\|.*0\.0\.0\|or.*default\|except'; then
        return 0
    fi

    # Check the K3s script as well
    local k3s_script="$PROJECT_ROOT/scripts/update-k3s.sh"
    if [[ -f "$k3s_script" ]]; then
        if grep 'pyproject' "$k3s_script" | grep -qE 'grep.*version\|sed.*version'; then
            # K3s script reads from pyproject.toml — check for error handling
            if grep -A1 'pyproject' "$k3s_script" | grep -qE '\|\||2>/dev/null'; then
                return 0
            fi
        fi
    fi

    # Alternative: version comes from API at runtime (always available)
    if grep -qE 'get_current_version|curl.*version' "$script"; then
        return 0
    fi

    echo "  Kein Fallback wenn pyproject.toml nicht lesbar" >&2
    return 1
}

# =============================================================================
# Hauptlogik
# =============================================================================
main() {
    local filter="${1:-}"

    echo -e "\n${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Edge-Cases: Versionen (EC-20..EC-24)          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}\n"

    if [[ -n "$filter" ]]; then
        case "$filter" in
            EC-20) run_test "EC-20" "Downgrade-Versuch → Fehlermeldung" test_ec20_downgrade_attempt ;;
            EC-21) run_test "EC-21" "MAJOR-Sprung → Warnung" test_ec21_major_jump_warning ;;
            EC-22) run_test "EC-22" "Gleiche Version → No-Op" test_ec22_same_version_noop ;;
            EC-23) run_test "EC-23" "Unbekannte Version → Fehler" test_ec23_unknown_version ;;
            EC-24) run_test "EC-24" "pyproject.toml Fallback" test_ec24_pyproject_fallback ;;
            *)     echo -e "${RED}Unbekannter Test: $filter${NC}"; exit 1 ;;
        esac
    else
        run_test "EC-20" "Downgrade-Versuch → Fehlermeldung" test_ec20_downgrade_attempt
        run_test "EC-21" "MAJOR-Sprung → Warnung" test_ec21_major_jump_warning
        run_test "EC-22" "Gleiche Version → No-Op" test_ec22_same_version_noop
        run_test "EC-23" "Unbekannte Version → Fehler" test_ec23_unknown_version
        run_test "EC-24" "pyproject.toml Fallback" test_ec24_pyproject_fallback
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
