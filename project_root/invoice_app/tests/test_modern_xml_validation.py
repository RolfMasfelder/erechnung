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


class TestValidatorCoverageGaps(TestCase):
    """Cover previously-uncovered branches in ZugferdXmlValidator and backends."""

    # ---------- validator.py line 59: explicit backend bypasses _load_schemas ----------

    def test_explicit_backend_sets_backend_directly(self):
        """Passing backend= to constructor skips schema loading (line 59)."""
        backend = NoOpBackend()
        validator = ZugferdXmlValidator(backend=backend)
        self.assertIs(validator._backend, backend)
        # Schemas should remain None — not loaded
        self.assertIsNone(validator.xsd_schema)
        self.assertIsNone(validator.schematron_backend)

    # ---------- validator.py lines 69-71: XSD loading failure ----------

    def test_load_schemas_xsd_exception_is_caught(self):
        """Error loading XSD sets xsd_schema=None (lines 69-71)."""
        from lxml import etree

        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH") as mock_sch,
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", False),
            patch.object(etree, "XMLSchema", side_effect=Exception("bad XSD")),
        ):
            mock_xsd.exists.return_value = True
            mock_sch.exists.return_value = False
            validator = ZugferdXmlValidator()
        self.assertIsNone(validator.xsd_schema)

    # ---------- validator.py lines 80-82: Schematron (Saxon) loading failure ----------

    def test_load_schemas_schematron_exception_is_caught(self):
        """Error initialising SchematronSaxonBackend sets schematron_backend=None (lines 80-82)."""
        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH") as mock_sch,
            patch("invoice_app.utils.xml.validator.ENABLE_SCHEMATRON_VALIDATION", True),
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", False),
            patch("invoice_app.utils.xml.validator.SchematronSaxonBackend", side_effect=Exception("saxon fail")),
        ):
            mock_xsd.exists.return_value = False
            mock_sch.exists.return_value = True
            validator = ZugferdXmlValidator()
        self.assertIsNone(validator.schematron_backend)

    # ---------- validator.py lines 88-91: outer exception in _load_schemas ----------

    def test_load_schemas_outer_exception_handled(self):
        """Outer exception in _load_schemas resets both schemas (lines 88-91)."""
        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH"),
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", False),
        ):
            # Make XSD_PATH.exists() raise to trigger outer except
            mock_xsd.exists.side_effect = Exception("fs error")
            validator = ZugferdXmlValidator()
        self.assertIsNone(validator.xsd_schema)
        self.assertIsNone(validator.schematron_backend)

    # ---------- validator.py lines 102-103: schematron-only backend selection ----------

    def test_select_backend_schematron_only(self):
        """When only schematron_backend is set, uses it directly (lines 102-103)."""
        from unittest.mock import MagicMock

        with (
            patch("invoice_app.utils.xml.validator.XSD_PATH") as mock_xsd,
            patch("invoice_app.utils.xml.validator.SCHEMATRON_XSLT_PATH") as mock_sch,
            patch("invoice_app.utils.xml.validator.ENABLE_SCHEMATRON_VALIDATION", True),
            patch("invoice_app.utils.xml.validator.REQUIRE_VALIDATION_SCHEMAS", False),
            patch("invoice_app.utils.xml.validator.SchematronSaxonBackend") as MockSaxon,
        ):
            mock_xsd.exists.return_value = False
            mock_sch.exists.return_value = True
            fake_backend = MagicMock()
            MockSaxon.return_value = fake_backend
            validator = ZugferdXmlValidator()
        self.assertIs(validator._backend, fake_backend)

    # ---------- validator.py line 136: validate_file error handler ----------

    def test_validate_file_nonexistent_path_returns_error(self):
        """validate_file with a missing path returns an invalid result (line 136)."""
        validator = ZugferdXmlValidator()
        result = validator.validate_file("/nonexistent/path/to/file.xml")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("File error" in e for e in result.errors))

    # ---------- validator.py lines 167-171: validate_file_legacy ----------

    def test_validate_file_legacy_returns_tuple(self):
        """validate_file_legacy wraps validate_file and returns (bool, list) (lines 167-171)."""
        import tempfile

        validator = ZugferdXmlValidator()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<?xml version="1.0"?><test>content</test>')
            temp_path = f.name
        try:
            is_valid, errors = validator.validate_file_legacy(temp_path)
            self.assertIsInstance(is_valid, bool)
            self.assertIsInstance(errors, list)
        finally:
            os.unlink(temp_path)

    # ---------- backends.py line 127: XsdOnlyBackend bytes input ----------

    def test_xsd_only_backend_accepts_bytes(self):
        """XsdOnlyBackend.validate handles bytes input (line 127)."""
        from unittest.mock import MagicMock

        mock_schema = MagicMock()
        mock_schema.validate.return_value = True
        from invoice_app.utils.xml.backends import XsdOnlyBackend

        backend = XsdOnlyBackend(mock_schema)
        result = backend.validate(b'<?xml version="1.0"?><test/>')
        # validate was called with bytes path — no TypeError
        mock_schema.validate.assert_called_once()
        self.assertTrue(result.is_valid)

    # ---------- backends.py lines 134-136: XSD validation errors logged ----------

    def test_xsd_only_backend_collects_errors(self):
        """XsdOnlyBackend adds error entries from error_log when validation fails (lines 134-136)."""
        from unittest.mock import MagicMock, PropertyMock

        from invoice_app.utils.xml.backends import XsdOnlyBackend

        mock_error = MagicMock()
        mock_error.message = "Bad element"

        mock_schema = MagicMock()
        mock_schema.validate.return_value = False
        type(mock_schema).error_log = PropertyMock(return_value=[mock_error])

        backend = XsdOnlyBackend(mock_schema)
        result = backend.validate("<test/>")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Bad element" in e for e in result.errors))

    # ---------- backends.py line 152: SchematronBackend bytes input ----------

    def test_schematron_backend_accepts_bytes(self):
        """SchematronBackend.validate handles bytes input (line 152)."""
        from unittest.mock import MagicMock

        from invoice_app.utils.xml.backends import SchematronBackend

        mock_schematron = MagicMock()
        mock_schematron.validate.return_value = True
        backend = SchematronBackend(mock_schematron)
        result = backend.validate(b"<test/>")
        mock_schematron.validate.assert_called_once()
        self.assertTrue(result.is_valid)

    # ---------- backends.py lines 156-176: SchematronBackend failures and exception ----------

    def test_schematron_backend_collects_errors(self):
        """SchematronBackend adds errors from error_log when validation fails (lines 159-162)."""
        from unittest.mock import MagicMock, PropertyMock

        from invoice_app.utils.xml.backends import SchematronBackend

        mock_error = MagicMock()
        mock_error.message = "Schematron rule failed"

        mock_schematron = MagicMock()
        mock_schematron.validate.return_value = False
        type(mock_schematron).error_log = PropertyMock(return_value=[mock_error])

        backend = SchematronBackend(mock_schematron)
        result = backend.validate("<test/>")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Schematron rule failed" in e for e in result.errors))

    def test_schematron_backend_exception_handler(self):
        """SchematronBackend exception adds error (lines 175-176)."""
        from unittest.mock import MagicMock

        from invoice_app.utils.xml.backends import SchematronBackend

        mock_schematron = MagicMock()
        mock_schematron.validate.side_effect = Exception("parse crash")
        backend = SchematronBackend(mock_schematron)
        result = backend.validate("<test/>")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Schematron" in e for e in result.errors))

    # ---------- backends.py lines 223-225: SchematronSaxonBackend SVRL None ----------

    def test_schematron_saxon_backend_svrl_none(self):
        """SchematronSaxonBackend adds error when XSLT produces None (lines 223-225)."""
        from unittest.mock import MagicMock, patch

        from invoice_app.utils.xml.backends import SchematronSaxonBackend

        with patch("invoice_app.utils.xml.backends.SchematronSaxonBackend.__init__", return_value=None):
            backend = SchematronSaxonBackend.__new__(SchematronSaxonBackend)
            mock_proc = MagicMock()
            mock_executable = MagicMock()
            mock_executable.transform_to_string.return_value = None
            mock_node = MagicMock()
            mock_proc.parse_xml.return_value = mock_node
            backend._proc = mock_proc
            backend._executable = mock_executable

        result = backend.validate("<test/>")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("no output" in e for e in result.errors))

    # ---------- backends.py lines 258-270: _parse_svrl warning (successful-report) ----------

    def test_parse_svrl_successful_report_warning(self):
        """_parse_svrl adds warning from successful-report with flag=warning (lines 258-270)."""
        from unittest.mock import patch

        from invoice_app.utils.xml.backends import SchematronSaxonBackend, ValidationResult

        svrl_xml = """<?xml version="1.0"?>
<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <svrl:successful-report flag="warning" location="/Invoice">
    <svrl:text>Optional field missing</svrl:text>
  </svrl:successful-report>
</svrl:schematron-output>"""

        with patch("invoice_app.utils.xml.backends.SchematronSaxonBackend.__init__", return_value=None):
            backend = SchematronSaxonBackend.__new__(SchematronSaxonBackend)

        result = ValidationResult()
        backend._parse_svrl(svrl_xml, result)
        self.assertTrue(result.is_valid)  # no errors
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("Optional field missing", result.warnings[0])
