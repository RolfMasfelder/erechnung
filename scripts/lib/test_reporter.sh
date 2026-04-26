#!/usr/bin/env bash
# =============================================================================
# Test-Reporter für Update-Tests
# =============================================================================
# Erzeugt JUnit XML und HTML Summary aus Test-Ergebnissen.
#
# Usage (aus anderen Skripten):
#   source scripts/lib/test_reporter.sh
#   reporter_init "Update-Tests"
#   reporter_add_result "M-01" "Schema-Vollständigkeit" "PASS" "2.3"
#   reporter_add_result "M-02" "Datenintegrität" "FAIL" "1.1" "Expected 5, got 3"
#   reporter_write_junit "test-artifacts/update-tests/junit.xml"
#   reporter_write_html  "test-artifacts/update-tests/report.html"
#
# Standalone:
#   ./scripts/lib/test_reporter.sh --from-log <logfile> --junit <out.xml> --html <out.html>
# =============================================================================

# --- State -------------------------------------------------------------------
_REPORTER_SUITE_NAME=""
_REPORTER_RESULTS=()    # "STATUS|ID|NAME|DURATION|MESSAGE"
_REPORTER_START_TIME=""

# --- API ---------------------------------------------------------------------

reporter_init() {
    _REPORTER_SUITE_NAME="${1:-Update-Tests}"
    _REPORTER_RESULTS=()
    _REPORTER_START_TIME=$(date +%s)
}

reporter_add_result() {
    local test_id="$1"
    local test_name="$2"
    local status="$3"           # PASS, FAIL, SKIP
    local duration="${4:-0}"     # secs
    local message="${5:-}"

    _REPORTER_RESULTS+=("${status}|${test_id}|${test_name}|${duration}|${message}")
}

# --- JUnit XML ---------------------------------------------------------------

reporter_write_junit() {
    local output_file="$1"
    mkdir -p "$(dirname "$output_file")"

    local total=0
    local failures=0
    local skipped=0
    local total_time=0

    for entry in "${_REPORTER_RESULTS[@]}"; do
        ((total++)) || true
        local status="${entry%%|*}"
        local duration
        duration=$(echo "$entry" | cut -d'|' -f4)
        total_time=$(echo "$total_time + $duration" | bc 2>/dev/null || echo "$total_time")
        case "$status" in
            FAIL) ((failures++)) || true ;;
            SKIP) ((skipped++)) || true ;;
        esac
    done

    cat > "$output_file" <<XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="${_REPORTER_SUITE_NAME}" tests="${total}" failures="${failures}" skipped="${skipped}" time="${total_time}" timestamp="$(date -Iseconds)">
XMLEOF

    for entry in "${_REPORTER_RESULTS[@]}"; do
        local status test_id test_name duration message
        IFS='|' read -r status test_id test_name duration message <<< "$entry"

        echo "    <testcase classname=\"${_REPORTER_SUITE_NAME}\" name=\"[${test_id}] ${test_name}\" time=\"${duration}\">" >> "$output_file"

        case "$status" in
            FAIL)
                local safe_message
                safe_message=$(echo "$message" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')
                echo "      <failure message=\"${safe_message}\">Test ${test_id} fehlgeschlagen</failure>" >> "$output_file"
                ;;
            SKIP)
                echo "      <skipped/>" >> "$output_file"
                ;;
        esac

        echo "    </testcase>" >> "$output_file"
    done

    cat >> "$output_file" <<XMLEOF
  </testsuite>
</testsuites>
XMLEOF
}

# --- HTML Report -------------------------------------------------------------

reporter_write_html() {
    local output_file="$1"
    mkdir -p "$(dirname "$output_file")"

    local total=0
    local passed=0
    local failures=0
    local skipped=0

    for entry in "${_REPORTER_RESULTS[@]}"; do
        ((total++)) || true
        local status="${entry%%|*}"
        case "$status" in
            PASS) ((passed++)) || true ;;
            FAIL) ((failures++)) || true ;;
            SKIP) ((skipped++)) || true ;;
        esac
    done

    local end_time
    end_time=$(date +%s)
    local total_duration=$(( end_time - ${_REPORTER_START_TIME:-$end_time} ))

    cat > "$output_file" <<HTMLEOF
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>eRechnung Update-Test Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #f5f5f5; color: #333; }
    h1 { color: #1a1a2e; border-bottom: 2px solid #16213e; padding-bottom: 0.5rem; }
    .summary { display: flex; gap: 1rem; margin: 1rem 0 2rem; }
    .summary .card { padding: 1rem 1.5rem; border-radius: 8px; color: white; font-size: 1.2rem; min-width: 120px; text-align: center; }
    .card.total { background: #16213e; }
    .card.pass { background: #2ecc71; }
    .card.fail { background: #e74c3c; }
    .card.skip { background: #f39c12; }
    .card .number { font-size: 2rem; font-weight: bold; display: block; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th { background: #16213e; color: white; padding: 0.75rem 1rem; text-align: left; }
    td { padding: 0.5rem 1rem; border-bottom: 1px solid #eee; }
    tr:hover { background: #f8f9fa; }
    .status-pass { color: #2ecc71; font-weight: bold; }
    .status-fail { color: #e74c3c; font-weight: bold; }
    .status-skip { color: #f39c12; font-weight: bold; }
    .footer { margin-top: 2rem; color: #888; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>eRechnung Update-Test Report</h1>
  <p>Suite: <strong>${_REPORTER_SUITE_NAME}</strong> | Datum: $(date '+%d.%m.%Y %H:%M:%S') | Dauer: ${total_duration}s</p>

  <div class="summary">
    <div class="card total"><span class="number">${total}</span>Gesamt</div>
    <div class="card pass"><span class="number">${passed}</span>Bestanden</div>
    <div class="card fail"><span class="number">${failures}</span>Fehlgeschlagen</div>
    <div class="card skip"><span class="number">${skipped}</span>Übersprungen</div>
  </div>

  <table>
    <thead>
      <tr><th>Test-ID</th><th>Beschreibung</th><th>Status</th><th>Dauer</th><th>Details</th></tr>
    </thead>
    <tbody>
HTMLEOF

    for entry in "${_REPORTER_RESULTS[@]}"; do
        local status test_id test_name duration message
        IFS='|' read -r status test_id test_name duration message <<< "$entry"

        local css_class="status-pass"
        case "$status" in
            FAIL) css_class="status-fail" ;;
            SKIP) css_class="status-skip" ;;
        esac

        local safe_message
        safe_message=$(echo "$message" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')

        cat >> "$output_file" <<ROWEOF
      <tr>
        <td><code>${test_id}</code></td>
        <td>${test_name}</td>
        <td class="${css_class}">${status}</td>
        <td>${duration}s</td>
        <td>${safe_message}</td>
      </tr>
ROWEOF
    done

    cat >> "$output_file" <<HTMLEOF
    </tbody>
  </table>
  <div class="footer">Generiert von eRechnung Test-Reporter | $(date -Iseconds)</div>
</body>
</html>
HTMLEOF
}

# --- Standalone mode: parse log output and generate reports ------------------

_parse_log_and_report() {
    local log_file=""
    local junit_file=""
    local html_file=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --from-log) log_file="$2"; shift 2 ;;
            --junit)    junit_file="$2"; shift 2 ;;
            --html)     html_file="$2"; shift 2 ;;
            *)          shift ;;
        esac
    done

    if [[ -z "$log_file" ]]; then
        echo "Usage: $0 --from-log <logfile> [--junit <out.xml>] [--html <out.html>]" >&2
        return 1
    fi

    reporter_init "Update-Tests"

    # Parse lines like: "  [M-01] Schema-Vollständigkeit ... PASS"
    while IFS= read -r line; do
        if [[ "$line" =~ \[([A-Z0-9_-]+)\]\ (.+)\ \.\.\.\ (PASS|FAIL|SKIP) ]]; then
            local test_id="${BASH_REMATCH[1]}"
            local test_name="${BASH_REMATCH[2]}"
            local status="${BASH_REMATCH[3]}"
            reporter_add_result "$test_id" "$test_name" "$status" "0"
        fi
    done < "$log_file"

    [[ -n "$junit_file" ]] && reporter_write_junit "$junit_file"
    [[ -n "$html_file" ]]  && reporter_write_html "$html_file"
}

# Only run standalone if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    _parse_log_and_report "$@"
fi
