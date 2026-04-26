"""
DSGVO/GDPR Models — Data Subject Requests, Processing Activities,
Privacy Impact Assessments, Consent Records, and Data Classification.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ── Data Classification ────────────────────────────────────────────────────


class DataClassification(models.TextChoices):
    PUBLIC = "public", _("Öffentlich")
    INTERNAL = "internal", _("Intern")
    CONFIDENTIAL = "confidential", _("Vertraulich")
    RESTRICTED = "restricted", _("Streng vertraulich")


# Registry mapping model fields to their classification
DATA_CLASSIFICATION_REGISTRY = {
    # BusinessPartner PII
    "BusinessPartner.first_name": DataClassification.CONFIDENTIAL,
    "BusinessPartner.last_name": DataClassification.CONFIDENTIAL,
    "BusinessPartner.email": DataClassification.CONFIDENTIAL,
    "BusinessPartner.phone": DataClassification.CONFIDENTIAL,
    "BusinessPartner.fax": DataClassification.CONFIDENTIAL,
    "BusinessPartner.contact_person": DataClassification.CONFIDENTIAL,
    "BusinessPartner.accounting_contact": DataClassification.CONFIDENTIAL,
    "BusinessPartner.accounting_email": DataClassification.CONFIDENTIAL,
    "BusinessPartner.company_name": DataClassification.INTERNAL,
    "BusinessPartner.legal_name": DataClassification.INTERNAL,
    "BusinessPartner.tax_id": DataClassification.RESTRICTED,
    "BusinessPartner.vat_id": DataClassification.CONFIDENTIAL,
    "BusinessPartner.address_line1": DataClassification.CONFIDENTIAL,
    "BusinessPartner.address_line2": DataClassification.CONFIDENTIAL,
    "BusinessPartner.postal_code": DataClassification.INTERNAL,
    "BusinessPartner.city": DataClassification.INTERNAL,
    "BusinessPartner.website": DataClassification.PUBLIC,
    # UserProfile PII
    "UserProfile.employee_id": DataClassification.CONFIDENTIAL,
    "UserProfile.phone": DataClassification.CONFIDENTIAL,
    "UserProfile.mobile": DataClassification.CONFIDENTIAL,
    "UserProfile.department": DataClassification.INTERNAL,
    "UserProfile.last_login_ip": DataClassification.CONFIDENTIAL,
    "UserProfile.mfa_secret": DataClassification.RESTRICTED,
    "UserProfile.backup_codes": DataClassification.RESTRICTED,
    # Django User
    "User.username": DataClassification.INTERNAL,
    "User.email": DataClassification.CONFIDENTIAL,
    "User.first_name": DataClassification.CONFIDENTIAL,
    "User.last_name": DataClassification.CONFIDENTIAL,
    "User.password": DataClassification.RESTRICTED,
    # AuditLog
    "AuditLog.username": DataClassification.INTERNAL,
    "AuditLog.ip_address": DataClassification.CONFIDENTIAL,
    "AuditLog.user_agent": DataClassification.INTERNAL,
    "AuditLog.session_key": DataClassification.RESTRICTED,
    # Invoice — business data, not PII
    "Invoice.invoice_number": DataClassification.INTERNAL,
    "Invoice.total_amount": DataClassification.CONFIDENTIAL,
}


def get_classification(model_name, field_name):
    """Get the data classification for a model field."""
    key = f"{model_name}.{field_name}"
    return DATA_CLASSIFICATION_REGISTRY.get(key)


def get_unclassified_fields():
    """Return model fields that have no classification assigned."""
    from django.apps import apps

    unclassified = []

    pii_models = ["BusinessPartner", "UserProfile"]
    for model_name in pii_models:
        try:
            model = apps.get_model("invoice_app", model_name)
        except LookupError:
            continue
        for field in model._meta.get_fields():
            if hasattr(field, "column") and field.name not in ("id", "pk"):
                key = f"{model_name}.{field.name}"
                if key not in DATA_CLASSIFICATION_REGISTRY:
                    unclassified.append(key)

    return unclassified


# ── Data Subject Request (Art. 15-20 DSGVO) ───────────────────────────────


class DataSubjectRequest(models.Model):
    """Tracks GDPR data subject requests (Betroffenenrechte)."""

    class RequestType(models.TextChoices):
        ACCESS = "access", _("Auskunft (Art. 15)")
        ERASURE = "erasure", _("Löschung (Art. 17)")
        RECTIFICATION = "rectification", _("Berichtigung (Art. 16)")
        PORTABILITY = "portability", _("Datenübertragbarkeit (Art. 20)")
        RESTRICTION = "restriction", _("Einschränkung (Art. 18)")
        OBJECTION = "objection", _("Widerspruch (Art. 21)")

    class RequestStatus(models.TextChoices):
        RECEIVED = "received", _("Eingegangen")
        IN_PROGRESS = "in_progress", _("In Bearbeitung")
        COMPLETED = "completed", _("Abgeschlossen")
        REJECTED = "rejected", _("Abgelehnt")
        ESCALATED = "escalated", _("Eskaliert")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(_("Antragstyp"), max_length=20, choices=RequestType.choices)
    status = models.CharField(
        _("Status"), max_length=20, choices=RequestStatus.choices, default=RequestStatus.RECEIVED
    )

    # Who is the data subject?
    subject_email = models.EmailField(_("E-Mail der betroffenen Person"))
    subject_name = models.CharField(_("Name der betroffenen Person"), max_length=255)
    subject_type = models.CharField(
        _("Betroffenentyp"),
        max_length=20,
        choices=[("user", _("Benutzer")), ("partner", _("Geschäftspartner"))],
    )

    # Request details
    description = models.TextField(_("Beschreibung"), blank=True)
    internal_notes = models.TextField(_("Interne Notizen"), blank=True)
    rejection_reason = models.TextField(_("Ablehnungsgrund"), blank=True)

    # Linked records (optional)
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsr_requests",
        verbose_name=_("Verknüpfter Benutzer"),
    )
    related_partner = models.ForeignKey(
        "invoice_app.BusinessPartner",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsr_requests",
        verbose_name=_("Verknüpfter Geschäftspartner"),
    )

    # Processing
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsr_processed",
        verbose_name=_("Bearbeitet von"),
    )
    result_data = models.JSONField(_("Ergebnisdaten"), default=dict, blank=True)

    # Timestamps & SLA
    created_at = models.DateTimeField(_("Erstellt am"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aktualisiert am"), auto_now=True)
    deadline = models.DateField(_("Frist (30 Tage)"))
    completed_at = models.DateTimeField(_("Abgeschlossen am"), null=True, blank=True)

    class Meta:
        verbose_name = _("Betroffenenanfrage (DSGVO)")
        verbose_name_plural = _("Betroffenenanfragen (DSGVO)")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "deadline"]),
            models.Index(fields=["subject_email"]),
        ]

    def __str__(self):
        return f"DSR-{self.id.hex[:8]} ({self.get_request_type_display()}) — {self.subject_name}"

    def save(self, *args, **kwargs):
        if not self.deadline:
            self.deadline = (timezone.now() + timezone.timedelta(days=30)).date()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return self.status not in (self.RequestStatus.COMPLETED, self.RequestStatus.REJECTED) and (
            timezone.now().date() > self.deadline
        )

    @property
    def days_remaining(self):
        if self.status in (self.RequestStatus.COMPLETED, self.RequestStatus.REJECTED):
            return None
        return (self.deadline - timezone.now().date()).days


# ── Processing Activity Register (Art. 30 DSGVO) ──────────────────────────


class ProcessingActivity(models.Model):
    """Verarbeitungsverzeichnis nach Art. 30 DSGVO."""

    class LegalBasis(models.TextChoices):
        CONTRACT = "contract", _("Vertragserfüllung (Art. 6 Abs. 1 lit. b)")
        LEGAL_OBLIGATION = "legal_obligation", _("Rechtliche Verpflichtung (Art. 6 Abs. 1 lit. c)")
        LEGITIMATE_INTEREST = "legitimate_interest", _("Berechtigtes Interesse (Art. 6 Abs. 1 lit. f)")
        CONSENT = "consent", _("Einwilligung (Art. 6 Abs. 1 lit. a)")
        PUBLIC_INTEREST = "public_interest", _("Öffentliches Interesse (Art. 6 Abs. 1 lit. e)")

    name = models.CharField(_("Verarbeitungstätigkeit"), max_length=255, unique=True)
    purpose = models.TextField(_("Zweck der Verarbeitung"))
    legal_basis = models.CharField(_("Rechtsgrundlage"), max_length=30, choices=LegalBasis.choices)
    legal_basis_detail = models.TextField(_("Detaillierte Rechtsgrundlage"), blank=True)

    # Categories
    data_subjects = models.TextField(_("Kategorien betroffener Personen"))
    data_categories = models.TextField(_("Kategorien personenbezogener Daten"))
    recipients = models.TextField(_("Empfänger"), blank=True)

    # Transfer & Retention
    third_country_transfer = models.BooleanField(_("Drittlandübermittlung"), default=False)
    third_country_details = models.TextField(_("Details Drittlandübermittlung"), blank=True)
    retention_period = models.CharField(_("Löschfristen"), max_length=255)

    # Technical & Organizational Measures
    tom_reference = models.TextField(_("Technische und organisatorische Maßnahmen"), blank=True)

    # Metadata
    responsible_department = models.CharField(_("Verantwortliche Abteilung"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Aktiv"), default=True)
    created_at = models.DateTimeField(_("Erstellt am"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aktualisiert am"), auto_now=True)

    class Meta:
        verbose_name = _("Verarbeitungstätigkeit")
        verbose_name_plural = _("Verarbeitungsverzeichnis")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── Privacy Impact Assessment (Art. 35 DSGVO) ─────────────────────────────


class PrivacyImpactAssessment(models.Model):
    """Datenschutz-Folgenabschätzung (DSFA) nach Art. 35 DSGVO."""

    class RiskLevel(models.TextChoices):
        LOW = "low", _("Niedrig")
        MEDIUM = "medium", _("Mittel")
        HIGH = "high", _("Hoch")
        CRITICAL = "critical", _("Kritisch")

    class AssessmentStatus(models.TextChoices):
        DRAFT = "draft", _("Entwurf")
        IN_REVIEW = "in_review", _("In Prüfung")
        APPROVED = "approved", _("Genehmigt")
        REJECTED = "rejected", _("Abgelehnt")
        ARCHIVED = "archived", _("Archiviert")

    feature_name = models.CharField(_("Feature / System"), max_length=255)
    description = models.TextField(_("Beschreibung der Verarbeitung"))

    # Assessment
    data_types = models.TextField(_("Betroffene Datentypen"))
    risk_level = models.CharField(_("Risikoniveau"), max_length=10, choices=RiskLevel.choices)
    risk_description = models.TextField(_("Risikobeschreibung"))
    mitigation_measures = models.TextField(_("Gegenmaßnahmen"))

    # Status & Review
    status = models.CharField(
        _("Status"), max_length=20, choices=AssessmentStatus.choices, default=AssessmentStatus.DRAFT
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Prüfer"),
    )
    review_date = models.DateField(_("Prüfdatum"), null=True, blank=True)
    review_notes = models.TextField(_("Prüfnotizen"), blank=True)

    # Metadata
    created_at = models.DateTimeField(_("Erstellt am"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aktualisiert am"), auto_now=True)

    class Meta:
        verbose_name = _("Datenschutz-Folgenabschätzung")
        verbose_name_plural = _("Datenschutz-Folgenabschätzungen")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feature_name} ({self.get_risk_level_display()})"


# ── Consent Record ─────────────────────────────────────────────────────────


class ConsentRecord(models.Model):
    """Einwilligungsnachweis nach Art. 7 DSGVO."""

    class ConsentPurpose(models.TextChoices):
        ANALYTICS = "analytics", _("Nutzungsanalyse")
        NEWSLETTER = "newsletter", _("Newsletter")
        PROFILING = "profiling", _("Profiling")
        THIRD_PARTY = "third_party", _("Weitergabe an Dritte")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consent_records",
        verbose_name=_("Benutzer"),
    )
    purpose = models.CharField(_("Zweck"), max_length=30, choices=ConsentPurpose.choices)
    granted = models.BooleanField(_("Einwilligung erteilt"), default=False)

    granted_at = models.DateTimeField(_("Erteilt am"), null=True, blank=True)
    revoked_at = models.DateTimeField(_("Widerrufen am"), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_("IP-Adresse"), null=True, blank=True)

    class Meta:
        verbose_name = _("Einwilligungsnachweis")
        verbose_name_plural = _("Einwilligungsnachweise")
        unique_together = [("user", "purpose")]
        ordering = ["-granted_at"]

    def __str__(self):
        status = "✓" if self.granted and not self.revoked_at else "✗"
        return f"{status} {self.user} — {self.get_purpose_display()}"

    def grant(self, ip_address=None):
        self.granted = True
        self.granted_at = timezone.now()
        self.revoked_at = None
        self.ip_address = ip_address
        self.save()

    def revoke(self):
        self.granted = False
        self.revoked_at = timezone.now()
        self.save()
