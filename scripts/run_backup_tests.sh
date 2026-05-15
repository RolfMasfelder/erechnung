#!/bin/bash
# Run backup/restore Django unit tests (invoice_app/tests/backup_restore_tests.py).
#
# Diese Tests laufen NICHT im normalen Testlauf (manage.py test invoice_app),
# weil sie den Testdatenbankzustand stören können. Stattdessen werden sie
# separat ausgeführt — automatisch bei Migrations-Änderungen oder manuell.
#
# Verwendung:
#   ./run_backup_tests.sh              # Nur ausführen wenn Migrations geändert
#   ./run_backup_tests.sh --always     # Immer ausführen
#   ./run_backup_tests.sh -v           # Verbose output (zeigt jeden Test)
#
# Migrations werden erkannt in:
#   - Uncommitted/staged changes (git diff HEAD)
#   - Letztem Commit (git diff HEAD~1 HEAD)
#   - invoice_app/management/commands/backup_database.py

set -e

ALWAYS_RUN=false
VERBOSITY=1

for arg in "$@"; do
    case $arg in
        --always) ALWAYS_RUN=true ;;
        -v)       VERBOSITY=2 ;;
    esac
done

# -----------------------------------------------------------------------
# Prüfen ob relevante Änderungen vorliegen
# -----------------------------------------------------------------------
migrations_changed() {
    # Uncommitted changes (staged + unstaged)
    if git diff --name-only HEAD 2>/dev/null | grep -q "invoice_app/migrations/\|backup_database.py"; then
        return 0
    fi
    # Letzter Commit
    if git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -q "invoice_app/migrations/\|backup_database.py"; then
        return 0
    fi
    return 1
}

if [ "$ALWAYS_RUN" = false ]; then
    if ! migrations_changed; then
        echo "Keine Migration- oder Backup-Command-Änderungen gefunden."
        echo "Backup-Tests übersprungen. Für manuelle Ausführung: $0 --always"
        exit 0
    fi
    echo "Migrations- oder Backup-Command-Änderungen erkannt — starte Backup-Tests..."
else
    echo "Backup-Tests werden ausgeführt (--always)..."
fi

# -----------------------------------------------------------------------
# Tests ausführen
# -----------------------------------------------------------------------
cd "$(dirname "$0")/.."

docker compose exec web python project_root/manage.py \
    test invoice_app.tests.backup_restore_tests \
    --noinput -v "$VERBOSITY"
