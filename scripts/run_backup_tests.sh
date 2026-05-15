#!/bin/bash
# Run backup/restore integration tests (project_root/integration_tests/backup_restore_tests.py).
#
# Diese Tests liegen in integration_tests/ (nicht in invoice_app/tests/) und
# testen die Funktionalität des backup_database-Management-Commands als Ganzes.
# Sie laufen immer — unabhängig davon ob Migrations geändert wurden.
#
# Verwendung:
#   ./run_backup_tests.sh        # Tests ausführen
#   ./run_backup_tests.sh -v     # Verbose output (zeigt jeden Test)

set -e

VERBOSITY=1

for arg in "$@"; do
    case $arg in
        -v) VERBOSITY=2 ;;
    esac
done

# -----------------------------------------------------------------------
# Tests ausführen
# -----------------------------------------------------------------------
cd "$(dirname "$0")/.."

echo "Backup/Restore-Integrationstests werden ausgeführt..."

docker compose exec web python project_root/manage.py \
    test integration_tests.backup_restore_tests \
    --noinput -v "$VERBOSITY"
