"""
Country model for the invoice_app application.

Provides ISO-standardized country data including currency, language,
EU membership status, and VAT rates for tax calculations.
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    """
    Country model with ISO standards and tax information.

    Primary key is the ISO 3166-1 alpha-2 code (e.g., 'DE', 'AT', 'FR').
    Used for:
    - Customer location (determines applicable tax rates)
    - Currency defaults
    - Language preferences
    - EU/Eurozone membership for Reverse Charge logic
    """

    # ISO 3166-1 codes
    code = models.CharField(
        _("Country Code"),
        max_length=2,
        primary_key=True,
        help_text=_("ISO 3166-1 alpha-2 code (e.g., DE, AT, FR)"),
    )
    code_alpha3 = models.CharField(
        _("Alpha-3 Code"),
        max_length=3,
        help_text=_("ISO 3166-1 alpha-3 code (e.g., DEU, AUT, FRA)"),
    )
    numeric_code = models.CharField(
        _("Numeric Code"),
        max_length=3,
        help_text=_("ISO 3166-1 numeric code (e.g., 276, 040, 250)"),
    )

    # Country names
    name = models.CharField(
        _("Name (English)"),
        max_length=100,
        help_text=_("Official country name in English"),
    )
    name_local = models.CharField(
        _("Name (Local)"),
        max_length=100,
        help_text=_("Country name in local language"),
    )

    # Currency (ISO 4217)
    currency_code = models.CharField(
        _("Currency Code"),
        max_length=3,
        help_text=_("ISO 4217 currency code (e.g., EUR, CHF, USD)"),
    )
    currency_name = models.CharField(
        _("Currency Name"),
        max_length=50,
        help_text=_("Currency name (e.g., Euro, Swiss Franc)"),
    )
    currency_symbol = models.CharField(
        _("Currency Symbol"),
        max_length=5,
        help_text=_("Currency symbol (e.g., €, CHF, $)"),
    )

    # Language (ISO 639-1)
    default_language = models.CharField(
        _("Default Language"),
        max_length=5,
        help_text=_("ISO 639-1 language code (e.g., de, en, fr)"),
    )

    # EU & Eurozone status
    is_eu_member = models.BooleanField(
        _("EU Member"),
        default=False,
        help_text=_("Is this country a member of the European Union?"),
    )
    is_eurozone = models.BooleanField(
        _("Eurozone Member"),
        default=False,
        help_text=_("Does this country use the Euro as official currency?"),
    )

    # VAT rates (current, as of model creation date)
    standard_vat_rate = models.DecimalField(
        _("Standard VAT Rate"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Standard VAT rate in percent (e.g., 19.00 for Germany)"),
    )
    reduced_vat_rate = models.DecimalField(
        _("Reduced VAT Rate"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Reduced VAT rate in percent (e.g., 7.00 for Germany)"),
    )
    super_reduced_vat_rate = models.DecimalField(
        _("Super Reduced VAT Rate"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Super reduced VAT rate (used in FR, ES, IE, etc.)"),
    )

    # Formatting preferences
    date_format = models.CharField(
        _("Date Format"),
        max_length=20,
        default="DD.MM.YYYY",
        help_text=_("Date format pattern"),
    )
    decimal_separator = models.CharField(
        _("Decimal Separator"),
        max_length=1,
        default=",",
        help_text=_("Decimal separator character"),
    )
    thousands_separator = models.CharField(
        _("Thousands Separator"),
        max_length=1,
        default=".",
        help_text=_("Thousands separator character"),
    )

    # Audit fields
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def vat_rates(self):
        """Return all available VAT rates as a dict."""
        rates = {"standard": self.standard_vat_rate}
        if self.reduced_vat_rate is not None:
            rates["reduced"] = self.reduced_vat_rate
        if self.super_reduced_vat_rate is not None:
            rates["super_reduced"] = self.super_reduced_vat_rate
        rates["zero"] = Decimal("0.00")
        return rates

    def get_vat_rate(self, category="standard"):
        """
        Get VAT rate by category.

        Args:
            category: One of 'standard', 'reduced', 'super_reduced', 'zero'

        Returns:
            Decimal: The VAT rate as percentage
        """
        return self.vat_rates.get(category, self.standard_vat_rate)


class CountryTaxRate(models.Model):
    """Legally valid VAT rates per country with effective dates."""

    class RateType(models.TextChoices):
        EXEMPT = "EXEMPT", _("Exempt")
        REDUCED = "REDUCED", _("Reduced")
        STANDARD = "STANDARD", _("Standard")
        SUPER_REDUCED = "SUPER_REDUCED", _("Super Reduced")

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="tax_rates", verbose_name=_("Country"))
    rate_type = models.CharField(_("Rate Type"), max_length=20, choices=RateType.choices)
    rate = models.DecimalField(_("Tax Rate"), max_digits=5, decimal_places=2)
    valid_from = models.DateField(_("Valid From"))
    valid_to = models.DateField(_("Valid To"), null=True, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Country Tax Rate")
        verbose_name_plural = _("Country Tax Rates")
        ordering = ["country__code", "-valid_from", "rate_type", "rate"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "rate_type", "valid_from"], name="unique_country_rate_type_valid_from"
            )
        ]
        indexes = [
            models.Index(fields=["country", "valid_from", "valid_to"]),
            models.Index(fields=["country", "is_active"]),
        ]

    def __str__(self):
        return f"{self.country.code} {self.rate}% ({self.valid_from})"

    @classmethod
    def get_effective_rates(cls, country, on_date):
        """Return latest active legal rate per rate_type valid on a given date for a country."""
        base_queryset = cls.objects.filter(
            country=country,
            is_active=True,
            valid_from__lte=on_date,
        ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on_date))

        latest_rates = []
        for rate_type, _label in cls.RateType.choices:
            current = base_queryset.filter(rate_type=rate_type).order_by("-valid_from", "-id").first()
            if current:
                latest_rates.append(current)

        return latest_rates
