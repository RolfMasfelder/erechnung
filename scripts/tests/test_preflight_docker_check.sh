#!/usr/bin/env bash
# Test: check_docker_running detects missing/unreachable Docker daemon.
#
# Strategy: We can't reliably stop the real Docker daemon during a test, so we
# put a "docker" shim earlier on PATH that simulates `docker info` failing
# (exit 1, simulating "Cannot connect to the Docker daemon").
#
# Run:
#   bash scripts/tests/test_preflight_docker_check.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PREFLIGHT_LIB="${REPO_ROOT}/scripts/lib/preflight.sh"

if [[ ! -f "${PREFLIGHT_LIB}" ]]; then
    echo "FAIL: preflight library not found at ${PREFLIGHT_LIB}" >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
PASS=0
FAIL=0

assert_eq() {
    local expected="$1" actual="$2" msg="$3"
    if [[ "${expected}" == "${actual}" ]]; then
        echo "PASS: ${msg}"
        PASS=$((PASS + 1))
    else
        echo "FAIL: ${msg}: expected '${expected}', got '${actual}'" >&2
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local needle="$1" haystack="$2" msg="$3"
    if [[ "${haystack}" == *"${needle}"* ]]; then
        echo "PASS: ${msg}"
        PASS=$((PASS + 1))
    else
        echo "FAIL: ${msg}: expected to contain '${needle}', got: ${haystack}" >&2
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Test 1: Docker daemon unreachable -> check_docker_running fails with message
# ---------------------------------------------------------------------------
TMPBIN="$(mktemp -d)"
trap 'rm -rf "${TMPBIN}"' EXIT

cat > "${TMPBIN}/docker" <<'EOF'
#!/usr/bin/env bash
# Stub: simulate "Cannot connect to the Docker daemon"
if [[ "$1" == "info" ]]; then
    echo "Cannot connect to the Docker daemon at unix:///var/run/docker.sock." >&2
    exit 1
fi
exit 1
EOF
chmod +x "${TMPBIN}/docker"

# Source the lib in a subshell so we can rebind PATH safely.
output=$( {
    PATH="${TMPBIN}:${PATH}"
    # shellcheck disable=SC1090
    source "${PREFLIGHT_LIB}"
    # preflight.sh enables 'set -e'; disable it so we can capture the
    # function's non-zero return code without aborting the subshell.
    set +e
    check_docker_running
    echo "EXIT=$?"
} 2>&1 )

exit_line="$(echo "${output}" | grep '^EXIT=' || true)"
exit_code="${exit_line#EXIT=}"

assert_eq "1" "${exit_code}" "check_docker_running returns 1 when docker daemon is unreachable"
assert_contains "Docker-Daemon ist nicht erreichbar" "${output}" "error message mentions unreachable Docker daemon"

# ---------------------------------------------------------------------------
# Test 2: docker binary missing entirely (FileNotFoundError equivalent)
# ---------------------------------------------------------------------------
EMPTY_TMPBIN="$(mktemp -d)"
trap 'rm -rf "${TMPBIN}" "${EMPTY_TMPBIN}"' EXIT

output2=$( {
    # Replace PATH so 'docker' cannot be resolved at all.
    PATH="${EMPTY_TMPBIN}"
    # shellcheck disable=SC1090
    source "${PREFLIGHT_LIB}"
    set +e
    check_docker_running
    echo "EXIT=$?"
} 2>&1 )

exit_line2="$(echo "${output2}" | grep '^EXIT=' || true)"
exit_code2="${exit_line2#EXIT=}"

assert_eq "1" "${exit_code2}" "check_docker_running returns 1 when docker binary is missing"
assert_contains "Docker-Daemon ist nicht erreichbar" "${output2}" "error message also covers missing docker binary"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "Tests passed: ${PASS}"
echo "Tests failed: ${FAIL}"
echo "=========================================="

if [[ "${FAIL}" -gt 0 ]]; then
    exit 1
fi
exit 0
