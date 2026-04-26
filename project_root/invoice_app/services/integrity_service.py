"""
GoBD Integrity Service — eRechnung

Prüft die kryptographische Integrität von Rechnungen und Audit-Log-Ketten.
Generiert Compliance-Reports für Betriebsprüfungen.

Referenz: GoBD (BMF-Schreiben vom 28.11.2019), Phase 2 + 5 des GoBD Implementation Plans.
"""

import logging

from django.utils import timezone


logger = logging.getLogger(__name__)


class IntegrityService:
    """Service für GoBD-konforme Integritätsprüfung."""

    @classmethod
    def verify_all_invoices(cls):
        """Prüft alle gesperrten Rechnungen auf Integrität.

        Returns:
            list[dict]: Liste von Integritätsverletzungen.
        """
        from invoice_app.models.invoice_models import Invoice

        violations = []
        locked_invoices = Invoice.objects.filter(is_locked=True, is_archived=False)

        for invoice in locked_invoices:
            is_valid, error = invoice.verify_integrity()
            if not is_valid:
                violations.append(
                    {
                        "invoice_number": invoice.invoice_number,
                        "invoice_id": invoice.pk,
                        "error": error,
                    }
                )

        return violations

    @classmethod
    def verify_audit_chain(cls, limit=5000):
        """Prüft die AuditLog-Hash-Kette.

        Returns:
            list[dict]: Liste von Kettenbrüchen.
        """
        from invoice_app.models.audit import AuditLog

        return AuditLog.verify_chain(limit=limit)

    @classmethod
    def generate_integrity_report(cls):
        """Erstellt umfassenden Integritätsbericht für Betriebsprüfungen.

        Returns:
            dict: Report mit Status, Zählern und ggf. Verletzungen.
        """
        from invoice_app.models.audit import AuditLog
        from invoice_app.models.invoice_models import Invoice

        report = {
            "generated_at": timezone.now().isoformat(),
            "status": "OK",
            # Invoice integrity
            "invoices_total": Invoice.objects.count(),
            "invoices_locked": Invoice.objects.filter(is_locked=True).count(),
            "invoices_archived": Invoice.objects.filter(is_archived=True).count(),
            "invoices_with_hash": Invoice.objects.filter(is_locked=True).exclude(content_hash="").count(),
            "invoice_violations": [],
            # Audit chain integrity
            "audit_log_total": AuditLog.objects.count(),
            "audit_log_with_hash": AuditLog.objects.exclude(entry_hash="").count(),
            "audit_chain_violations": [],
            # Retention
            "invoices_within_retention": Invoice.objects.filter(retention_until__gt=timezone.now().date()).count(),
        }

        # Check invoice integrity
        report["invoice_violations"] = cls.verify_all_invoices()

        # Check audit chain
        report["audit_chain_violations"] = cls.verify_audit_chain()

        # Set overall status
        if report["invoice_violations"] or report["audit_chain_violations"]:
            report["status"] = "VIOLATIONS_FOUND"
            logger.warning(
                "Integrity report: %d invoice violations, %d audit chain violations",
                len(report["invoice_violations"]),
                len(report["audit_chain_violations"]),
            )
        else:
            logger.info("Integrity report: OK — no violations found")

        return report

    @classmethod
    def get_retention_summary(cls):
        """Zusammenfassung der Aufbewahrungsfristen.

        Returns:
            dict: Retention-Statistiken.
        """
        from invoice_app.models.audit import AuditLog
        from invoice_app.models.invoice_models import Invoice

        today = timezone.now().date()
        now = timezone.now()

        return {
            "invoices_within_retention": Invoice.objects.filter(retention_until__gt=today).count(),
            "invoices_retention_expired": Invoice.objects.filter(retention_until__lte=today).count(),
            "invoices_no_retention": Invoice.objects.filter(retention_until__isnull=True).count(),
            "audit_logs_within_retention": AuditLog.objects.filter(retention_until__gt=now).count(),
            "audit_logs_retention_expired": AuditLog.objects.filter(retention_until__lte=now).count(),
        }
