#!/usr/bin/env bash
# validate_invoice_mustang.sh
# Validates a ZUGFeRD/Factur-X PDF (or XML) using Mustang-CLI.
#
# Usage:
#   ./scripts/validate_invoice_mustang.sh <invoice.pdf>
#   ./scripts/validate_invoice_mustang.sh <factur-x.xml>
#   ./scripts/validate_invoice_mustang.sh          # validates media/invoices/*.pdf (all)
#
# Requires: Java 11+ on the host (already available: OpenJDK 21)
# The Mustang-CLI JAR is downloaded automatically on first run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSTANG_VERSION="2.22.0"
MUSTANG_JAR="${SCRIPT_DIR}/Mustang-CLI-${MUSTANG_VERSION}.jar"
MUSTANG_URL="https://www.mustangproject.org/deploy/Mustang-CLI-${MUSTANG_VERSION}.jar"

# ── Download JAR if missing ───────────────────────────────────────────────────
if [[ ! -f "${MUSTANG_JAR}" ]]; then
    echo "Mustang-CLI ${MUSTANG_VERSION} not found – downloading..."
    curl -L --progress-bar -o "${MUSTANG_JAR}" "${MUSTANG_URL}"
    echo "Downloaded: ${MUSTANG_JAR}"
fi

# ── Collect files to validate ─────────────────────────────────────────────────
FILES=()
if [[ $# -ge 1 ]]; then
    FILES=("$@")
else
    # Default: all PDFs in the Django media directory (inside the project)
    MEDIA_DIR="${SCRIPT_DIR}/../project_root/media/invoices"
    if [[ -d "${MEDIA_DIR}" ]]; then
        mapfile -t FILES < <(find "${MEDIA_DIR}" -name "*.pdf" -type f | sort)
    fi
    if [[ ${#FILES[@]} -eq 0 ]]; then
        echo "Usage: $0 <invoice.pdf|factur-x.xml> [more files...]"
        echo "       or place PDFs in project_root/media/invoices/ and run without arguments."
        exit 1
    fi
fi

# ── Validate ──────────────────────────────────────────────────────────────────
PASS=0
FAIL=0

for FILE in "${FILES[@]}"; do
    if [[ ! -f "${FILE}" ]]; then
        echo "ERROR: File not found: ${FILE}"
        ((FAIL++))
        continue
    fi

    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo "Validating: ${FILE}"
    echo "══════════════════════════════════════════════════════════════════"

    # --no-notices suppresses XRechnung-specific notices (not relevant here)
    # Redirect stderr (log noise) to /dev/null; XML report goes to stdout
    if java -Xmx1G -Dfile.encoding=UTF-8 \
        -jar "${MUSTANG_JAR}" \
        --no-notices \
        --action validate \
        --source "${FILE}" \
        2>/dev/null; then
        ((PASS++))
    else
        ((FAIL++))
    fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Result: ${PASS} valid  |  ${FAIL} invalid  (${#FILES[@]} total)"
echo "══════════════════════════════════════════════════════════════════"

[[ ${FAIL} -eq 0 ]]   # exit 0 on all valid, exit 1 if any invalid
