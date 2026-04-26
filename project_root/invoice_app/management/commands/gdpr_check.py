"""
DSGVO / GDPR Management Command

Prüft offene Betroffenenanfragen, zeigt Fristen an,
und gibt eine Übersicht der Datenklassifizierung.

Nutzung:
    python manage.py gdpr_check
    python manage.py gdpr_check --deadlines
    python manage.py gdpr_check --classification
    python manage.py gdpr_check --json
"""

import json
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone

from invoice_app.models.gdpr import (
    DATA_CLASSIFICATION_REGISTRY,
    DataSubjectRequest,
    ProcessingActivity,
    get_unclassified_fields,
)
from invoice_app.services.gdpr_service import GDPRService


class Command(BaseCommand):
    help = "DSGVO-Prüfung: Fristen, Datenklassifizierung, Verarbeitungsverzeichnis"

    def add_arguments(self, parser):
        parser.add_argument(
            "--deadlines",
            action="store_true",
            help="Zeige nur offene/überfällige Betroffenenanfragen",
        )
        parser.add_argument(
            "--classification",
            action="store_true",
            help="Zeige Datenklassifizierungs-Übersicht",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Ausgabe im JSON-Format",
        )

    def handle(self, *args, **options):
        if options["deadlines"]:
            return self._check_deadlines(options)
        if options["classification"]:
            return self._check_classification(options)
        return self._full_report(options)

    def _full_report(self, options):
        """Complete GDPR status report."""
        report = {
            "timestamp": timezone.now().isoformat(),
            "dsr_summary": self._get_dsr_summary(),
            "processing_activities": ProcessingActivity.objects.filter(is_active=True).count(),
            "unclassified_fields": get_unclassified_fields(),
        }

        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            return

        self.stdout.write(self.style.SUCCESS("\n═══ DSGVO-Statusbericht ═══\n"))

        summary = report["dsr_summary"]
        self.stdout.write(f"  Offene Anfragen:      {summary['open']}")
        self.stdout.write(f"  Überfällig:           {summary['overdue']}")
        self.stdout.write(f"  Abgeschlossen:        {summary['completed']}")
        self.stdout.write(f"  Verarbeitungstätig.:  {report['processing_activities']}")

        unclassified = report["unclassified_fields"]
        if unclassified:
            self.stdout.write(self.style.WARNING(f"\n  ⚠ {len(unclassified)} Felder ohne Klassifizierung:"))
            for field in unclassified:
                self.stdout.write(f"    - {field}")
        else:
            self.stdout.write(self.style.SUCCESS("\n  ✓ Alle PII-Felder klassifiziert"))

        if summary["overdue"] > 0:
            self.stdout.write(self.style.ERROR(f"\n  ✗ {summary['overdue']} überfällige Anfragen!"))
            sys.exit(1)

    def _check_deadlines(self, options):
        """Show DSR deadlines."""
        overdue = GDPRService.get_overdue_requests()
        upcoming = GDPRService.get_upcoming_deadlines(days=7)

        if options["json"]:
            data = {
                "overdue": list(overdue.values("id", "subject_name", "request_type", "deadline")),
                "upcoming": list(upcoming.values("id", "subject_name", "request_type", "deadline")),
            }
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            return

        self.stdout.write(self.style.SUCCESS("\n═══ DSGVO-Fristen ═══\n"))

        if overdue.exists():
            self.stdout.write(self.style.ERROR("Überfällig:"))
            for dsr in overdue:
                self.stdout.write(f"  ✗ {dsr.subject_name} ({dsr.get_request_type_display()}) — Frist: {dsr.deadline}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ Keine überfälligen Anfragen"))

        if upcoming.exists():
            self.stdout.write(self.style.WARNING("\nBald fällig (7 Tage):"))
            for dsr in upcoming:
                self.stdout.write(
                    f"  ⚠ {dsr.subject_name} ({dsr.get_request_type_display()}) — Frist: {dsr.deadline}"
                    f" ({dsr.days_remaining} Tage)"
                )

    def _check_classification(self, options):
        """Show data classification overview."""
        if options["json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "classifications": DATA_CLASSIFICATION_REGISTRY,
                        "unclassified": get_unclassified_fields(),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("\n═══ Datenklassifizierung ═══\n"))
        current_model = None
        for key, classification in sorted(DATA_CLASSIFICATION_REGISTRY.items()):
            model, field = key.split(".")
            if model != current_model:
                current_model = model
                self.stdout.write(f"\n  {model}:")
            self.stdout.write(f"    {field:30s} → {classification}")

        unclassified = get_unclassified_fields()
        if unclassified:
            self.stdout.write(self.style.WARNING("\n  ⚠ Nicht klassifiziert:"))
            for field in unclassified:
                self.stdout.write(f"    - {field}")

    def _get_dsr_summary(self):
        """Get DSR statistics."""
        qs = DataSubjectRequest.objects
        open_statuses = [
            DataSubjectRequest.RequestStatus.RECEIVED,
            DataSubjectRequest.RequestStatus.IN_PROGRESS,
        ]
        open_count = qs.filter(status__in=open_statuses).count()
        overdue_count = qs.filter(status__in=open_statuses, deadline__lt=timezone.now().date()).count()
        completed_count = qs.filter(status=DataSubjectRequest.RequestStatus.COMPLETED).count()
        return {"open": open_count, "overdue": overdue_count, "completed": completed_count}
