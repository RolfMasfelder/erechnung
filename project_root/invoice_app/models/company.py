"""
Company model for the invoice_app application.

Represents the invoice issuing organization (your own company/organization).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from invoice_app.models.helpers import COUNTRY_CODE_MAP


class Company(models.Model):
    """
    Company model representing the invoice issuing organization.
    This is typically your own company/organization.
    """

    name = models.CharField(_("Company Name"), max_length=255)
    legal_name = models.CharField(_("Legal Name"), max_length=255, blank=True)
    tax_id = models.CharField(_("Tax ID"), max_length=50, unique=True)
    vat_id = models.CharField(_("VAT ID"), max_length=50, blank=True)
    commercial_register = models.CharField(_("Commercial Register"), max_length=100, blank=True)

    # Address information
    address_line1 = models.CharField(_("Address Line 1"), max_length=255)
    address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20)
    city = models.CharField(_("City"), max_length=100)
    state_province = models.CharField(_("State/Province"), max_length=100, blank=True)
    country = models.CharField(_("Country"), max_length=100)

    # Contact information
    phone = models.CharField(_("Phone"), max_length=50, blank=True)
    fax = models.CharField(_("Fax"), max_length=50, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    website = models.URLField(_("Website"), blank=True)

    # Branding
    logo = models.ImageField(
        _("Logo"),
        upload_to="company_logos/",
        blank=True,
        null=True,
        help_text=_("Company logo for invoices (PNG/JPG, max 60mm × 20mm recommended)"),
    )

    # Banking information
    bank_name = models.CharField(_("Bank Name"), max_length=255, blank=True)
    bank_account = models.CharField(_("Bank Account"), max_length=50, blank=True)
    iban = models.CharField(_("IBAN"), max_length=34, blank=True)
    bic = models.CharField(_("BIC/SWIFT"), max_length=11, blank=True)

    # Business settings
    default_currency = models.CharField(_("Default Currency"), max_length=3, default="EUR")
    default_payment_terms = models.PositiveIntegerField(_("Default Payment Terms (days)"), default=30)

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ["name"]

    def clean(self):
        """Validate BR-CO-26: at least vat_id or commercial_register must be set."""
        super().clean()
        if not self.vat_id and not self.commercial_register:
            raise ValidationError(
                _(
                    "Für eine gültige ZUGFeRD-Rechnung muss mindestens die USt-IdNr. (BT-31) "
                    "oder das Handelsregister (BT-30) angegeben werden (Regel BR-CO-26)."
                ),
                code="br_co_26_missing_seller_id",
            )

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        """Return formatted full address."""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([f"{self.postal_code} {self.city}"])
        if self.state_province:
            address_parts.append(self.state_province)
        address_parts.append(self.country)
        return ", ".join(address_parts)

    # ZUGFeRD-specific properties (mapping to official structure)
    @property
    def street_name(self):
        """Street name for ZUGFeRD XML (maps to address_line1)."""
        return self.address_line1 or ""

    @property
    def city_name(self):
        """City name for ZUGFeRD XML (maps to city)."""
        return self.city or ""

    @property
    def postcode_code(self):
        """Postcode for ZUGFeRD XML (maps to postal_code)."""
        return self.postal_code or ""

    @property
    def country_id(self):
        """Country ID for ZUGFeRD XML - ISO 3166-1 alpha-2 code.

        Maps country name to ISO code. Defaults to 'DE' for Germany.
        """
        return COUNTRY_CODE_MAP.get(self.country, "DE")
