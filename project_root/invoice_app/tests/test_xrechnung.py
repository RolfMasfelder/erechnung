"""
Tests for XRechnung (B2G) support.

Covers:
- Leitweg-ID validation (format + Modulo-97 check digit)
- BusinessPartner model: GOVERNMENT requires leitweg_id
- Serializer validation: leitweg_id required for GOVERNMENT
- InvoiceSerializer: auto-fill buyer_reference from leitweg_id
- XRechnung profile in PROFILE_MAP
- XML generation with XRECHNUNG profile
"""

import pytest
from django.core.exceptions import ValidationError

from invoice_app.models import BusinessPartner
from invoice_app.models.business_partner import validate_leitweg_id
from invoice_app.tests.factories import (
    BusinessPartnerFactory,
    CompanyFactory,
    CountryFactory,
)
from invoice_app.utils.xml.constants import PROFILE_MAP


# ── Leitweg-ID Validator ────────────────────────────────────────────────────


class TestLeitwegIdValidator:
    """Tests for the Leitweg-ID format and check digit validation."""

    def test_valid_leitweg_id(self):
        """Standard Leitweg-ID with valid check digit should pass."""
        # 04011000-1234512345-06
        # Numeric: 04011000 + 1234512345 = "040110001234512345"
        # 40110001234512345 mod 97 = ?
        # Let's compute: 40110001234512345 % 97
        # We need to find a valid one. Let's construct:
        # grob=04011000, fein=12345
        numeric_str = "0401100012345"
        check = 98 - (int(numeric_str) % 97)
        leitweg = f"04011000-12345-{check:02d}"
        validate_leitweg_id(leitweg)  # Should not raise

    def test_valid_leitweg_id_with_letters(self):
        """Leitweg-ID with alphanumeric Feinadressierung."""
        # grob=991, fein=AB => numeric = "991" + "1011" = "9911011"
        numeric_str = "9911011"
        check = 98 - (int(numeric_str) % 97)
        leitweg = f"991-AB-{check:02d}"
        validate_leitweg_id(leitweg)

    def test_invalid_format_missing_parts(self):
        """Leitweg-ID with missing parts should fail."""
        with pytest.raises(ValidationError, match="Ungültiges Leitweg-ID Format"):
            validate_leitweg_id("12345")

    def test_invalid_format_no_dashes(self):
        """Leitweg-ID without dashes should fail."""
        with pytest.raises(ValidationError, match="Ungültiges Leitweg-ID Format"):
            validate_leitweg_id("04011000123451234506")

    def test_invalid_format_grob_too_short(self):
        """Grobadressierung with less than 2 digits should fail."""
        with pytest.raises(ValidationError, match="Ungültiges Leitweg-ID Format"):
            validate_leitweg_id("1-ABC-06")

    def test_invalid_format_grob_too_long(self):
        """Grobadressierung with more than 12 digits should fail."""
        with pytest.raises(ValidationError, match="Ungültiges Leitweg-ID Format"):
            validate_leitweg_id("1234567890123-ABC-06")

    def test_invalid_format_fein_empty(self):
        """Empty Feinadressierung should fail."""
        with pytest.raises(ValidationError, match="Ungültiges Leitweg-ID Format"):
            validate_leitweg_id("04011000--06")

    def test_invalid_check_digit(self):
        """Wrong check digit should fail with specific error."""
        # Use a known-good Leitweg-ID but change the check digit
        numeric_str = "0401100012345"
        correct_check = 98 - (int(numeric_str) % 97)
        wrong_check = (correct_check + 1) % 100
        leitweg = f"04011000-12345-{wrong_check:02d}"
        with pytest.raises(ValidationError, match="Prüfziffer ungültig"):
            validate_leitweg_id(leitweg)

    def test_empty_string_allowed_by_model(self):
        """Empty string is allowed (blank=True) — validator not called."""
        # The validator itself would reject empty, but Django fields with blank=True
        # skip validators for empty values. This tests the model field behavior.
        partner = BusinessPartnerFactory.build(partner_type="BUSINESS", leitweg_id="")
        # Should not raise — blank is allowed for non-GOVERNMENT
        assert partner.leitweg_id == ""


# ── BusinessPartner Model ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBusinessPartnerLeitwegId:
    """Tests for leitweg_id on the BusinessPartner model."""

    def _valid_leitweg_id(self):
        """Helper to generate a valid Leitweg-ID."""
        numeric_str = "0401100012345"
        check = 98 - (int(numeric_str) % 97)
        return f"04011000-12345-{check:02d}"

    def test_government_partner_with_leitweg_id(self):
        """GOVERNMENT partner with valid Leitweg-ID should save."""
        partner = BusinessPartnerFactory(
            partner_type="GOVERNMENT",
            leitweg_id=self._valid_leitweg_id(),
        )
        assert partner.pk is not None
        assert partner.leitweg_id == self._valid_leitweg_id()

    def test_government_partner_without_leitweg_id_fails_clean(self):
        """GOVERNMENT partner without Leitweg-ID should fail clean()."""
        partner = BusinessPartnerFactory.build(
            partner_type="GOVERNMENT",
            leitweg_id="",
        )
        with pytest.raises(ValidationError, match="leitweg_id"):
            partner.clean()

    def test_business_partner_without_leitweg_id_ok(self):
        """BUSINESS partner without Leitweg-ID should pass clean()."""
        partner = BusinessPartnerFactory.build(partner_type="BUSINESS", leitweg_id="")
        partner.clean()  # Should not raise

    def test_leitweg_id_max_length(self):
        """Leitweg-ID field max_length is 46."""
        field = BusinessPartner._meta.get_field("leitweg_id")
        assert field.max_length == 46


# ── BusinessPartner Serializer ──────────────────────────────────────────────


@pytest.mark.django_db
class TestBusinessPartnerSerializerXRechnung:
    """Tests for leitweg_id validation in the BusinessPartner serializer."""

    def _valid_leitweg_id(self):
        numeric_str = "0401100012345"
        check = 98 - (int(numeric_str) % 97)
        return f"04011000-12345-{check:02d}"

    def test_government_partner_requires_leitweg_id(self):
        """Creating GOVERNMENT partner without leitweg_id should fail."""
        from invoice_app.api.serializers import BusinessPartnerSerializer

        country = CountryFactory()
        data = {
            "partner_type": "GOVERNMENT",
            "company_name": "Bundesamt für Test",
            "address_line1": "Teststraße 1",
            "postal_code": "10117",
            "city": "Berlin",
            "country": country.pk,
            "vat_id": "DE123456789",
        }
        serializer = BusinessPartnerSerializer(data=data)
        assert not serializer.is_valid()
        assert "leitweg_id" in serializer.errors

    def test_government_partner_with_leitweg_id_valid(self):
        """Creating GOVERNMENT partner with valid leitweg_id should succeed."""
        from invoice_app.api.serializers import BusinessPartnerSerializer

        country = CountryFactory()
        data = {
            "partner_type": "GOVERNMENT",
            "company_name": "Bundesamt für Test",
            "address_line1": "Teststraße 1",
            "postal_code": "10117",
            "city": "Berlin",
            "country": country.pk,
            "vat_id": "DE123456789",
            "leitweg_id": self._valid_leitweg_id(),
        }
        serializer = BusinessPartnerSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_business_partner_without_leitweg_id_valid(self):
        """BUSINESS partner without leitweg_id should be valid."""
        from invoice_app.api.serializers import BusinessPartnerSerializer

        country = CountryFactory()
        data = {
            "partner_type": "BUSINESS",
            "company_name": "Firma GmbH",
            "address_line1": "Teststraße 1",
            "postal_code": "10117",
            "city": "Berlin",
            "country": country.pk,
            "vat_id": "DE123456789",
        }
        serializer = BusinessPartnerSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


# ── Invoice Serializer: buyer_reference Auto-Fill ────────────────────────────


@pytest.mark.django_db
class TestInvoiceBuyerReferenceAutoFill:
    """Tests for auto-filling buyer_reference from leitweg_id."""

    def _valid_leitweg_id(self):
        numeric_str = "0401100012345"
        check = 98 - (int(numeric_str) % 97)
        return f"04011000-12345-{check:02d}"

    def test_auto_fill_buyer_reference_for_government(self):
        """buyer_reference should auto-fill from leitweg_id for GOVERNMENT partners."""
        from invoice_app.api.serializers import InvoiceSerializer

        company = CompanyFactory()
        partner = BusinessPartnerFactory(
            partner_type="GOVERNMENT",
            leitweg_id=self._valid_leitweg_id(),
        )
        data = {
            "company": company.pk,
            "business_partner": partner.pk,
            "invoice_type": "INVOICE",
            "issue_date": "2026-04-15",
            "due_date": "2026-05-15",
            "currency": "EUR",
            "subtotal": "1000.00",
            "tax_amount": "190.00",
            "total_amount": "1190.00",
        }
        serializer = InvoiceSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["buyer_reference"] == self._valid_leitweg_id()

    def test_no_auto_fill_when_buyer_reference_set(self):
        """buyer_reference should NOT be overwritten if explicitly set."""
        from invoice_app.api.serializers import InvoiceSerializer

        company = CompanyFactory()
        partner = BusinessPartnerFactory(
            partner_type="GOVERNMENT",
            leitweg_id=self._valid_leitweg_id(),
        )
        data = {
            "company": company.pk,
            "business_partner": partner.pk,
            "invoice_type": "INVOICE",
            "issue_date": "2026-04-15",
            "due_date": "2026-05-15",
            "currency": "EUR",
            "subtotal": "1000.00",
            "tax_amount": "190.00",
            "total_amount": "1190.00",
            "buyer_reference": "CUSTOM-REF-001",
        }
        serializer = InvoiceSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["buyer_reference"] == "CUSTOM-REF-001"

    def test_no_auto_fill_for_business_partner(self):
        """buyer_reference should NOT auto-fill for BUSINESS partners."""
        from invoice_app.api.serializers import InvoiceSerializer

        company = CompanyFactory()
        partner = BusinessPartnerFactory(partner_type="BUSINESS")
        data = {
            "company": company.pk,
            "business_partner": partner.pk,
            "invoice_type": "INVOICE",
            "issue_date": "2026-04-15",
            "due_date": "2026-05-15",
            "currency": "EUR",
            "subtotal": "1000.00",
            "tax_amount": "190.00",
            "total_amount": "1190.00",
        }
        serializer = InvoiceSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data.get("buyer_reference", "") == ""


# ── PROFILE_MAP ─────────────────────────────────────────────────────────────


class TestXRechnungProfile:
    """Tests for XRechnung profile in PROFILE_MAP."""

    def test_xrechnung_profile_exists(self):
        """XRECHNUNG profile should be in PROFILE_MAP."""
        assert "XRECHNUNG" in PROFILE_MAP

    def test_xrechnung_profile_uri(self):
        """XRechnung profile URI should match KoSIT spec."""
        expected = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
        assert PROFILE_MAP["XRECHNUNG"] == expected

    def test_all_profiles_present(self):
        """All expected profiles should be present."""
        expected_profiles = {"MINIMUM", "BASICWL", "BASIC", "COMFORT", "EXTENDED", "XRECHNUNG"}
        assert set(PROFILE_MAP.keys()) == expected_profiles


# ── XML Generation ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestXRechnungXMLGeneration:
    """Tests for XML generation with XRECHNUNG profile."""

    def _valid_leitweg_id(self):
        numeric_str = "0401100012345"
        check = 98 - (int(numeric_str) % 97)
        return f"04011000-12345-{check:02d}"

    def test_xrechnung_xml_has_correct_profile_uri(self):
        """Generated XML should contain the XRechnung profile URI."""
        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        generator = ZugferdXmlGenerator(profile="XRECHNUNG")
        invoice_data = {
            "number": "XR-2026-001",
            "type_code": "380",
            "date": "20260415",
            "due_date": "20260515",
            "buyer_reference": self._valid_leitweg_id(),
            "seller_reference": "",
            "currency": "EUR",
            "subtotal": 1000.0,
            "tax_amount": 190.0,
            "total_amount": 1190.0,
            "company": {
                "name": "Test GmbH",
                "legal_name": "Test GmbH",
                "tax_id": "DE123456789",
                "vat_id": "DE123456789",
                "commercial_register": "HRB 12345",
                "street_name": "Teststraße 1",
                "city_name": "Berlin",
                "postcode_code": "10117",
                "country_id": "DE",
                "email": "test@test.de",
                "iban": "DE89370400440532013000",
                "bic": "COBADEFFXXX",
                "bank_name": "Commerzbank",
            },
            "customer": {
                "name": "Bundesamt für Test",
                "tax_id": "",
                "vat_id": "DE987654321",
                "street_name": "Amtstraße 1",
                "city_name": "Berlin",
                "postcode_code": "10115",
                "country_id": "DE",
                "email": "amt@bund.de",
            },
            "items": [
                {
                    "product_name": "Beratung",
                    "quantity": 10.0,
                    "price": 100.0,
                    "tax_rate": 19.0,
                    "tax_category_code": "S",
                    "tax_exemption_reason": "",
                    "product_code": "BER-001",
                    "unit_of_measure": "HUR",
                    "line_total": 1000.0,
                    "discount_amount": 0.0,
                    "discount_reason": "",
                },
            ],
            "allowances_charges": [],
            "allowance_total": 0.0,
            "charge_total": 0.0,
            "additional_documents": [],
        }

        xml_content = generator.generate_xml(invoice_data)
        assert "urn:xeinkauf.de:kosit:xrechnung_3.0" in xml_content

    def test_xrechnung_xml_contains_buyer_reference(self):
        """XRechnung XML should contain the buyer_reference (BT-10)."""
        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        leitweg = self._valid_leitweg_id()
        generator = ZugferdXmlGenerator(profile="XRECHNUNG")
        invoice_data = {
            "number": "XR-2026-002",
            "type_code": "380",
            "date": "20260415",
            "due_date": "20260515",
            "buyer_reference": leitweg,
            "seller_reference": "",
            "currency": "EUR",
            "subtotal": 500.0,
            "tax_amount": 95.0,
            "total_amount": 595.0,
            "company": {
                "name": "Test GmbH",
                "legal_name": "Test GmbH",
                "tax_id": "DE123456789",
                "vat_id": "DE123456789",
                "commercial_register": "HRB 12345",
                "street_name": "Teststraße 1",
                "city_name": "Berlin",
                "postcode_code": "10117",
                "country_id": "DE",
                "email": "test@test.de",
                "iban": "DE89370400440532013000",
                "bic": "COBADEFFXXX",
                "bank_name": "Commerzbank",
            },
            "customer": {
                "name": "Stadtverwaltung",
                "tax_id": "",
                "vat_id": "DE111222333",
                "street_name": "Rathausplatz 1",
                "city_name": "München",
                "postcode_code": "80331",
                "country_id": "DE",
                "email": "stadt@muenchen.de",
            },
            "items": [
                {
                    "product_name": "IT-Service",
                    "quantity": 5.0,
                    "price": 100.0,
                    "tax_rate": 19.0,
                    "tax_category_code": "S",
                    "tax_exemption_reason": "",
                    "product_code": "IT-001",
                    "unit_of_measure": "HUR",
                    "line_total": 500.0,
                    "discount_amount": 0.0,
                    "discount_reason": "",
                },
            ],
            "allowances_charges": [],
            "allowance_total": 0.0,
            "charge_total": 0.0,
            "additional_documents": [],
        }

        xml_content = generator.generate_xml(invoice_data)
        assert leitweg in xml_content
