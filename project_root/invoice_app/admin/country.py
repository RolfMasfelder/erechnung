"""
Country admin configuration for the invoice_app application.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from invoice_app.models import Country, CountryTaxRate


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin configuration for the Country model."""

    list_display = (
        "code",
        "name",
        "currency_code",
        "is_eu_member",
        "is_eurozone",
        "standard_vat_rate",
        "reduced_vat_rate",
        "is_active",
    )
    list_filter = ("is_eu_member", "is_eurozone", "is_active", "currency_code")
    search_fields = ("code", "name", "name_local")
    ordering = ("name",)

    fieldsets = (
        (
            _("ISO Codes"),
            {
                "fields": ("code", "code_alpha3", "numeric_code"),
            },
        ),
        (
            _("Names"),
            {
                "fields": ("name", "name_local"),
            },
        ),
        (
            _("Currency"),
            {
                "fields": ("currency_code", "currency_name", "currency_symbol"),
            },
        ),
        (
            _("Language & Formatting"),
            {
                "fields": ("default_language", "date_format", "decimal_separator", "thousands_separator"),
                "classes": ("collapse",),
            },
        ),
        (
            _("EU & Tax"),
            {
                "fields": (
                    "is_eu_member",
                    "is_eurozone",
                    "standard_vat_rate",
                    "reduced_vat_rate",
                    "super_reduced_vat_rate",
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active",),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(CountryTaxRate)
class CountryTaxRateAdmin(admin.ModelAdmin):
    """Admin configuration for legally valid VAT rates."""

    list_display = ("country", "rate_type", "rate", "valid_from", "valid_to", "is_active")
    list_filter = ("country", "rate_type", "is_active")
    search_fields = ("country__code", "country__name", "country__name_local")
    ordering = ("country__code", "-valid_from", "rate_type")
    date_hierarchy = "valid_from"
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            _("Tax Rate"),
            {
                "fields": (
                    "country",
                    "rate_type",
                    "rate",
                    "valid_from",
                    "valid_to",
                    "is_active",
                )
            },
        ),
        (
            _("System"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
