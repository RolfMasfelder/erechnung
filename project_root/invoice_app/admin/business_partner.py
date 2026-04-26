"""Admin configuration for BusinessPartner model."""

from django.contrib import admin

from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import BusinessPartner


@admin.register(BusinessPartner)
class BusinessPartnerAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for BusinessPartner model."""

    list_display = (
        "display_name",
        "partner_type",
        "role_display",
        "tax_id",
        "city",
        "country",
        "email",
        "is_active",
    )
    search_fields = ("company_name", "first_name", "last_name", "tax_id", "vat_id", "email", "partner_number")
    list_filter = ("partner_type", "is_customer", "is_supplier", "country", "is_active")
    fieldsets = (
        (
            "Partner Role",
            {
                "fields": ("is_customer", "is_supplier"),
                "description": "Define the business relationship with this partner.",
            },
        ),
        (
            "Basic Information",
            {
                "fields": (
                    "partner_type",
                    "partner_number",
                    "first_name",
                    "last_name",
                    "company_name",
                    "legal_name",
                    "is_active",
                )
            },
        ),
        ("Tax Information", {"fields": ("tax_id", "vat_id", "commercial_register")}),
        ("Contact Information", {"fields": ("email", "phone", "fax", "website")}),
        (
            "Address",
            {"fields": ("address_line1", "address_line2", "postal_code", "city", "state_province", "country")},
        ),
        ("Business Relationship", {"fields": ("payment_terms", "credit_limit", "preferred_currency")}),
        ("Additional Contacts", {"fields": ("contact_person", "accounting_contact", "accounting_email")}),
    )
