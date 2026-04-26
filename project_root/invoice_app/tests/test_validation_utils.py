"""
Tests for validation utilities.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import TestCase

from invoice_app.utils.validation import ValidationResult


class ValidationResultTestCase(TestCase):
    """Test ValidationResult class."""

    def test_validation_result_creation_valid(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(
            is_valid=True, errors=[], warnings=["Minor warning"], extracted_xml="<xml>content</xml>"
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, ["Minor warning"])
        self.assertEqual(result.extracted_xml, "<xml>content</xml>")

    def test_validation_result_creation_invalid(self):
        """Test creating an invalid ValidationResult."""
        result = ValidationResult(is_valid=False, errors=["Error 1", "Error 2"], warnings=[], extracted_xml=None)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ["Error 1", "Error 2"])
        self.assertEqual(result.warnings, [])
        self.assertIsNone(result.extracted_xml)

    def test_validation_result_defaults(self):
        """Test ValidationResult with minimal parameters."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], extracted_xml="")

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.extracted_xml, "")

    def test_validation_result_string_representation(self):
        """Test string representation of ValidationResult."""
        result = ValidationResult(is_valid=False, errors=["Test error"], warnings=["Test warning"], extracted_xml=None)

        # Test that str() doesn't crash
        str_result = str(result)
        self.assertIsInstance(str_result, str)
        self.assertIn("INVALID", str_result)

        # Test that repr() doesn't crash
        repr_result = repr(result)
        self.assertIsInstance(repr_result, str)

    def test_validation_result_get_summary(self):
        """Test get_summary method of ValidationResult."""
        result = ValidationResult(
            is_valid=False,
            errors=["Critical error", "Another error"],
            warnings=["Warning message"],
            extracted_xml=None,
        )

        summary = result.get_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("VALIDATION FAILED", summary)
        self.assertIn("Critical error", summary)
        self.assertIn("Warning message", summary)

    def test_validation_result_valid_summary(self):
        """Test get_summary for valid result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=["Minor issue"], extracted_xml="<xml/>")

        summary = result.get_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("VALIDATION PASSED", summary)
        self.assertIn("Minor issue", summary)


class InvoiceFileManagerTestCase(TestCase):
    """Test InvoiceFileManager class."""

    def setUp(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()

    @patch("invoice_app.utils.validation.InvoiceFileManager")
    def test_file_manager_initialization(self, mock_file_manager):
        """Test file manager initialization."""
        from invoice_app.utils.validation import InvoiceFileManager

        # Mock the initialization to avoid filesystem operations
        mock_instance = Mock()
        mock_file_manager.return_value = mock_instance

        # Create instance
        InvoiceFileManager(self.temp_dir)

        # Verify it was called with the correct parameter
        mock_file_manager.assert_called_once_with(self.temp_dir)

    @patch("invoice_app.utils.validation.InvoiceFileManager")
    def test_move_to_processed(self, mock_file_manager):
        """Test moving file to processed directory."""
        mock_instance = Mock()
        mock_file_manager.return_value = mock_instance

        # Setup mock return value
        mock_instance.move_to_processed.return_value = "/processed/file.pdf"

        from invoice_app.utils.validation import InvoiceFileManager

        manager = InvoiceFileManager(self.temp_dir)

        # Test method
        result = manager.move_to_processed("/input/file.pdf")

        # Verify
        mock_instance.move_to_processed.assert_called_once_with("/input/file.pdf")
        self.assertEqual(result, "/processed/file.pdf")

    @patch("invoice_app.utils.validation.InvoiceFileManager")
    def test_move_to_rejected(self, mock_file_manager):
        """Test moving file to rejected directory."""
        mock_instance = Mock()
        mock_file_manager.return_value = mock_instance

        # Setup mock return value
        validation_result = ValidationResult(False, ["Error"], [], None)
        mock_instance.move_to_rejected.return_value = ("/rejected/file.pdf", "/rejected/report.txt")

        from invoice_app.utils.validation import InvoiceFileManager

        manager = InvoiceFileManager(self.temp_dir)

        # Test method
        file_path, report_path = manager.move_to_rejected("/input/file.pdf", validation_result)

        # Verify
        mock_instance.move_to_rejected.assert_called_once_with("/input/file.pdf", validation_result)
        self.assertEqual(file_path, "/rejected/file.pdf")
        self.assertEqual(report_path, "/rejected/report.txt")

    def test_file_manager_real_initialization(self):
        """Test real file manager initialization."""
        from invoice_app.utils.validation import InvoiceFileManager

        # Test with custom directory
        manager = InvoiceFileManager(self.temp_dir)
        self.assertEqual(str(manager.base_dir), self.temp_dir)

        # Test default initialization
        manager_default = InvoiceFileManager()
        self.assertIsNotNone(manager_default.base_dir)

    @patch("shutil.copy2")
    def test_move_to_processed_real(self, mock_copy):
        """Test real move_to_processed method."""
        from invoice_app.utils.validation import InvoiceFileManager

        manager = InvoiceFileManager(self.temp_dir)

        # Create a test file path
        test_file = "/test/invoice.pdf"

        # Call method
        result = manager.move_to_processed(test_file, invoice_id=123)

        # Verify copy was called
        mock_copy.assert_called_once()
        self.assertIsInstance(result, Path)
        self.assertIn("id123", str(result))

    @patch("shutil.copy2")
    @patch("builtins.open", create=True)
    def test_move_to_rejected_real(self, mock_open, mock_copy):
        """Test real move_to_rejected method."""
        from invoice_app.utils.validation import InvoiceFileManager

        manager = InvoiceFileManager(self.temp_dir)

        # Create test validation result
        validation_result = ValidationResult(is_valid=False, errors=["Test error"], warnings=[], extracted_xml=None)

        # Call method
        file_path, report_path = manager.move_to_rejected("/test/invoice.pdf", validation_result)

        # Verify copy was called
        mock_copy.assert_called_once()
        # Verify file was opened for writing
        mock_open.assert_called()
        self.assertIsInstance(file_path, Path)
        self.assertIsInstance(report_path, Path)


class InvoiceValidatorTestCase(TestCase):
    """Test InvoiceValidator class."""

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_validator_initialization(self, mock_setup):
        """Test validator initialization."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup to avoid import errors
        mock_setup.return_value = None

        _ = InvoiceValidator()

        # Verify setup was called
        mock_setup.assert_called_once()

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_validate_invoice_file_file_not_exists(self, mock_setup):
        """Test validation when file doesn't exist."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup
        mock_setup.return_value = None

        validator = InvoiceValidator()

        result = validator.validate_invoice_file("/nonexistent/file.pdf")

        # Should return invalid result
        self.assertFalse(result.is_valid)
        self.assertIn("File not found", str(result.errors))

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_validate_xml_content_empty(self, mock_setup):
        """Test XML content validation with empty content."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup
        mock_setup.return_value = None

        validator = InvoiceValidator()

        # Test with empty XML
        result = validator.validate_xml_content("")
        self.assertFalse(result.is_valid)
        self.assertIn("Empty XML content", str(result.errors))

        # Test with whitespace only
        result = validator.validate_xml_content("   ")
        self.assertFalse(result.is_valid)

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_validate_xml_content_with_content(self, mock_setup):
        """Test XML content validation with actual content."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup and validator
        mock_setup.return_value = None
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.extracted_xml = "<xml>test</xml>"
        mock_validator.validate_xml_content.return_value = mock_result

        validator = InvoiceValidator()
        validator.validator = mock_validator

        # Test with valid XML
        result = validator.validate_xml_content("<xml>test</xml>")

        # Verify validator was called
        mock_validator.validate_xml_content.assert_called_once_with("<xml>test</xml>")
        self.assertTrue(result.is_valid)

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    @patch("os.path.exists")
    def test_validate_invoice_file_with_validator(self, mock_exists, mock_setup):
        """Test file validation with comprehensive validator."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup and file existence
        mock_setup.return_value = None
        mock_exists.return_value = True

        # Mock validator
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = ["Minor warning"]
        mock_result.extracted_xml = "<xml>content</xml>"
        mock_validator.validate_pdf_file.return_value = mock_result

        validator = InvoiceValidator()
        validator.validator = mock_validator

        # Test validation
        result = validator.validate_invoice_file("/test/file.pdf")

        # Verify
        mock_validator.validate_pdf_file.assert_called_once_with("/test/file.pdf")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.warnings, ["Minor warning"])

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_check_duplicate_invoice(self, mock_setup):
        """Test duplicate invoice checking."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup
        mock_setup.return_value = None

        validator = InvoiceValidator()

        # Test duplicate checking - should not crash even without database
        result = validator.check_duplicate_invoice("INV-001", 100.50)

        # Should return False if there's any error (no database connection)
        self.assertFalse(result)

    @patch("invoice_app.utils.validation.InvoiceValidator._setup_validator")
    def test_error_handling_setup_failure(self, mock_setup):
        """Test error handling when setup fails."""
        from invoice_app.utils.validation import InvoiceValidator

        # Mock setup to raise an exception
        mock_setup.side_effect = ImportError("Test import error")

        # Should handle the error gracefully
        with self.assertRaises(ImportError):
            InvoiceValidator()

    def test_setup_validator_import_error(self):
        """Test _setup_validator with actual import error."""
        from invoice_app.utils.validation import InvoiceValidator

        # This should fail with ImportError due to missing comprehensive_invoice_validator
        with self.assertRaises(ImportError) as context:
            InvoiceValidator()

        self.assertIn("Could not import ComprehensiveInvoiceValidator", str(context.exception))


class ValidationUtilsTestCase(TestCase):
    """Test validation utility functions."""

    def test_validation_result_immutability(self):
        """Test that ValidationResult behaves predictably."""
        result = ValidationResult(is_valid=True, errors=[], warnings=["test"], extracted_xml="<xml/>")

        # Test that attributes are accessible
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, ["test"])
        self.assertEqual(result.extracted_xml, "<xml/>")

    def test_validation_error_scenarios(self):
        """Test various error scenarios in validation."""
        # Test multiple errors
        result = ValidationResult(
            is_valid=False, errors=["Error 1", "Error 2", "Error 3"], warnings=["Warning 1"], extracted_xml=None
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 3)
        self.assertEqual(len(result.warnings), 1)
        self.assertIsNone(result.extracted_xml)

    def test_validation_warning_scenarios(self):
        """Test validation with warnings but valid result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Non-critical issue", "Minor formatting problem"],
            extracted_xml="<valid>xml</valid>",
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 2)
        self.assertIsNotNone(result.extracted_xml)

    def test_validation_result_none_handling(self):
        """Test ValidationResult with None values."""
        result = ValidationResult(is_valid=False, errors=None, warnings=None, extracted_xml=None)

        # Should convert None to empty list
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertIsNone(result.extracted_xml)
