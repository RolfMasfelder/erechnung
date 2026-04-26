"""
GoBD Compliance Audit — Management Command

Führt eine vollständige Integritätsprüfung aller Rechnungen und
Audit-Log-Einträge durch und gibt einen Bericht aus.

Nutzung:
    python manage.py gobd_audit
    python manage.py gobd_audit --json
    python manage.py gobd_audit --retention

Exit-Codes:
    0 = Alle Prüfungen bestanden
    1 = Integritätsverletzungen gefunden
"""

import json
import sys

from django.core.management.base import BaseCommand

from invoice_app.models.audit import AuditLog
from invoice_app.services.integrity_service import IntegrityService


class Command(BaseCommand):
    help = "GoBD-Integritätsprüfung: Prüft Rechnungs-Hashes und Audit-Log-Kette"

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Ausgabe als JSON (für automatisierte Auswertung)",
        )
        parser.add_argument(
            "--retention",
            action="store_true",
            help="Zusätzlich Aufbewahrungsfristen-Übersicht anzeigen",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5000,
            help="Maximale Anzahl geprüfter Audit-Log-Einträge (Default: 5000)",
        )

    def handle(self, *args, **options):
        output_json = options["json"]
        show_retention = options["retention"]

        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write(self.style.HTTP_INFO("  GoBD Compliance Audit"))
        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write("")

        # Generate report
        report = IntegrityService.generate_integrity_report()

        if output_json:
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            self._print_report(report)

        if show_retention:
            retention = IntegrityService.get_retention_summary()
            if output_json:
                self.stdout.write(json.dumps(retention, indent=2, ensure_ascii=False))
            else:
                self._print_retention(retention)

        # Log the audit run itself
        AuditLog.log_action(
            action=AuditLog.ActionType.SECURITY_EVENT,
            description="GoBD-Audit via Management Command durchgeführt",
            details={"status": report["status"]},
            severity=AuditLog.Severity.MEDIUM,
        )

        # Exit code based on results
        if report["status"] != "OK":
            self.stderr.write(self.style.ERROR("\n⚠ VIOLATIONS FOUND — Exit Code 1"))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Alle Prüfungen bestanden"))

    def _print_report(self, report):
        self.stdout.write(self.style.MIGRATE_HEADING("Rechnungen:"))
        self.stdout.write(f"  Gesamt:        {report['invoices_total']}")
        self.stdout.write(f"  Gesperrt:      {report['invoices_locked']}")
        self.stdout.write(f"  Mit Hash:      {report['invoices_with_hash']}")
        self.stdout.write(f"  Archiviert:    {report['invoices_archived']}")
        self.stdout.write("")

        if report["invoice_violations"]:
            self.stdout.write(self.style.ERROR(f"  ✗ {len(report['invoice_violations'])} Verletzung(en):"))
            for v in report["invoice_violations"]:
                self.stdout.write(self.style.ERROR(f"    - {v['invoice_number']}: {v['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ Keine Integritätsverletzungen"))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Audit-Log:"))
        self.stdout.write(f"  Gesamt:        {report['audit_log_total']}")
        self.stdout.write(f"  Mit Hash:      {report['audit_log_with_hash']}")
        self.stdout.write("")

        if report["audit_chain_violations"]:
            self.stdout.write(self.style.ERROR(f"  ✗ {len(report['audit_chain_violations'])} Kettenbruch/-brüche:"))
            for v in report["audit_chain_violations"]:
                self.stdout.write(self.style.ERROR(f"    - Event {v['event_id']} ({v['timestamp']})"))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ Audit-Log-Kette intakt"))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Status: {report['status']}"))

    def _print_retention(self, retention):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Aufbewahrungsfristen:"))
        self.stdout.write(f"  Rechnungen innerhalb Frist:    {retention['invoices_within_retention']}")
        self.stdout.write(f"  Rechnungen Frist abgelaufen:   {retention['invoices_retention_expired']}")
        self.stdout.write(f"  Rechnungen ohne Frist:         {retention['invoices_no_retention']}")
        self.stdout.write(f"  Audit-Logs innerhalb Frist:    {retention['audit_logs_within_retention']}")
        self.stdout.write(f"  Audit-Logs Frist abgelaufen:   {retention['audit_logs_retention_expired']}")
