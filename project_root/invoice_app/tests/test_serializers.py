"""
Tests for API serializers — covers validation logic, computed fields,
and import serializers.
"""

from decimal import Decimal

from django.test import TestCase

from invoice_app.api.serializers import (
    BusinessPartnerImportRowSerializer,
    BusinessPartnerImportSerializer,
    BusinessPartnerSerializer,
    CompanySerializer,
    InvoiceAllowanceChargeSerializer,
    ProductImportRowSerializer,
    ProductImportSerializer,
    ProductSerializer,
)
from invoice_app.tests.factories import (
    CompanyFactory,
    CountryFactory,
    CountryTaxRateFactory,
    InvoiceAllowanceFactory,
    InvoiceChargeFactory,
    InvoiceLineFactory,
    ProductFactory,
)


class CompanySerializerValidationTests(TestCase):
    """Test CompanySerializer BR-CO-26 validation."""

    def test_valid_with_vat_id(self):
        """Company with vat_id passes validation."""
        company = CompanyFactory.build()
        data = CompanySerializer(company).data
        data["vat_id"] = "DE123456789"
        data["commercial_register"] = ""
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("id", None)
        data.pop("logo", None)
        serializer = CompanySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_with_commercial_register(self):
        """Company with commercial_register passes validation."""
        company = CompanyFactory.build()
        data = CompanySerializer(company).data
        data["vat_id"] = ""
        data["commercial_register"] = "HRB 12345"
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("id", None)
        data.pop("logo", None)
        serializer = CompanySerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_without_vat_or_register(self):
        """Company without vat_id or commercial_register fails BR-CO-26."""
        company = CompanyFactory.build()
        data = CompanySerializer(company).data
        data["vat_id"] = ""
        data["commercial_register"] = ""
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("id", None)
        data.pop("logo", None)
        serializer = CompanySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_update_keeps_existing_vat_id(self):
        """Updating a company keeps existing vat_id for BR-CO-26 check."""
        company = CompanyFactory(vat_id="DE999888777")
        serializer = CompanySerializer(company, data={"name": "Updated Name"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class BusinessPartnerSerializerTests(TestCase):
    """Test BusinessPartnerSerializer validation."""

    def test_valid_vat_id_accepted(self):
        """Valid EU VAT ID passes validation."""
        country = CountryFactory()
        serializer = BusinessPartnerSerializer(
            data={
                "company_name": "Test GmbH",
                "partner_type": "BUSINESS",
                "vat_id": "DE123456789",
                "address_line1": "Str. 1",
                "postal_code": "12345",
                "city": "Berlin",
                "country": country.code,
                "is_customer": True,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_vat_id_too_short(self):
        """VAT ID shorter than 5 chars is rejected."""
        country = CountryFactory()
        serializer = BusinessPartnerSerializer(
            data={
                "company_name": "Test GmbH",
                "partner_type": "BUSINESS",
                "vat_id": "DE1",
                "address_line1": "Str. 1",
                "postal_code": "12345",
                "city": "Berlin",
                "country": country.code,
                "is_customer": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("vat_id", serializer.errors)
        self.assertIn("zu kurz", str(serializer.errors["vat_id"]))

    def test_vat_id_invalid_format(self):
        """VAT ID with valid country prefix but wrong number format is rejected."""
        country = CountryFactory()
        serializer = BusinessPartnerSerializer(
            data={
                "company_name": "Test GmbH",
                "partner_type": "BUSINESS",
                "vat_id": "DE12345",  # DE requires exactly 9 digits
                "address_line1": "Str. 1",
                "postal_code": "12345",
                "city": "Berlin",
                "country": country.code,
                "is_customer": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("vat_id", serializer.errors)
        self.assertIn("Ungültiges Format", str(serializer.errors["vat_id"]))

    def test_empty_vat_id_allowed(self):
        """Empty VAT ID is accepted (optional field)."""
        country = CountryFactory()
        serializer = BusinessPartnerSerializer(
            data={
                "company_name": "Test GmbH",
                "partner_type": "BUSINESS",
                "vat_id": "",
                "address_line1": "Str. 1",
                "postal_code": "12345",
                "city": "Berlin",
                "country": country.code,
                "is_customer": True,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ProductSerializerTaxRateValidationTests(TestCase):
    """Test ProductSerializer validate_default_tax_rate."""

    def test_valid_tax_rate_accepted(self):
        """Tax rate matching country rates passes."""
        country = CountryFactory()
        CompanyFactory(country=country.name, is_active=True)
        CountryTaxRateFactory(country=country, rate=Decimal("19.00"), rate_type="STANDARD")
        CountryTaxRateFactory(country=country, rate=Decimal("7.00"), rate_type="REDUCED")

        product = ProductFactory.build(default_tax_rate=Decimal("19.00"))
        data = ProductSerializer(product).data
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("created_by", None)
        # Remove read-only computed fields
        for f in ("profit_margin", "is_in_stock", "needs_restock", "current_price"):
            data.pop(f, None)
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_tax_rate_rejected(self):
        """Tax rate not matching any country rate is rejected."""
        country = CountryFactory()
        CompanyFactory(country=country.code, is_active=True)
        CountryTaxRateFactory(country=country, rate=Decimal("19.00"), rate_type="STANDARD")
        CountryTaxRateFactory(country=country, rate=Decimal("7.00"), rate_type="REDUCED")

        product = ProductFactory.build(default_tax_rate=Decimal("25.00"))
        data = ProductSerializer(product).data
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("created_by", None)
        for f in ("profit_margin", "is_in_stock", "needs_restock", "current_price"):
            data.pop(f, None)
        serializer = ProductSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("default_tax_rate", serializer.errors)
        self.assertIn("Ungültiger MwSt.-Satz", str(serializer.errors["default_tax_rate"]))

    def test_no_active_company_skips_validation(self):
        """If no active company, any tax rate passes."""
        product = ProductFactory.build(default_tax_rate=Decimal("99.00"))
        data = ProductSerializer(product).data
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("created_by", None)
        for f in ("profit_margin", "is_in_stock", "needs_restock", "current_price"):
            data.pop(f, None)
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_no_country_match_skips_validation(self):
        """If company country doesn't match any Country, tax rate passes."""
        CompanyFactory(country="Nonexistent", is_active=True)
        product = ProductFactory.build(default_tax_rate=Decimal("99.00"))
        data = ProductSerializer(product).data
        data.pop("id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        data.pop("created_by", None)
        for f in ("profit_margin", "is_in_stock", "needs_restock", "current_price"):
            data.pop(f, None)
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class InvoiceAllowanceChargeSerializerTests(TestCase):
    """Test InvoiceAllowanceChargeSerializer computed fields."""

    def test_header_level_allowance(self):
        """Header-level A/C has is_line_level=False."""
        allowance = InvoiceAllowanceFactory()
        data = InvoiceAllowanceChargeSerializer(allowance).data
        self.assertFalse(data["is_line_level"])

    def test_line_level_allowance(self):
        """Line-level A/C has is_line_level=True."""
        line = InvoiceLineFactory()
        charge = InvoiceChargeFactory(invoice=line.invoice, invoice_line=line)
        data = InvoiceAllowanceChargeSerializer(charge).data
        self.assertTrue(data["is_line_level"])


# =============================================================================
# Import Serializers
# =============================================================================


class BusinessPartnerImportRowSerializerTests(TestCase):
    """Test BusinessPartnerImportRowSerializer validation."""

    def setUp(self):
        self.country = CountryFactory()

    def test_valid_minimal_data(self):
        serializer = BusinessPartnerImportRowSerializer(
            data={
                "company_name": "Import GmbH",
                "address_line1": "Importstr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": self.country.code,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_country_code(self):
        serializer = BusinessPartnerImportRowSerializer(
            data={
                "company_name": "Import GmbH",
                "address_line1": "Importstr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": "ZZ",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("country_code", serializer.errors)
        self.assertIn("nicht gefunden", str(serializer.errors["country_code"]))

    def test_vat_id_too_short(self):
        serializer = BusinessPartnerImportRowSerializer(
            data={
                "company_name": "Import GmbH",
                "address_line1": "Importstr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": self.country.code,
                "vat_id": "AB1",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("vat_id", serializer.errors)

    def test_vat_id_invalid_format(self):
        serializer = BusinessPartnerImportRowSerializer(
            data={
                "company_name": "Import GmbH",
                "address_line1": "Importstr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": self.country.code,
                "vat_id": "DE12345",  # DE requires exactly 9 digits
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("vat_id", serializer.errors)
        self.assertIn("Ungültiges Format", str(serializer.errors["vat_id"]))

    def test_valid_vat_id(self):
        serializer = BusinessPartnerImportRowSerializer(
            data={
                "company_name": "Import GmbH",
                "address_line1": "Importstr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": self.country.code,
                "vat_id": "DE123456789",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class BusinessPartnerImportSerializerTests(TestCase):
    """Test BusinessPartnerImportSerializer."""

    def test_empty_rows_rejected(self):
        serializer = BusinessPartnerImportSerializer(data={"rows": []})
        self.assertFalse(serializer.is_valid())
        self.assertIn("rows", serializer.errors)

    def test_valid_rows_accepted(self):
        country = CountryFactory()
        serializer = BusinessPartnerImportSerializer(
            data={
                "rows": [
                    {
                        "company_name": "Firma A",
                        "address_line1": "Str. 1",
                        "postal_code": "12345",
                        "city": "Berlin",
                        "country_code": country.code,
                    }
                ],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ProductImportRowSerializerTests(TestCase):
    """Test ProductImportRowSerializer validation and field mapping."""

    def test_valid_minimal(self):
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "9.99"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_price_must_be_positive(self):
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "0"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("base_price", serializer.errors)

    def test_negative_price_rejected(self):
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "-5.00"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("base_price", serializer.errors)

    def test_tax_rate_mapped_to_default_tax_rate(self):
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "10.00", "tax_rate": "19.00"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("default_tax_rate", serializer.validated_data)
        self.assertNotIn("tax_rate", serializer.validated_data)

    def test_reorder_level_mapped_to_minimum_stock(self):
        serializer = ProductImportRowSerializer(
            data={"name": "Widget", "base_price": "10.00", "reorder_level": "5.000"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("minimum_stock", serializer.validated_data)
        self.assertNotIn("reorder_level", serializer.validated_data)

    def test_null_tax_rate_removed(self):
        """tax_rate=None is cleaned up, not mapped."""
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "10.00", "tax_rate": None})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("tax_rate", serializer.validated_data)
        self.assertNotIn("default_tax_rate", serializer.validated_data)

    def test_null_reorder_level_removed(self):
        serializer = ProductImportRowSerializer(data={"name": "Widget", "base_price": "10.00", "reorder_level": None})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("reorder_level", serializer.validated_data)
        self.assertNotIn("minimum_stock", serializer.validated_data)

    def test_invalid_fields_filtered(self):
        """Fields not in valid_fields set are removed."""
        serializer = ProductImportRowSerializer(
            data={
                "name": "Widget",
                "base_price": "10.00",
                "category": "Electronics",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("category", serializer.validated_data)

    def test_empty_strings_filtered(self):
        """Empty string values are removed from output."""
        serializer = ProductImportRowSerializer(
            data={
                "name": "Widget",
                "base_price": "10.00",
                "product_code": "",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("product_code", serializer.validated_data)


class ProductImportSerializerTests(TestCase):
    """Test ProductImportSerializer."""

    def test_empty_rows_rejected(self):
        serializer = ProductImportSerializer(data={"rows": []})
        self.assertFalse(serializer.is_valid())
        self.assertIn("rows", serializer.errors)

    def test_valid_rows_accepted(self):
        serializer = ProductImportSerializer(
            data={
                "rows": [{"name": "Product A", "base_price": "19.99"}],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
