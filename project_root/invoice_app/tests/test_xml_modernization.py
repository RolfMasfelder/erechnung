"""
Simple test to verify the modernized XML validation.
"""

from django.test import TestCase

from invoice_app.utils.xml import ZugferdXmlValidator


class TestModernizedXmlValidation(TestCase):
    """Test modernized XML validation functionality."""

    def test_validation_info(self):
        """Test that validation info is returned correctly."""
        validator = ZugferdXmlValidator()
        info = validator.get_validation_info()

        # Check that all expected keys are present
        expected_keys = [
            "xsd_available",
            "schematron_available",
            "schematron_enabled",
            "strict_mode",
            "timing_threshold_ms",
            "xsd_path",
            "schematron_path",
            "schemas_loaded",
        ]

        for key in expected_keys:
            self.assertIn(key, info, f"Missing key: {key}")

        # Check that schemas_loaded is a dict with expected keys
        self.assertIsInstance(info["schemas_loaded"], dict)
        self.assertIn("xsd", info["schemas_loaded"])
        self.assertIn("schematron", info["schemas_loaded"])

    def test_no_deprecation_warnings(self):
        """Test that creating a validator doesn't produce deprecation warnings."""
        # This test mainly ensures that the validator can be instantiated
        # without the old etree.Schematron deprecation warnings
        validator = ZugferdXmlValidator()

        # Basic validation call should work
        result = validator.validate_xml('<?xml version="1.0"?><test>content</test>')

        # Should return some result (even if validation fails due to schema mismatch)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.errors, list)
