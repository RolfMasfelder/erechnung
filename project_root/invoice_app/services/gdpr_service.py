"""
GDPR/DSGVO Service — Data Subject Request processing,
anonymization (GoBD-compliant), and data export.
"""

import json
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from invoice_app.models.audit import AuditLog
from invoice_app.models.business_partner import BusinessPartner
from invoice_app.models.gdpr import DataSubjectRequest
from invoice_app.models.user import UserProfile


User = get_user_model()
logger = logging.getLogger(__name__)


class GDPRService:
    """Handles GDPR data subject requests and anonymization."""

    # PII fields per model that can be collected/anonymized
    PARTNER_PII_FIELDS = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "fax",
        "contact_person",
        "accounting_contact",
        "accounting_email",
        "address_line1",
        "address_line2",
        "tax_id",
        "vat_id",
    ]

    USER_PII_FIELDS = [
        "username",
        "email",
        "first_name",
        "last_name",
    ]

    PROFILE_PII_FIELDS = [
        "employee_id",
        "phone",
        "mobile",
        "last_login_ip",
    ]

    # ── Data Access (Art. 15) ──────────────────────────────────────────

    @classmethod
    def collect_subject_data(cls, dsr):
        """Collect all personal data for a data subject (Art. 15 Auskunft)."""
        data = {"request_id": str(dsr.id), "subject_name": dsr.subject_name, "subject_email": dsr.subject_email}

        if dsr.subject_type == "partner":
            data["business_partner"] = cls._collect_partner_data(dsr)
        elif dsr.subject_type == "user":
            data["user_account"] = cls._collect_user_data(dsr)

        data["audit_entries"] = cls._collect_audit_data(dsr)
        return data

    @classmethod
    def _collect_partner_data(cls, dsr):
        """Collect BusinessPartner data matching the DSR."""
        partners = BusinessPartner.objects.filter(email__iexact=dsr.subject_email)
        result = []
        for bp in partners:
            entry = {}
            for field in cls.PARTNER_PII_FIELDS:
                entry[field] = getattr(bp, field, "")
            entry["company_name"] = bp.company_name
            entry["partner_number"] = bp.partner_number
            entry["created_at"] = bp.created_at.isoformat() if bp.created_at else None
            result.append(entry)
        return result

    @classmethod
    def _collect_user_data(cls, dsr):
        """Collect User + UserProfile data matching the DSR."""
        users = User.objects.filter(email__iexact=dsr.subject_email)
        result = []
        for user in users:
            entry = {f: getattr(user, f, "") for f in cls.USER_PII_FIELDS}
            entry["date_joined"] = user.date_joined.isoformat()
            entry["last_login"] = user.last_login.isoformat() if user.last_login else None

            try:
                profile = user.profile
                for field in cls.PROFILE_PII_FIELDS:
                    entry[f"profile_{field}"] = getattr(profile, field, "")
            except UserProfile.DoesNotExist:
                pass
            result.append(entry)
        return result

    @classmethod
    def _collect_audit_data(cls, dsr):
        """Collect audit log entries for the data subject."""
        audit_qs = AuditLog.objects.filter(
            username__iexact=dsr.subject_email,
        ).values("timestamp", "action", "object_type", "ip_address")
        entries = audit_qs[:100]
        return [
            {
                "timestamp": e["timestamp"].isoformat(),
                "action": e["action"],
                "object_type": e["object_type"],
                "ip_address": e["ip_address"],
            }
            for e in entries
        ]

    # ── Anonymization (Art. 17 — GoBD-compliant) ──────────────────────

    @classmethod
    @transaction.atomic
    def anonymize_partner(cls, partner_id, performed_by=None):
        """
        Anonymize a BusinessPartner's PII while preserving the record.

        GoBD requires 10-year retention of invoice-related data.
        Instead of deletion we replace PII with anonymized placeholders.
        """
        bp = BusinessPartner.objects.select_for_update().get(pk=partner_id)
        anonymized_label = f"Anonymisiert #{bp.pk}"

        bp.first_name = anonymized_label
        bp.last_name = ""
        bp.email = ""
        bp.phone = ""
        bp.fax = ""
        bp.contact_person = ""
        bp.accounting_contact = ""
        bp.accounting_email = ""
        bp.address_line1 = anonymized_label
        bp.address_line2 = ""
        bp.is_active = False
        bp.save()

        logger.info(
            "GDPR anonymization: BusinessPartner %s anonymized by %s",
            partner_id,
            performed_by,
        )
        return bp

    @classmethod
    @transaction.atomic
    def anonymize_user(cls, user_id, performed_by=None):
        """
        Anonymize a User account while preserving audit trail.

        The user account is deactivated and PII replaced.
        AuditLog entries are preserved for GoBD compliance.
        """
        user = User.objects.select_for_update().get(pk=user_id)
        anonymized = f"anon_{user.pk}"

        user.username = anonymized
        user.email = ""
        user.first_name = "Anonymisiert"
        user.last_name = ""
        user.is_active = False
        user.set_unusable_password()
        user.save()

        try:
            profile = user.profile
            profile.phone = ""
            profile.mobile = ""
            profile.employee_id = ""
            profile.last_login_ip = ""
            profile.mfa_secret = ""
            profile.backup_codes = ""
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        logger.info(
            "GDPR anonymization: User %s anonymized by %s",
            user_id,
            performed_by,
        )
        return user

    # ── DSR Processing ─────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def process_dsr(cls, dsr_id, performed_by=None):
        """Process a Data Subject Request based on its type."""
        dsr = DataSubjectRequest.objects.select_for_update().get(pk=dsr_id)
        dsr.status = DataSubjectRequest.RequestStatus.IN_PROGRESS
        dsr.processed_by = performed_by
        dsr.save()

        try:
            if dsr.request_type == DataSubjectRequest.RequestType.ACCESS:
                result = cls.collect_subject_data(dsr)
                dsr.result_data = result

            elif dsr.request_type == DataSubjectRequest.RequestType.ERASURE:
                result = cls._process_erasure(dsr, performed_by)
                dsr.result_data = result

            elif dsr.request_type == DataSubjectRequest.RequestType.PORTABILITY:
                result = cls.collect_subject_data(dsr)
                dsr.result_data = result

            elif dsr.request_type == DataSubjectRequest.RequestType.RECTIFICATION:
                dsr.result_data = {"note": "Berichtigung muss manuell durch den Sachbearbeiter erfolgen."}

            elif dsr.request_type == DataSubjectRequest.RequestType.RESTRICTION:
                result = cls._process_restriction(dsr)
                dsr.result_data = result

            elif dsr.request_type == DataSubjectRequest.RequestType.OBJECTION:
                dsr.result_data = {"note": "Widerspruch erfasst. Prüfung der Rechtsgrundlage erforderlich."}

            dsr.status = DataSubjectRequest.RequestStatus.COMPLETED
            dsr.completed_at = timezone.now()

        except Exception:
            dsr.status = DataSubjectRequest.RequestStatus.ESCALATED
            dsr.internal_notes += f"\nFehler bei Verarbeitung: {timezone.now().isoformat()}"
            logger.exception("Error processing DSR %s", dsr_id)

        dsr.save()
        return dsr

    @classmethod
    def _process_erasure(cls, dsr, performed_by):
        """Process an erasure request (Art. 17)."""
        result = {"anonymized_partners": [], "anonymized_users": []}

        if dsr.related_partner:
            cls.anonymize_partner(dsr.related_partner.pk, performed_by)
            result["anonymized_partners"].append(dsr.related_partner.pk)
        elif dsr.subject_type == "partner":
            partners = BusinessPartner.objects.filter(email__iexact=dsr.subject_email)
            for bp in partners:
                cls.anonymize_partner(bp.pk, performed_by)
                result["anonymized_partners"].append(bp.pk)

        if dsr.related_user:
            cls.anonymize_user(dsr.related_user.pk, performed_by)
            result["anonymized_users"].append(dsr.related_user.pk)
        elif dsr.subject_type == "user":
            users = User.objects.filter(email__iexact=dsr.subject_email)
            for user in users:
                cls.anonymize_user(user.pk, performed_by)
                result["anonymized_users"].append(user.pk)

        result["note"] = (
            "Personenbezogene Daten wurden anonymisiert. "
            "Rechnungsdaten bleiben gem. GoBD (10 Jahre Aufbewahrungspflicht) erhalten."
        )
        return result

    @classmethod
    def _process_restriction(cls, dsr):
        """Process a restriction request (Art. 18)."""
        result = {"restricted_partners": [], "restricted_users": []}

        if dsr.subject_type == "partner":
            partners = BusinessPartner.objects.filter(email__iexact=dsr.subject_email)
            for bp in partners:
                bp.is_active = False
                bp.save(update_fields=["is_active", "updated_at"])
                result["restricted_partners"].append(bp.pk)

        elif dsr.subject_type == "user":
            users = User.objects.filter(email__iexact=dsr.subject_email)
            for user in users:
                user.is_active = False
                user.save(update_fields=["is_active"])
                result["restricted_users"].append(user.pk)

        return result

    # ── Deadline Monitoring ────────────────────────────────────────────

    @classmethod
    def get_overdue_requests(cls):
        """Return all DSRs that are past their 30-day deadline."""
        return DataSubjectRequest.objects.filter(
            status__in=[
                DataSubjectRequest.RequestStatus.RECEIVED,
                DataSubjectRequest.RequestStatus.IN_PROGRESS,
            ],
            deadline__lt=timezone.now().date(),
        )

    @classmethod
    def get_upcoming_deadlines(cls, days=7):
        """Return DSRs with deadlines in the next N days."""
        cutoff = timezone.now().date() + timedelta(days=days)
        return DataSubjectRequest.objects.filter(
            status__in=[
                DataSubjectRequest.RequestStatus.RECEIVED,
                DataSubjectRequest.RequestStatus.IN_PROGRESS,
            ],
            deadline__lte=cutoff,
            deadline__gte=timezone.now().date(),
        )

    # ── Export (Art. 20 Datenübertragbarkeit) ──────────────────────────

    @classmethod
    def export_subject_data_json(cls, dsr):
        """Export collected data as JSON string (Art. 20)."""
        data = cls.collect_subject_data(dsr)
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
