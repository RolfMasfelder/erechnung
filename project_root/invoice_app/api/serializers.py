"""
Serializers for the invoice_app API.
"""

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from invoice_app.models import (
    AuditLog,
    BusinessPartner,
    Company,
    ConsentRecord,
    Country,
    CountryTaxRate,
    DataSubjectRequest,
    Invoice,
    InvoiceAllowanceCharge,
    InvoiceAttachment,
    InvoiceLine,
    PrivacyImpactAssessment,
    ProcessingActivity,
    Product,
)


class CountryTaxRateSerializer(serializers.ModelSerializer):
    """Serializer for CountryTaxRate (historically valid VAT rates per country)."""

    rate_type_display = serializers.CharField(source="get_rate_type_display", read_only=True)

    class Meta:
        model = CountryTaxRate
        fields = [
            "id",
            "country",
            "rate_type",
            "rate_type_display",
            "rate",
            "valid_from",
            "valid_to",
            "is_active",
        ]
        read_only_fields = ("id", "country")


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for the Country model (read-only reference data)."""

    vat_rates = serializers.DictField(
        child=serializers.DecimalField(max_digits=5, decimal_places=2),
        read_only=True,
        help_text="VAT rates by type (e.g. standard, reduced)",
    )

    class Meta:
        model = Country
        fields = [
            "code",
            "code_alpha3",
            "numeric_code",
            "name",
            "name_local",
            "currency_code",
            "currency_name",
            "currency_symbol",
            "default_language",
            "is_eu_member",
            "is_eurozone",
            "standard_vat_rate",
            "reduced_vat_rate",
            "super_reduced_vat_rate",
            "date_format",
            "decimal_separator",
            "thousands_separator",
            "is_active",
            "vat_rates",
        ]


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for the Company model."""

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "legal_name",
            "tax_id",
            "vat_id",
            "commercial_register",
            "address_line1",
            "address_line2",
            "postal_code",
            "city",
            "state_province",
            "country",
            "phone",
            "fax",
            "email",
            "website",
            "logo",
            "bank_name",
            "bank_account",
            "iban",
            "bic",
            "default_currency",
            "default_payment_terms",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {
            "legal_name": {"required": False, "allow_blank": True},
            "vat_id": {"required": False, "allow_blank": True},
            "commercial_register": {"required": False, "allow_blank": True},
            "address_line2": {"required": False, "allow_blank": True},
            "state_province": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "fax": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "website": {"required": False, "allow_blank": True},
            "bank_name": {"required": False, "allow_blank": True},
            "bank_account": {"required": False, "allow_blank": True},
            "iban": {"required": False, "allow_blank": True},
            "bic": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        """Validate BR-CO-26: at least vat_id or commercial_register must be set."""
        attrs = super().validate(attrs)
        vat_id = attrs.get("vat_id", getattr(self.instance, "vat_id", "") if self.instance else "")
        commercial_register = attrs.get(
            "commercial_register",
            getattr(self.instance, "commercial_register", "") if self.instance else "",
        )
        if not vat_id and not commercial_register:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Für eine gültige ZUGFeRD-Rechnung muss mindestens die USt-IdNr. "
                        "oder das Handelsregister angegeben werden (Regel BR-CO-26)."
                    ]
                }
            )
        return attrs


class BusinessPartnerSerializer(serializers.ModelSerializer):
    """Serializer for the BusinessPartner model."""

    name = serializers.CharField(read_only=True, help_text="Display name (company or full name)")
    role_display = serializers.CharField(read_only=True, help_text="Business partner role")

    class Meta:
        model = BusinessPartner
        fields = [
            "id",
            "is_customer",
            "is_supplier",
            "partner_type",
            "partner_number",
            "first_name",
            "last_name",
            "company_name",
            "legal_name",
            "tax_id",
            "vat_id",
            "commercial_register",
            "leitweg_id",
            "address_line1",
            "address_line2",
            "postal_code",
            "city",
            "state_province",
            "country",
            "phone",
            "fax",
            "email",
            "website",
            "payment_terms",
            "credit_limit",
            "preferred_currency",
            "default_reference_prefix",
            "contact_person",
            "accounting_contact",
            "accounting_email",
            "is_active",
            "created_at",
            "updated_at",
            # Computed / read-only
            "name",
            "role_display",
        ]
        read_only_fields = ("partner_number", "created_at", "updated_at", "name", "role_display")

    def validate_vat_id(self, value):
        """Validate EU VAT ID format using TaxService."""
        if value:
            from invoice_app.services.tax_service import TaxService

            value = value.strip().upper()
            if len(value) < 5:
                raise serializers.ValidationError("USt-IdNr. zu kurz (min. 5 Zeichen)")
            if not TaxService.validate_vat_id_format(value):
                country_prefix = value[:2]
                raise serializers.ValidationError(
                    f"Ungültiges Format für USt-IdNr. mit Länderpräfix '{country_prefix}'"
                )
        return value

    def validate(self, attrs):
        """Validate that GOVERNMENT partners have a Leitweg-ID."""
        attrs = super().validate(attrs)
        partner_type = attrs.get(
            "partner_type",
            getattr(self.instance, "partner_type", "") if self.instance else "",
        )
        leitweg_id = attrs.get(
            "leitweg_id",
            getattr(self.instance, "leitweg_id", "") if self.instance else "",
        )
        if partner_type == BusinessPartner.PartnerType.GOVERNMENT and not leitweg_id:
            raise serializers.ValidationError(
                {"leitweg_id": "Leitweg-ID ist für öffentliche Auftraggeber (GOVERNMENT) erforderlich."}
            )
        return attrs


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for the Product model."""

    profit_margin = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    needs_restock = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    def validate_default_tax_rate(self, value):
        active_company = Company.objects.filter(is_active=True).order_by("id").first()
        if not active_company:
            return value

        country_input = (active_company.country or "").strip()
        country = (
            Country.objects.filter(code__iexact=country_input).first()
            or Country.objects.filter(name__iexact=country_input).first()
            or Country.objects.filter(name_local__iexact=country_input).first()
        )
        if not country:
            return value

        effective_rates = {
            rate_obj.rate
            for rate_obj in CountryTaxRate.get_effective_rates(country=country, on_date=timezone.now().date())
        }
        if effective_rates and value not in effective_rates:
            allowed_display = ", ".join(str(rate) for rate in sorted(effective_rates))
            raise serializers.ValidationError(
                f"Ungültiger MwSt.-Satz für {country.code}. Erlaubt sind aktuell: {allowed_display}"
            )

        return value

    class Meta:
        model = Product
        fields = [
            "id",
            "product_code",
            "name",
            "description",
            "product_type",
            "category",
            "subcategory",
            "brand",
            "manufacturer",
            "base_price",
            "currency",
            "cost_price",
            "list_price",
            "unit_of_measure",
            "weight",
            "dimensions",
            "tax_category",
            "default_tax_rate",
            "tax_code",
            "track_inventory",
            "stock_quantity",
            "minimum_stock",
            "barcode",
            "sku",
            "tags",
            "is_active",
            "is_sellable",
            "discontinuation_date",
            "created_at",
            "updated_at",
            "created_by",
            # Computed / read-only
            "profit_margin",
            "is_in_stock",
            "needs_restock",
            "current_price",
        ]
        read_only_fields = (
            "created_at",
            "updated_at",
            "created_by",
            "profit_margin",
            "is_in_stock",
            "needs_restock",
            "current_price",
        )


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for the AuditLog model (read-only)."""

    username_display = serializers.CharField(source="username", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "event_id",
            "timestamp",
            "action",
            "action_display",
            "severity",
            "severity_display",
            "username",
            "username_display",
            "object_type",
            "object_id",
            "object_repr",
            "description",
            "ip_address",
            "is_compliance_relevant",
            "is_security_event",
            "is_expired",
            "details",
        ]
        read_only_fields = (
            "event_id",
            "timestamp",
            "action",
            "severity",
            "username",
            "object_type",
            "object_id",
            "object_repr",
            "description",
            "ip_address",
            "is_compliance_relevant",
            "is_security_event",
            "details",
        )


class InvoiceAllowanceChargeSerializer(serializers.ModelSerializer):
    """Serializer for invoice allowances and charges (EN16931) — header or line level."""

    is_line_level = serializers.SerializerMethodField(help_text="True wenn Positionsebene, False wenn Rechnungsebene")

    @extend_schema_field(serializers.BooleanField)
    def get_is_line_level(self, obj):
        return obj.invoice_line_id is not None

    class Meta:
        model = InvoiceAllowanceCharge
        fields = [
            "id",
            "invoice",
            "invoice_line",
            "is_line_level",
            "is_charge",
            "actual_amount",
            "calculation_percent",
            "basis_amount",
            "reason_code",
            "reason",
            "sort_order",
        ]


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for the InvoiceLine model."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    effective_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    allowance_charges = serializers.SerializerMethodField(help_text="Positionsebene Rabatte/Zuschläge")

    @extend_schema_field(InvoiceAllowanceChargeSerializer(many=True))
    def get_allowance_charges(self, obj):
        qs = obj.allowance_charges.all()
        return InvoiceAllowanceChargeSerializer(qs, many=True).data

    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "invoice",
            "product",
            "product_name",
            "description",
            "product_code",
            "quantity",
            "unit_price",
            "effective_unit_price",
            "unit_of_measure",
            "tax_rate",
            "tax_amount",
            "discount_percentage",
            "discount_amount",
            "discount_reason",
            "line_subtotal",
            "line_total",
            "allowance_charges",
        ]
        read_only_fields = ("tax_amount", "line_subtotal", "line_total")


class InvoiceAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for the InvoiceAttachment model."""

    class Meta:
        model = InvoiceAttachment
        fields = [
            "id",
            "invoice",
            "file",
            "original_filename",
            "description",
            "attachment_type",
            "mime_type",
            "uploaded_at",
        ]
        read_only_fields = ("original_filename", "mime_type", "uploaded_at")

    def validate_file(self, value):
        """Validate file size (max 10 MB)."""
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"File size {value.size} bytes exceeds maximum of 10 MB.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for the Invoice model."""

    company_details = CompanySerializer(source="company", read_only=True)
    business_partner_details = BusinessPartnerSerializer(source="business_partner", read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    attachments = InvoiceAttachmentSerializer(many=True, read_only=True)
    # Only header-level A/Cs (invoice_line=null); line-level are nested in each InvoiceLine
    allowance_charges = serializers.SerializerMethodField(
        help_text="Rechnungsebene Rabatte/Zuschläge (ohne Positionsebene)"
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    invoice_type_display = serializers.CharField(source="get_invoice_type_display", read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    # Cross-references for credit notes / cancellations
    cancelled_by_number = serializers.CharField(source="cancelled_by.invoice_number", read_only=True, default=None)
    cancelled_by_id = serializers.IntegerField(source="cancelled_by.id", read_only=True, default=None)
    cancels_invoice_number = serializers.SerializerMethodField()
    cancels_invoice_id = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cancels_invoice_number(self, obj):
        try:
            return obj.cancels_invoice.invoice_number
        except Invoice.DoesNotExist:
            return None

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_cancels_invoice_id(self, obj):
        try:
            return obj.cancels_invoice.id
        except Invoice.DoesNotExist:
            return None

    @extend_schema_field(InvoiceAllowanceChargeSerializer(many=True))
    def get_allowance_charges(self, obj):
        qs = obj.allowance_charges.filter(invoice_line__isnull=True)
        return InvoiceAllowanceChargeSerializer(qs, many=True).data

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "invoice_type",
            "invoice_type_display",
            "company",
            "company_details",
            "business_partner",
            "business_partner_details",
            "issue_date",
            "due_date",
            "delivery_date",
            "currency",
            "subtotal",
            "tax_amount",
            "total_amount",
            "payment_terms",
            "payment_method",
            "payment_reference",
            "buyer_reference",
            "seller_reference",
            "status",
            "status_display",
            "pdf_file",
            "xml_file",
            "notes",
            "created_by",
            "created_at",
            "updated_at",
            "lines",
            "attachments",
            "allowance_charges",
            "is_paid",
            "is_overdue",
            # GoBD Compliance
            "is_locked",
            "locked_at",
            "lock_reason",
            "content_hash",
            "retention_until",
            "is_archived",
            "cancelled_by",
            "cancelled_by_number",
            "cancelled_by_id",
            "cancels_invoice_number",
            "cancels_invoice_id",
        ]
        read_only_fields = [
            "pdf_file",
            "xml_file",
            "invoice_number",
            "created_at",
            "updated_at",
            "is_locked",
            "locked_at",
            "lock_reason",
            "content_hash",
            "retention_until",
            "is_archived",
            "cancelled_by",
            "cancelled_by_number",
            "cancelled_by_id",
            "cancels_invoice_number",
            "cancels_invoice_id",
        ]

    def validate(self, attrs):
        """Auto-fill buyer_reference from leitweg_id for GOVERNMENT partners."""
        attrs = super().validate(attrs)
        partner = attrs.get("business_partner") or (self.instance.business_partner if self.instance else None)
        if partner and partner.partner_type == BusinessPartner.PartnerType.GOVERNMENT:
            if not attrs.get("buyer_reference") and partner.leitweg_id:
                attrs["buyer_reference"] = partner.leitweg_id
        return attrs


# =============================================================================
# Import Serializers
# =============================================================================


class BusinessPartnerImportRowSerializer(serializers.Serializer):
    """
    Serializer for a single row of business partner import data.
    Handles validation and conversion of CSV data to model-compatible format.
    """

    # Required fields
    company_name = serializers.CharField(max_length=255, required=True)
    address_line1 = serializers.CharField(max_length=255, required=True)
    postal_code = serializers.CharField(max_length=20, required=True)
    city = serializers.CharField(max_length=100, required=True)

    # Optional fields
    partner_type = serializers.ChoiceField(
        choices=BusinessPartner.PartnerType.choices,
        required=False,
        default=BusinessPartner.PartnerType.BUSINESS,
    )
    partner_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tax_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    vat_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    commercial_register = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, default="DE")
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fax = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    payment_terms = serializers.IntegerField(required=False, default=30, min_value=0)
    credit_limit = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    preferred_currency = serializers.CharField(max_length=3, required=False, default="EUR")
    contact_person = serializers.CharField(max_length=255, required=False, allow_blank=True)
    accounting_contact = serializers.CharField(max_length=255, required=False, allow_blank=True)
    accounting_email = serializers.EmailField(required=False, allow_blank=True)
    is_customer = serializers.BooleanField(required=False, default=True)
    is_supplier = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_country_code(self, value):
        """Validate that country code exists in database."""
        if value:
            value = value.upper().strip()
            if not Country.objects.filter(code=value).exists():
                raise serializers.ValidationError(f"Land mit Code '{value}' nicht gefunden")
        return value

    def validate_vat_id(self, value):
        """Validate EU VAT ID format using TaxService."""
        if value:
            from invoice_app.services.tax_service import TaxService

            value = value.strip().upper()
            # Basic length check
            if len(value) < 5:
                raise serializers.ValidationError("USt-IdNr. zu kurz (min. 5 Zeichen)")
            # Validate format against EU patterns
            if not TaxService.validate_vat_id_format(value):
                country_prefix = value[:2]
                raise serializers.ValidationError(
                    f"Ungültiges Format für USt-IdNr. mit Länderpräfix '{country_prefix}'"
                )
        return value


class BusinessPartnerImportSerializer(serializers.Serializer):
    """
    Serializer for bulk importing business partners.
    Accepts a list of rows and validates each one.
    """

    rows = BusinessPartnerImportRowSerializer(many=True)
    skip_duplicates = serializers.BooleanField(default=True)
    update_existing = serializers.BooleanField(default=False)

    def validate_rows(self, value):
        """Validate that we have at least one row."""
        if not value:
            raise serializers.ValidationError("Keine Daten zum Importieren")
        return value


class ProductImportRowSerializer(serializers.Serializer):
    """
    Serializer for a single row of product import data.
    Maps CSV/import field names to model field names.
    """

    # Required fields
    name = serializers.CharField(max_length=255, required=True)
    base_price = serializers.DecimalField(max_digits=15, decimal_places=2, required=True)

    # Optional fields
    product_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    product_type = serializers.ChoiceField(
        choices=Product.ProductType.choices,
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True)
    short_description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    subcategory = serializers.CharField(max_length=100, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    manufacturer = serializers.CharField(max_length=255, required=False, allow_blank=True)
    unit_of_measure = serializers.ChoiceField(
        choices=Product.UnitOfMeasure.choices,
        required=False,
        help_text="Numerische ID (1=Stück, 2=Stunde, 3=Tag, 4=kg, 5=Liter, 6=Monat)",
    )
    tax_category = serializers.ChoiceField(
        choices=Product.TaxCategory.choices,
        required=False,
    )
    # Accept 'tax_rate' from import but map to 'default_tax_rate'
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    default_tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    cost_price = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=3, required=False)
    is_active = serializers.BooleanField(required=False)
    is_sellable = serializers.BooleanField(required=False)
    track_inventory = serializers.BooleanField(required=False)
    stock_quantity = serializers.DecimalField(max_digits=15, decimal_places=3, required=False, allow_null=True)
    # Accept 'reorder_level' from import but map to 'minimum_stock'
    reorder_level = serializers.DecimalField(max_digits=15, decimal_places=3, required=False, allow_null=True)
    minimum_stock = serializers.DecimalField(max_digits=15, decimal_places=3, required=False, allow_null=True)

    def validate_base_price(self, value):
        """Ensure price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Preis muss größer als 0 sein")
        return value

    def to_internal_value(self, data):
        """Map import field names to model field names."""
        ret = super().to_internal_value(data)

        # Map 'tax_rate' to 'default_tax_rate' if provided
        if "tax_rate" in ret and ret["tax_rate"] is not None:
            ret["default_tax_rate"] = ret.pop("tax_rate")
        elif "tax_rate" in ret:
            del ret["tax_rate"]

        # Map 'reorder_level' to 'minimum_stock' if provided
        if "reorder_level" in ret and ret["reorder_level"] is not None:
            ret["minimum_stock"] = ret.pop("reorder_level")
        elif "reorder_level" in ret:
            del ret["reorder_level"]

        # List of valid Product model fields
        valid_fields = {
            "name",
            "product_code",
            "description",
            "product_type",
            "category",
            "subcategory",
            "brand",
            "manufacturer",
            "base_price",
            "currency",
            "cost_price",
            "unit_of_measure",
            "tax_category",
            "default_tax_rate",
            "track_inventory",
            "stock_quantity",
            "minimum_stock",
            "is_active",
            "is_sellable",
        }

        # Remove None values, empty strings, and invalid fields
        return {k: v for k, v in ret.items() if v is not None and v != "" and k in valid_fields}


class ProductImportSerializer(serializers.Serializer):
    """
    Serializer for bulk importing products.
    """

    rows = ProductImportRowSerializer(many=True)
    skip_duplicates = serializers.BooleanField(default=True)
    update_existing = serializers.BooleanField(default=False)

    def validate_rows(self, value):
        """Validate that we have at least one row."""
        if not value:
            raise serializers.ValidationError("Keine Daten zum Importieren")
        return value


class ImportResultSerializer(serializers.Serializer):
    """Serializer for import result response."""

    success = serializers.BooleanField()
    imported_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.DictField(), required=False)
    imported_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


# ── GDPR / DSGVO Serializers ──────────────────────────────────────────────


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    """Serializer for Data Subject Requests."""

    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    request_type_display = serializers.CharField(source="get_request_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DataSubjectRequest
        fields = [
            "id",
            "request_type",
            "request_type_display",
            "status",
            "status_display",
            "subject_email",
            "subject_name",
            "subject_type",
            "description",
            "internal_notes",
            "rejection_reason",
            "related_user",
            "related_partner",
            "processed_by",
            "result_data",
            "deadline",
            "created_at",
            "updated_at",
            "completed_at",
            "is_overdue",
            "days_remaining",
        ]
        read_only_fields = (
            "id",
            "processed_by",
            "result_data",
            "created_at",
            "updated_at",
            "completed_at",
        )


class ProcessingActivitySerializer(serializers.ModelSerializer):
    """Serializer for the Processing Activities Register."""

    legal_basis_display = serializers.CharField(source="get_legal_basis_display", read_only=True)

    class Meta:
        model = ProcessingActivity
        fields = [
            "id",
            "name",
            "purpose",
            "legal_basis",
            "legal_basis_display",
            "legal_basis_detail",
            "data_subjects",
            "data_categories",
            "recipients",
            "third_country_transfer",
            "third_country_details",
            "retention_period",
            "tom_reference",
            "responsible_department",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class PrivacyImpactAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for Privacy Impact Assessments."""

    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PrivacyImpactAssessment
        fields = [
            "id",
            "feature_name",
            "description",
            "data_types",
            "risk_level",
            "risk_level_display",
            "risk_description",
            "mitigation_measures",
            "status",
            "status_display",
            "reviewer",
            "review_date",
            "review_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class ConsentRecordSerializer(serializers.ModelSerializer):
    """Serializer for Consent Records."""

    purpose_display = serializers.CharField(source="get_purpose_display", read_only=True)

    class Meta:
        model = ConsentRecord
        fields = [
            "id",
            "user",
            "purpose",
            "purpose_display",
            "granted",
            "granted_at",
            "revoked_at",
            "ip_address",
        ]
        read_only_fields = ("id", "granted_at", "revoked_at", "ip_address")
