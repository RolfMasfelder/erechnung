"""
Product model for the invoice_app application.

Supports physical products, services, digital products, and subscriptions
with flexible pricing and tax handling.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UnitOfMeasure(models.IntegerChoices):
    """Interne numerische IDs für Maßeinheiten.
    Die Zuordnung zu UN/CEFACT-Codes (für ZUGFeRD-XML) erfolgt über UNCEFACT_CODES.

    Auf Modul-Ebene definiert, damit Meta.constraints dynamisch auf .values zugreifen
    kann — Python-Klassen-Scopes nehmen nicht an der LEGB-Lookup-Chain teil.
    Zugriff über Product.UnitOfMeasure bleibt überall funktionsfähig (Alias unten).
    """

    PCE = 1, _("Stück")
    HUR = 2, _("Stunde")
    DAY = 3, _("Tag")
    KGM = 4, _("Kilogramm")
    LTR = 5, _("Liter")
    MON = 6, _("Monat")


class Product(models.Model):
    """
    Product model for managing items/services that can be invoiced.
    Supports both physical products and services with flexible pricing and tax handling.
    """

    # Alias: Product.UnitOfMeasure bleibt überall nutzbar (backward-compatible)
    UnitOfMeasure = UnitOfMeasure

    # Mapping: interne ID → UN/CEFACT Recommendation 20 Code für ZUGFeRD-XML-Export
    UNIT_UNCEFACT_CODES = {
        UnitOfMeasure.PCE: "C62",  # Piece/Stück
        UnitOfMeasure.HUR: "HUR",  # Hour/Stunde
        UnitOfMeasure.DAY: "DAY",  # Day/Tag
        UnitOfMeasure.KGM: "KGM",  # Kilogram/Kilogramm
        UnitOfMeasure.LTR: "LTR",  # Liter
        UnitOfMeasure.MON: "MON",  # Month/Monat
    }

    class ProductType(models.TextChoices):
        PHYSICAL = "PHYSICAL", _("Physical Product")
        SERVICE = "SERVICE", _("Service")
        DIGITAL = "DIGITAL", _("Digital Product")
        SUBSCRIPTION = "SUBSCRIPTION", _("Subscription")

    class TaxCategory(models.TextChoices):
        STANDARD = "STANDARD", _("Standard Rate")
        REDUCED = "REDUCED", _("Reduced Rate")
        ZERO = "ZERO", _("Zero Rate")
        EXEMPT = "EXEMPT", _("Exempt")
        REVERSE_CHARGE = "REVERSE_CHARGE", _("Reverse Charge")

    # Basic product information
    product_code = models.CharField(_("Product Code"), max_length=100, unique=True)
    name = models.CharField(_("Product Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    product_type = models.CharField(
        _("Product Type"), max_length=20, choices=ProductType.choices, default=ProductType.PHYSICAL
    )

    # Categorization
    category = models.CharField(_("Category"), max_length=100, blank=True)
    subcategory = models.CharField(_("Subcategory"), max_length=100, blank=True)
    brand = models.CharField(_("Brand"), max_length=100, blank=True)
    manufacturer = models.CharField(_("Manufacturer"), max_length=255, blank=True)

    # Pricing information
    base_price = models.DecimalField(
        _("Base Price"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0
    )
    currency = models.CharField(_("Currency"), max_length=3, default="EUR")
    cost_price = models.DecimalField(
        _("Cost Price"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
    )
    list_price = models.DecimalField(
        _("List Price"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        null=True,
        blank=True,
    )

    # Units and measurements
    unit_of_measure = models.IntegerField(
        _("Unit of Measure"), choices=UnitOfMeasure.choices, default=UnitOfMeasure.PCE
    )
    weight = models.DecimalField(
        _("Weight"), max_digits=10, decimal_places=3, null=True, blank=True, help_text=_("Weight in kg")
    )
    dimensions = models.CharField(_("Dimensions"), max_length=100, blank=True, help_text=_("L x W x H in cm"))

    # Tax information
    tax_category = models.CharField(
        _("Tax Category"), max_length=20, choices=TaxCategory.choices, default=TaxCategory.STANDARD
    )
    default_tax_rate = models.DecimalField(
        _("Default Tax Rate"),
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        default=19.00,
    )
    tax_code = models.CharField(_("Tax Code"), max_length=50, blank=True)

    # Stock management (optional)
    track_inventory = models.BooleanField(_("Track Inventory"), default=False)
    stock_quantity = models.DecimalField(_("Stock Quantity"), max_digits=15, decimal_places=3, null=True, blank=True)
    minimum_stock = models.DecimalField(_("Minimum Stock"), max_digits=15, decimal_places=3, null=True, blank=True)

    # Additional product details
    barcode = models.CharField(_("Barcode"), max_length=100, blank=True)
    sku = models.CharField(_("SKU"), max_length=100, blank=True)
    tags = models.CharField(_("Tags"), max_length=500, blank=True, help_text=_("Comma-separated tags"))

    # Status and lifecycle
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_sellable = models.BooleanField(_("Is Sellable"), default=True)
    discontinuation_date = models.DateField(_("Discontinuation Date"), null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_products",
        verbose_name=_("Created By"),
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["product_code", "name"]
        indexes = [
            models.Index(fields=["product_code"]),
            models.Index(fields=["name"]),
            models.Index(fields=["category", "subcategory"]),
            models.Index(fields=["is_active", "is_sellable"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_of_measure__in=UnitOfMeasure.values),
                name="product_unit_of_measure_valid",
            ),
        ]

    def __str__(self):
        return f"{self.product_code} - {self.name}"

    @property
    def current_price(self):
        """Return the current selling price (base_price by default)."""
        return self.base_price

    @property
    def profit_margin(self):
        """Calculate profit margin if cost price is available."""
        if self.cost_price and self.cost_price > 0:
            return ((self.base_price - self.cost_price) / self.cost_price) * 100
        return None

    @property
    def is_in_stock(self):
        """Check if product is in stock (if inventory tracking is enabled)."""
        if not self.track_inventory:
            return True
        return self.stock_quantity and self.stock_quantity > 0

    @property
    def needs_restock(self):
        """Check if product needs restocking."""
        if not self.track_inventory or not self.minimum_stock:
            return False
        return self.stock_quantity and self.stock_quantity <= self.minimum_stock

    def get_tax_rate_for_partner(self, partner=None):
        """
        Get appropriate tax rate for a specific business partner.

        Determines the correct tax rate based on the relationship between
        the issuing company and the business partner:
        - Domestic: normal product tax rate
        - EU Reverse Charge: 0% (partner in EU with valid VAT ID)
        - Export (Drittland): 0% (partner outside EU)

        Args:
            partner: BusinessPartner instance or None

        Returns:
            Decimal: The applicable tax rate
        """
        from invoice_app.models import Company
        from invoice_app.services.tax_service import TaxService

        if not partner:
            return self.default_tax_rate

        company = Company.objects.filter(is_active=True).order_by("id").first()
        company_country_code = TaxService.get_company_country_code(company)

        determination = TaxService.get_tax_determination(
            product_tax_rate=self.default_tax_rate,
            product_tax_category=self.tax_category,
            company_country_code=company_country_code,
            partner=partner,
        )
        return determination.tax_rate

    def get_tax_determination_for_partner(self, partner=None):
        """
        Get full tax determination (rate + category + exemption reason) for a partner.

        Returns a TaxDetermination dataclass with:
        - scenario: TaxScenario enum
        - tax_rate: Decimal
        - tax_category_code: str (S, Z, E, AE, G)
        - exemption_reason: str

        Args:
            partner: BusinessPartner instance or None

        Returns:
            TaxDetermination dataclass
        """
        from invoice_app.models import Company
        from invoice_app.services.tax_service import TaxDetermination, TaxScenario, TaxService

        if not partner:
            from decimal import Decimal

            if self.tax_category == self.TaxCategory.EXEMPT:
                cat = "E"
            elif self.tax_category == self.TaxCategory.ZERO or self.default_tax_rate == Decimal("0"):
                cat = "Z"
            else:
                cat = "S"
            return TaxDetermination(
                scenario=TaxScenario.DOMESTIC,
                tax_rate=self.default_tax_rate,
                tax_category_code=cat,
                exemption_reason="",
            )

        company = Company.objects.filter(is_active=True).order_by("id").first()
        company_country_code = TaxService.get_company_country_code(company)

        return TaxService.get_tax_determination(
            product_tax_rate=self.default_tax_rate,
            product_tax_category=self.tax_category,
            company_country_code=company_country_code,
            partner=partner,
        )

    def clean(self):
        """Custom validation for the product model."""
        from invoice_app.models import Company, Country, CountryTaxRate

        if self.track_inventory and self.stock_quantity is None:
            raise ValidationError(_("Stock quantity is required when inventory tracking is enabled."))

        active_company = Company.objects.filter(is_active=True).order_by("id").first()
        if active_company:
            country_input = (active_company.country or "").strip()
            country = (
                Country.objects.filter(code__iexact=country_input).first()
                or Country.objects.filter(name__iexact=country_input).first()
                or Country.objects.filter(name_local__iexact=country_input).first()
            )
            if country:
                allowed_rates = {
                    rate_obj.rate
                    for rate_obj in CountryTaxRate.get_effective_rates(country=country, on_date=timezone.now().date())
                }
                if allowed_rates and self.default_tax_rate not in allowed_rates:
                    allowed_display = ", ".join(str(rate) for rate in sorted(allowed_rates))
                    raise ValidationError(
                        _("Ungültiger MwSt.-Satz für %(country)s. Erlaubt: %(rates)s")
                        % {"country": country.code, "rates": allowed_display}
                    )

        if self.discontinuation_date and self.discontinuation_date <= timezone.now().date():
            if self.is_active or self.is_sellable:
                raise ValidationError(_("Discontinued products cannot be active or sellable."))
