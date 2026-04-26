"""
Tests for modernized XML validation system.

This module tests the new pluggable validation backends,
ISO Schematron support, and enhanced error reporting.
"""

import os
import tempfile
from unittest.mock import patch

from django.test import TestCase

from invoice_app.utils.xml import NoOpBackend, ValidationResult, ZugferdXmlValidator


class TestValidationResult(TestCase):
    """Test ValidationResult class functionality."""

    def test_init_defaults(self):
        """Test ValidationResult initialization with defaults."""
        result = ValidationResult()
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.validation_time_ms, 0)
        self.assertEqual(result.backend_used, "unknown")

    def test_add_error(self):
        """Test adding an error marks result as invalid."""
        result = ValidationResult()
        result.add_error("Test error")

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ["Test error"])

    def test_add_warning(self):
        """Test adding a warning doesn't affect validity."""
        result = ValidationResult()
        result.add_warning("Test warning")

        self.assertTrue(result.is_valid)
        self.assertEqual(result.warnings, ["Test warning"])

    def test_merge(self):
        """Test merging validation results."""
        result1 = ValidationResult(is_valid=True, validation_time_ms=100)
        result1.add_warning("Warning 1")

        result2 = ValidationResult(is_valid=False, validation_time_ms=50)
        result2.add_error("Error 1")
        result2.add_warning("Warning 2")

        result1.merge(result2)

        self.assertFalse(result1.is_valid)
        self.assertEqual(result1.errors, ["Error 1"])
        self.assertEqual(result1.warnings, ["Warning 1", "Warning 2"])
        self.assertEqual(result1.validation_time_ms, 150)


class TestNoOpBackend(TestCase):
    """Test No-operation validation backend."""

    def test_noop_validation_returns_error(self):
        """Test NoOp backend returns invalid with error - missing schemas is a failure."""
        backend = NoOpBackend()
        result = backend.validate("<test>xml</test>")

        # NoOp backend should now return invalid with error
        self.assertFalse(result.is_valid)
        self.assertEqual(result.backend_used, "NoOp")
        self.assertGreater(len(result.errors), 0)
        self.assertTrue(any("No validation schemas available" in error for error in result.errors))


class TestZugferdXmlValidator(TestCase):
    """Test modernized ZugferdXmlValidator."""

    def test_initialization_raises_error_when_no_schemas(self):
        """Test validator raises RuntimeError when no schemas available and REQUIRE_VALIDATION_SCHEMAS=True."""
        # Patch the paths where they're actually used (in the validator module)
        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd_path,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH") as mock_sch_path,
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", True),
        ):
            mock_xsd_path.exists.return_value = False
            mock_sch_path.exists.return_value = False

            with self.assertRaises(RuntimeError) as context:
                ZugferdXmlValidator()

            self.assertIn("No validation schemas available", str(context.exception))

    def test_initialization_with_noop_backend_when_allowed(self):
        """Test validator initializes with NoOp backend when REQUIRE_VALIDATION_SCHEMAS=False."""
        # Patch the paths where they're actually used (in the validator module)
        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd_path,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH") as mock_sch_path,
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", False),
        ):
            mock_xsd_path.exists.return_value = False
            mock_sch_path.exists.return_value = False

            validator = ZugferdXmlValidator()
            self.assertEqual(validator._backend.__class__.__name__, "NoOpBackend")

    def test_get_validation_info(self):
        """Test validation info method."""
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
            "backend_type",
            "schemas_loaded",
        ]

        for key in expected_keys:
            self.assertIn(key, info, f"Missing key: {key}")

        # Check that schemas_loaded is a dict with expected keys
        self.assertIsInstance(info["schemas_loaded"], dict)
        self.assertIn("xsd", info["schemas_loaded"])
        self.assertIn("schematron", info["schemas_loaded"])

    def test_validation_result_structure(self):
        """Test that validation returns ValidationResult object."""
        validator = ZugferdXmlValidator()
        result = validator.validate_xml('<?xml version="1.0"?><test>content</test>')

        self.assertIsInstance(result, ValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.validation_time_ms, (int, float))
        self.assertIsInstance(result.backend_used, str)

    def test_legacy_validation_methods(self):
        """Test legacy methods for backward compatibility."""
        validator = ZugferdXmlValidator()

        # Test legacy validate_xml method
        is_valid, errors = validator.validate_xml_legacy('<?xml version="1.0"?><test>content</test>')
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)

        # Test legacy validate_file method with temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<?xml version="1.0"?><test>content</test>')
            temp_path = f.name

        try:
            is_valid, errors = validator.validate_file_legacy(temp_path)
            self.assertIsInstance(is_valid, bool)
            self.assertIsInstance(errors, list)
        finally:
            os.unlink(temp_path)
