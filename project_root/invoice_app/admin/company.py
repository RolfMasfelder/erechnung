"""Admin configuration for Company model."""

from django.contrib import admin

from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import Company


@admin.register(Company)
class CompanyAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for Company model."""

    list_display = ("name", "tax_id", "vat_id", "city", "country", "email", "is_active")
    search_fields = ("name", "tax_id", "vat_id", "email")
    list_filter = ("country", "is_active")
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "legal_name", "tax_id", "vat_id", "commercial_register", "is_active")},
        ),
        ("Contact Information", {"fields": ("email", "phone", "fax", "website")}),
        (
            "Address",
            {"fields": ("address_line1", "address_line2", "postal_code", "city", "state_province", "country")},
        ),
        ("Branding", {"fields": ("logo",)}),
        ("Banking Details", {"fields": ("bank_name", "bank_account", "iban", "bic")}),
        ("Business Settings", {"fields": ("default_currency", "default_payment_terms")}),
    )
