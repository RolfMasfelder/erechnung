"""
BusinessPartner model for the invoice_app application.

Represents business partners who can be customers (receive invoices from us),
suppliers (send invoices to us), or both.
"""

import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_leitweg_id(value):
    """
    Validate Leitweg-ID format and Modulo-97 check digit (ISO 7064).

    Format: <Grobadressierung>-<Feinadressierung>-<Prüfziffer>
    - Grobadressierung: 2–12 digits
    - Feinadressierung: 1–30 alphanumeric characters
    - Prüfziffer: 2-digit Modulo-97 check (98 - mod97 of numeric representation)
    """
    pattern = r"^(\d{2,12})-([A-Za-z0-9]{1,30})-(\d{2})$"
    match = re.match(pattern, value)
    if not match:
        raise ValidationError(
            _("Ungültiges Leitweg-ID Format. Erwartet: <2-12 Ziffern>-<1-30 alphanumerisch>-<2 Ziffern Prüfziffer>"),
            code="invalid_leitweg_format",
        )

    grob = match.group(1)
    fein = match.group(2)
    check_digits = int(match.group(3))

    # Build numeric string: digits stay, letters → two-digit number (A=10, B=11, …, Z=35)
    numeric_str = ""
    for ch in grob + fein:
        if ch.isdigit():
            numeric_str += ch
        else:
            numeric_str += str(ord(ch.upper()) - ord("A") + 10)

    # Modulo-97 check digit per ISO 7064
    expected = 98 - (int(numeric_str) % 97)
    if check_digits != expected:
        raise ValidationError(
            _("Leitweg-ID Prüfziffer ungültig. Erwartet: %(expected)02d, erhalten: %(actual)02d")
            % {"expected": expected, "actual": check_digits},
            code="invalid_leitweg_checksum",
        )


class BusinessPartner(models.Model):
    """
    BusinessPartner model representing organizations or individuals we do business with.

    A partner can be:
    - Customer only (is_customer=True): receives invoices from us (outgoing invoices)
    - Supplier only (is_supplier=True): sends invoices to us (incoming invoices)
    - Both (is_customer=True, is_supplier=True): bidirectional business relationship
    """

    class PartnerType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", _("Individual")
        BUSINESS = "BUSINESS", _("Business")
        GOVERNMENT = "GOVERNMENT", _("Government")
        NON_PROFIT = "NON_PROFIT", _("Non-Profit")

    # Partner role flags
    is_customer = models.BooleanField(
        _("Is Customer"),
        default=True,
        help_text=_("Partner can receive invoices from us (outgoing invoices)"),
    )
    is_supplier = models.BooleanField(
        _("Is Supplier"),
        default=False,
        help_text=_("Partner can send invoices to us (incoming invoices)"),
    )

    # Basic information
    partner_type = models.CharField(
        _("Partner Type"),
        max_length=20,
        choices=PartnerType.choices,
        default=PartnerType.BUSINESS,
    )
    partner_number = models.CharField(
        _("Partner Number"),
        max_length=50,
        unique=True,
        blank=True,
    )

    # Individual partner fields
    first_name = models.CharField(_("First Name"), max_length=100, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=100, blank=True)

    # Business partner fields
    company_name = models.CharField(_("Company Name"), max_length=255, blank=True)
    legal_name = models.CharField(_("Legal Name"), max_length=255, blank=True)
    tax_id = models.CharField(_("Tax ID"), max_length=50, blank=True)
    vat_id = models.CharField(_("VAT ID"), max_length=50, blank=True)
    commercial_register = models.CharField(_("Commercial Register"), max_length=100, blank=True)

    # XRechnung / B2G fields
    leitweg_id = models.CharField(
        _("Leitweg-ID"),
        max_length=46,
        blank=True,
        validators=[validate_leitweg_id],
        help_text=_("Leitweg-ID for government invoices (XRechnung). Required when partner_type is GOVERNMENT."),
    )

    # Address information
    address_line1 = models.CharField(_("Address Line 1"), max_length=255)
    address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20)
    city = models.CharField(_("City"), max_length=100)
    state_province = models.CharField(_("State/Province"), max_length=100, blank=True)

    # Country reference (ForeignKey to Country model)
    country = models.ForeignKey(
        "invoice_app.Country",
        on_delete=models.PROTECT,
        related_name="business_partners",
        verbose_name=_("Country"),
        help_text=_("Partner's country - determines tax rates and currency"),
        null=True,
        blank=True,
        db_column="country",
    )

    # Contact information
    phone = models.CharField(_("Phone"), max_length=50, blank=True)
    fax = models.CharField(_("Fax"), max_length=50, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    website = models.URLField(_("Website"), blank=True)

    # Business relationship
    payment_terms = models.PositiveIntegerField(
        _("Payment Terms (days)"),
        default=30,
        blank=True,
    )
    credit_limit = models.DecimalField(
        _("Credit Limit"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    preferred_currency = models.CharField(
        _("Preferred Currency"),
        max_length=3,
        default="EUR",
        blank=True,
    )
    default_reference_prefix = models.CharField(
        _("Default Reference Prefix"),
        max_length=20,
        blank=True,
        help_text=_("Default prefix for customer order references (e.g., 'PO-', 'ORDER-', 'PROJ-')"),
    )

    # Additional contacts
    contact_person = models.CharField(_("Contact Person"), max_length=255, blank=True)
    accounting_contact = models.CharField(_("Accounting Contact"), max_length=255, blank=True)
    accounting_email = models.EmailField(_("Accounting Email"), blank=True)

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Business Partner")
        verbose_name_plural = _("Business Partners")
        ordering = ["company_name", "last_name", "first_name"]
        db_table = "invoice_app_businesspartner"

    def clean(self):
        """Validate that GOVERNMENT partners have a Leitweg-ID."""
        super().clean()
        if self.partner_type == self.PartnerType.GOVERNMENT and not self.leitweg_id:
            raise ValidationError(
                {"leitweg_id": _("Leitweg-ID ist für öffentliche Auftraggeber (GOVERNMENT) erforderlich.")},
            )

    def __str__(self):
        if self.partner_type == self.PartnerType.INDIVIDUAL:
            return f"{self.first_name} {self.last_name}".strip()
        else:
            return self.company_name or f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Return appropriate display name based on partner type."""
        if self.partner_type == self.PartnerType.INDIVIDUAL:
            return f"{self.first_name} {self.last_name}".strip()
        else:
            return self.company_name or f"{self.first_name} {self.last_name}".strip()

    @property
    def name(self):
        """Alias for display_name."""
        return self.display_name

    @property
    def role_display(self):
        """Return human-readable role description."""
        if self.is_customer and self.is_supplier:
            return _("Customer & Supplier")
        elif self.is_customer:
            return _("Customer")
        elif self.is_supplier:
            return _("Supplier")
        else:
            return _("Inactive Partner")

    @property
    def full_address(self):
        """Return formatted full address."""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([f"{self.postal_code} {self.city}"])
        if self.state_province:
            address_parts.append(self.state_province)
        if self.country:
            address_parts.append(self.country.name)
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

        Returns the country code from the linked Country model.
        Defaults to 'DE' for Germany if no country is set.
        """
        if self.country:
            return self.country.code
        return "DE"

    @property
    def country_name(self):
        """Country name for display purposes."""
        if self.country:
            return self.country.name
        return ""

    def get_applicable_vat_rate(self, category="standard"):
        """
        Get the applicable VAT rate for this partner based on their country.

        Args:
            category: One of 'standard', 'reduced', 'super_reduced', 'zero'

        Returns:
            Decimal: The VAT rate as percentage, or 19.00 as default
        """
        from decimal import Decimal

        if self.country:
            return self.country.get_vat_rate(category)
        return Decimal("19.00")  # German default

    def save(self, *args, **kwargs):
        """Generate partner number if not provided."""
        if not self.partner_number:
            # Generate partner number based on type and creation order
            prefix = "IND" if self.partner_type == self.PartnerType.INDIVIDUAL else "BUS"
            last_partner = BusinessPartner.objects.filter(partner_number__startswith=prefix).order_by("-id").first()
            if last_partner and last_partner.partner_number:
                try:
                    last_num = int(last_partner.partner_number[3:])
                    self.partner_number = f"{prefix}{last_num + 1:06d}"
                except (ValueError, IndexError):
                    self.partner_number = f"{prefix}000001"
            else:
                self.partner_number = f"{prefix}000001"
        super().save(*args, **kwargs)
