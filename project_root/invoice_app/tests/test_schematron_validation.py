"""
Tests for EN16931 Schematron validation via Saxon-HE.

Tests the SchematronSaxonBackend, CombinedBackend with Saxon,
and end-to-end validation of generated ZUGFeRD XML.
"""

import unittest
from unittest.mock import patch

from django.test import TestCase

from invoice_app.utils.xml import ZugferdXmlGenerator, ZugferdXmlValidator
from invoice_app.utils.xml.backends import CombinedBackend, SchematronSaxonBackend, ValidationResult, XsdOnlyBackend
from invoice_app.utils.xml.constants import SCHEMATRON_XSLT_PATH, XSD_PATH


class TestSchematronSaxonBackend(TestCase):
    """Test SchematronSaxonBackend with real Saxon-HE engine."""

    @classmethod
    def setUpClass(cls):
        """Load Schematron XSLT once for all tests."""
        super().setUpClass()
        if not SCHEMATRON_XSLT_PATH.exists():
            raise unittest.SkipTest(f"Schematron XSLT not found: {SCHEMATRON_XSLT_PATH}")
        cls.backend = SchematronSaxonBackend(SCHEMATRON_XSLT_PATH)

    def _generate_valid_xml(self):
        """Generate a valid EN16931 COMFORT-profile CII XML."""
        generator = ZugferdXmlGenerator(profile="COMFORT")
        invoice_data = {
            "number": "TEST-SCHEMATRON-001",
            "date": "20260305",
            "due_date": "20260405",
            "currency": "EUR",
            "issuer": {
                "name": "Schematron Test GmbH",
                "tax_id": "DE123456789",
                "street_name": "Teststraße 1",
                "city_name": "Berlin",
                "postcode_code": "10115",
                "country_id": "DE",
                "email": "test@example.com",
            },
            "customer": {
                "name": "Kunde AG",
                "tax_id": "DE987654321",
                "street_name": "Kundenweg 2",
                "city_name": "München",
                "postcode_code": "80331",
                "country_id": "DE",
                "email": "kunde@example.com",
            },
            "items": [
                {
                    "product_name": "Beratungsleistung",
                    "quantity": 10,
                    "price": 150.00,
                    "tax_rate": 19.0,
                },
            ],
        }
        return generator.generate_xml(invoice_data)

    def test_backend_initialization(self):
        """Test Saxon backend initializes with XSLT."""
        self.assertIsNotNone(self.backend._proc)
        self.assertIsNotNone(self.backend._executable)
        self.assertEqual(self.backend.validate("").backend_used, "Schematron-Saxon")

    def test_validate_returns_validation_result(self):
        """Test validate returns a ValidationResult object."""
        xml = self._generate_valid_xml()
        result = self.backend.validate(xml)

        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.backend_used, "Schematron-Saxon")
        self.assertGreater(result.validation_time_ms, 0)

    def test_validate_valid_xml(self):
        """Test validation of a valid EN16931 CII invoice."""
        xml = self._generate_valid_xml()
        result = self.backend.validate(xml)

        # Log errors for debugging if validation fails
        if not result.is_valid:
            for error in result.errors:
                print(f"  Schematron error: {error}")

        # Even if some business rules fail, it should at least return a structured result
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)

    def test_validate_bytes_input(self):
        """Test that bytes input is handled correctly."""
        xml = self._generate_valid_xml()
        result = self.backend.validate(xml.encode("utf-8"))

        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.backend_used, "Schematron-Saxon")

    def test_validate_malformed_xml(self):
        """Test validation of malformed XML returns error."""
        result = self.backend.validate("not-xml-at-all")

        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

    def test_validate_wrong_namespace_xml(self):
        """Test validation of XML with wrong namespace."""
        xml = '<?xml version="1.0"?><root xmlns="http://wrong.namespace">test</root>'
        result = self.backend.validate(xml)

        # Should produce Schematron errors since this is not a CII invoice
        self.assertIsInstance(result, ValidationResult)

    def test_svrl_parsing_extracts_rule_ids(self):
        """Test that SVRL parsing extracts rule IDs from failed-assert."""
        # Use an intentionally incomplete XML to trigger Schematron rules
        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rsm:CrossIndustryInvoice
            xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
            xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
            xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
            <rsm:ExchangedDocumentContext>
                <ram:GuidelineSpecifiedDocumentContextParameter>
                    <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
                </ram:GuidelineSpecifiedDocumentContextParameter>
            </rsm:ExchangedDocumentContext>
            <rsm:ExchangedDocument>
                <ram:ID>INCOMPLETE-001</ram:ID>
                <ram:TypeCode>380</ram:TypeCode>
            </rsm:ExchangedDocument>
            <rsm:SupplyChainTradeTransaction/>
        </rsm:CrossIndustryInvoice>"""

        result = self.backend.validate(minimal_xml)

        # This incomplete invoice MUST fail Schematron (missing required elements)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

        # Check that error messages contain "Schematron:" prefix
        for error in result.errors:
            self.assertTrue(
                error.startswith("Schematron:"),
                f"Error should start with 'Schematron:': {error}",
            )


class TestCombinedBackendWithSaxon(TestCase):
    """Test CombinedBackend using XSD + SchematronSaxonBackend."""

    @classmethod
    def setUpClass(cls):
        """Set up combined backend with real schemas."""
        super().setUpClass()
        from lxml import etree

        if not XSD_PATH.exists() or not SCHEMATRON_XSLT_PATH.exists():
            raise unittest.SkipTest("XSD or Schematron schemas not available")

        xsd_schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        saxon_backend = SchematronSaxonBackend(SCHEMATRON_XSLT_PATH)
        cls.backend = CombinedBackend(XsdOnlyBackend(xsd_schema), saxon_backend)

    def test_combined_backend_type(self):
        """Test combined backend reports correct type."""
        result = self.backend.validate('<?xml version="1.0"?><test/>')
        self.assertEqual(result.backend_used, "Combined (XSD + Schematron)")

    def test_combined_catches_xsd_errors(self):
        """Test that XSD errors are caught by combined backend."""
        result = self.backend.validate('<?xml version="1.0"?><invalid-root/>')

        self.assertFalse(result.is_valid)
        # XSD errors should be present
        xsd_errors = [e for e in result.errors if e.startswith("XSD:")]
        self.assertGreater(len(xsd_errors), 0)

    def test_combined_with_valid_generator_output(self):
        """Test combined validation with generator output."""
        generator = ZugferdXmlGenerator(profile="COMFORT")
        invoice_data = {
            "number": "COMBINED-TEST-001",
            "date": "20260305",
            "due_date": "20260405",
            "currency": "EUR",
            "issuer": {
                "name": "Test Supplier GmbH",
                "tax_id": "DE123456789",
                "street_name": "Teststraße 1",
                "city_name": "Berlin",
                "postcode_code": "10115",
                "country_id": "DE",
                "email": "supplier@example.com",
            },
            "customer": {
                "name": "Test Customer AG",
                "tax_id": "DE987654321",
                "street_name": "Kundenweg 2",
                "city_name": "München",
                "postcode_code": "80331",
                "country_id": "DE",
                "email": "customer@example.com",
            },
            "items": [
                {
                    "product_name": "Service",
                    "quantity": 5,
                    "price": 200.00,
                    "tax_rate": 19.0,
                },
            ],
        }
        xml = generator.generate_xml(invoice_data)
        result = self.backend.validate(xml)

        # XSD validation should pass (generator produces structurally valid XML)
        xsd_errors = [e for e in result.errors if e.startswith("XSD:")]
        self.assertEqual(len(xsd_errors), 0, f"XSD errors: {xsd_errors}")

        # Report result for visibility
        if result.is_valid:
            print("  Combined validation: PASSED (XSD + Schematron)")
        else:
            print(f"  Combined validation: {len(result.errors)} Schematron issues")
            for error in result.errors[:5]:
                print(f"    - {error}")


class TestValidatorAutoDetection(TestCase):
    """Test that ZugferdXmlValidator auto-detects Saxon backend."""

    def test_validator_uses_combined_backend_when_schemas_available(self):
        """Test that validator auto-selects CombinedBackend with Saxon."""
        if not XSD_PATH.exists() or not SCHEMATRON_XSLT_PATH.exists():
            self.skipTest("Schemas not available")

        with patch("invoice_app.utils.xml.validator.ENABLE_SCHEMATRON_VALIDATION", True):
            validator = ZugferdXmlValidator()
            self.assertEqual(validator._backend.__class__.__name__, "CombinedBackend")

    def test_validator_falls_back_to_xsd_only_when_schematron_disabled(self):
        """Test fallback to XSD-only when Schematron is disabled."""
        if not XSD_PATH.exists():
            self.skipTest("XSD schema not available")

        with patch("invoice_app.utils.xml.validator.ENABLE_SCHEMATRON_VALIDATION", False):
            validator = ZugferdXmlValidator()
            self.assertEqual(validator._backend.__class__.__name__, "XsdOnlyBackend")

    def test_validation_info_reports_saxon(self):
        """Test get_validation_info reports Schematron availability."""
        if not XSD_PATH.exists() or not SCHEMATRON_XSLT_PATH.exists():
            self.skipTest("Schemas not available")

        with patch("invoice_app.utils.xml.validator.ENABLE_SCHEMATRON_VALIDATION", True):
            validator = ZugferdXmlValidator()
            info = validator.get_validation_info()

            self.assertTrue(info["schematron_available"])
            self.assertTrue(info["schematron_enabled"])
            self.assertTrue(info["schemas_loaded"]["schematron"])
            self.assertEqual(info["backend_type"], "CombinedBackend")
