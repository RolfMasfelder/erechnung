"""Admin configuration for GDPR/DSGVO models."""

from django.contrib import admin
from django.utils.html import format_html

from invoice_app.models.gdpr import ConsentRecord, DataSubjectRequest, PrivacyImpactAssessment, ProcessingActivity


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    """Admin interface for GDPR Data Subject Requests."""

    list_display = (
        "short_id",
        "request_type",
        "subject_name",
        "status",
        "deadline_display",
        "created_at",
        "processed_by",
    )
    list_filter = ("request_type", "status", "subject_type")
    search_fields = ("subject_name", "subject_email", "description")
    readonly_fields = ("id", "created_at", "updated_at", "completed_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("related_user", "related_partner", "processed_by")

    fieldsets = (
        ("Anfrage", {"fields": ("id", "request_type", "status", "description")}),
        ("Betroffene Person", {"fields": ("subject_name", "subject_email", "subject_type")}),
        (
            "Verknüpfungen",
            {"fields": ("related_user", "related_partner"), "classes": ("collapse",)},
        ),
        ("Bearbeitung", {"fields": ("processed_by", "internal_notes", "rejection_reason", "result_data")}),
        ("Fristen", {"fields": ("deadline", "created_at", "updated_at", "completed_at")}),
    )

    def short_id(self, obj):
        return f"DSR-{obj.id.hex[:8]}"

    short_id.short_description = "ID"

    def deadline_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠ {} (überfällig)</span>', obj.deadline)
        days = obj.days_remaining
        if days is not None and days <= 7:
            return format_html('<span style="color: orange;">{} ({} Tage)</span>', obj.deadline, days)
        return obj.deadline

    deadline_display.short_description = "Frist"


@admin.register(ProcessingActivity)
class ProcessingActivityAdmin(admin.ModelAdmin):
    """Admin interface for the Processing Activities Register (Art. 30)."""

    list_display = ("name", "legal_basis", "responsible_department", "is_active", "updated_at")
    list_filter = ("legal_basis", "is_active", "third_country_transfer")
    search_fields = ("name", "purpose", "data_categories")

    fieldsets = (
        ("Verarbeitungstätigkeit", {"fields": ("name", "purpose", "legal_basis", "legal_basis_detail")}),
        ("Datenkategorien", {"fields": ("data_subjects", "data_categories", "recipients")}),
        (
            "Drittlandübermittlung",
            {"fields": ("third_country_transfer", "third_country_details"), "classes": ("collapse",)},
        ),
        ("Löschfristen & TOM", {"fields": ("retention_period", "tom_reference")}),
        ("Organisation", {"fields": ("responsible_department", "is_active")}),
    )


@admin.register(PrivacyImpactAssessment)
class PrivacyImpactAssessmentAdmin(admin.ModelAdmin):
    """Admin interface for Privacy Impact Assessments (Art. 35)."""

    list_display = ("feature_name", "risk_level", "status", "reviewer", "review_date")
    list_filter = ("risk_level", "status")
    search_fields = ("feature_name", "description", "data_types")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("reviewer",)

    fieldsets = (
        ("Feature", {"fields": ("feature_name", "description", "data_types")}),
        ("Risikobewertung", {"fields": ("risk_level", "risk_description", "mitigation_measures")}),
        ("Prüfung", {"fields": ("status", "reviewer", "review_date", "review_notes")}),
        ("Zeitstempel", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Admin interface for Consent Records (Art. 7)."""

    list_display = ("user", "purpose", "granted", "granted_at", "revoked_at")
    list_filter = ("purpose", "granted")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("granted_at", "revoked_at", "ip_address")
    raw_id_fields = ("user",)
