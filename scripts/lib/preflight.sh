#!/usr/bin/env bash
# =============================================================================
# Pre-Flight-Check Library für Update-Skripte
# =============================================================================
# Verwendung:
#   source scripts/lib/preflight.sh
#   check_docker_running || exit 1
#
# Exit-Codes:
#   0 = OK
#   1 = Check fehlgeschlagen
# =============================================================================

set -euo pipefail

# Farben (nur wenn Terminal vorhanden)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' NC=''
fi

LOCK_FILE="/tmp/erechnung-update.lock"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
preflight_info()  { echo -e "${GREEN}[✓]${NC} $*"; }
preflight_warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
preflight_error() { echo -e "${RED}[✗]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Docker-Prüfungen
# ---------------------------------------------------------------------------

check_docker_running() {
    if ! docker info &>/dev/null; then
        preflight_error "Docker-Daemon ist nicht erreichbar."
        preflight_error "Bitte starten Sie Docker und versuchen Sie es erneut."
        return 1
    fi
    preflight_info "Docker-Daemon läuft."
}

check_disk_space() {
    local min_gb="${1:-2}"
    local available_gb
    available_gb=$(df -BG --output=avail / | tail -1 | tr -d ' G')
    if (( available_gb < min_gb )); then
        preflight_error "Nicht genügend Speicherplatz: ${available_gb} GB frei, mindestens ${min_gb} GB benötigt."
        return 1
    fi
    preflight_info "Speicherplatz OK: ${available_gb} GB frei (min. ${min_gb} GB)."
}

check_compose_file_exists() {
    local file="${1:-docker-compose.yml}"
    if [[ ! -f "$file" ]]; then
        preflight_error "Compose-Datei nicht gefunden: $file"
        return 1
    fi
    preflight_info "Compose-Datei vorhanden: $file"
}

check_current_version() {
    local compose_file="${1:-docker-compose.yml}"
    local service="${2:-web}"
    local version

    # Versuche Version über /api/version/ Endpoint
    version=$(curl -sf http://localhost:8000/api/version/ 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null) || true

    if [[ -z "$version" ]]; then
        # Fallback: Version aus laufendem Container lesen
        version=$(docker compose -f "$compose_file" exec -T "$service" python -c "
from importlib.metadata import version
try:
    print(version('erechnung'))
except Exception:
    print('unknown')
" 2>/dev/null) || version="unknown"
    fi

    if [[ "$version" == "unknown" ]]; then
        preflight_warn "Aktuelle Version konnte nicht ermittelt werden."
        return 1
    fi
    preflight_info "Aktuelle Version: $version"
    echo "$version"
}

check_target_version_exists() {
    local target_version="$1"
    local image="${2:-}"

    if [[ -z "$target_version" ]]; then
        preflight_error "Keine Zielversion angegeben."
        return 1
    fi

    if [[ -n "$image" ]]; then
        # Prüfe ob das Docker-Image mit dem Tag existiert
        if ! docker image inspect "${image}:${target_version}" &>/dev/null; then
            preflight_error "Image ${image}:${target_version} nicht gefunden."
            return 1
        fi
        preflight_info "Ziel-Image vorhanden: ${image}:${target_version}"
    else
        preflight_info "Zielversion: $target_version"
    fi
}

# ---------------------------------------------------------------------------
# Kubernetes-Prüfungen (K3s)
# ---------------------------------------------------------------------------

check_cluster_health() {
    if ! kubectl cluster-info &>/dev/null; then
        preflight_error "Kubernetes-Cluster ist nicht erreichbar."
        return 1
    fi
    preflight_info "Kubernetes-Cluster erreichbar."
}

check_nodes_ready() {
    local not_ready
    not_ready=$(kubectl get nodes --no-headers 2>/dev/null | grep -c "NotReady" || true)
    if (( not_ready > 0 )); then
        preflight_error "$not_ready Nodes sind nicht Ready."
        kubectl get nodes --no-headers 2>/dev/null | grep "NotReady" | while read -r line; do
            preflight_error "  $line"
        done
        return 1
    fi
    preflight_info "Alle Kubernetes-Nodes sind Ready."
}

# ---------------------------------------------------------------------------
# Update-Lock (verhindert parallele Updates)
# ---------------------------------------------------------------------------

acquire_update_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            preflight_error "Ein anderes Update läuft bereits (PID: $lock_pid)."
            return 1
        fi
        # Lock von beendetem Prozess — aufräumen
        preflight_warn "Veralteter Lock gefunden, wird entfernt."
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
    preflight_info "Update-Lock erworben (PID: $$)."
}

release_update_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE"
        preflight_info "Update-Lock freigegeben."
    fi
}

# ---------------------------------------------------------------------------
# Gesamtprüfung für Docker-Updates
# ---------------------------------------------------------------------------

run_docker_preflight() {
    local compose_file="${1:-docker-compose.yml}"
    local errors=0

    echo "=== Pre-Flight-Checks (Docker) ==="
    check_docker_running    || ((errors++))
    check_disk_space 2      || ((errors++))
    check_compose_file_exists "$compose_file" || ((errors++))

    if (( errors > 0 )); then
        preflight_error "$errors Pre-Flight-Check(s) fehlgeschlagen."
        return 1
    fi
    preflight_info "Alle Pre-Flight-Checks bestanden."
}

# ---------------------------------------------------------------------------
# Gesamtprüfung für K3s-Updates
# ---------------------------------------------------------------------------

run_k3s_preflight() {
    local errors=0

    echo "=== Pre-Flight-Checks (K3s) ==="
    check_disk_space 2     || ((errors++))
    check_cluster_health   || ((errors++))
    check_nodes_ready      || ((errors++))

    if (( errors > 0 )); then
        preflight_error "$errors Pre-Flight-Check(s) fehlgeschlagen."
        return 1
    fi
    preflight_info "Alle Pre-Flight-Checks bestanden."
}
