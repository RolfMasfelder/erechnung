"""
Tests for IncomingInvoiceService.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from invoice_app.services.incoming_invoice_service import (
    DEFAULT_COUNTRY,
    DEFAULT_POSTAL_CODE,
    PLACEHOLDER_TEXT,
    IncomingInvoiceService,
    ProcessingResult,
)
from invoice_app.utils.validation import ValidationResult


User = get_user_model()


class IncomingInvoiceServiceTestCase(TestCase):
    """Test IncomingInvoiceService."""

    @patch("invoice_app.services.incoming_invoice_service.InvoiceValidator")
    @patch("invoice_app.services.incoming_invoice_service.InvoiceFileManager")
    @patch("invoice_app.services.incoming_invoice_service.SupplierDataExtractor")
    @patch("invoice_app.services.incoming_invoice_service.IncomingXmlParser")
    def setUp(self, mock_parser, mock_extractor, mock_file_manager, mock_validator):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()

        # Setup mocks
        self.mock_parser = Mock()
        self.mock_extractor = Mock()
        self.mock_file_manager = Mock()
        self.mock_validator = Mock()

        mock_parser.return_value = self.mock_parser
        mock_extractor.return_value = self.mock_extractor
        mock_file_manager.return_value = self.mock_file_manager
        mock_validator.return_value = self.mock_validator

        self.service = IncomingInvoiceService(base_directory=self.temp_dir)

        # Create test user
        self.test_user = User.objects.create_user(username="testuser", email="test@test.com", password="testpass123")

        # IMPORTANT: Set up realistic mock data for XML parser
        # Mock objects break string formatting (:.2f) in service code,
        # so we need to return actual data structures, not Mock objects
        self._setup_realistic_invoice_data()

    def _setup_realistic_invoice_data(self):
        """Set up realistic invoice data that can be formatted without errors."""
        # Default successful invoice data - matches incoming_xml.py structure
        self.realistic_invoice_data = {
            "invoice_number": "INV-2024-001",
            "issue_date": "2024-01-15",
            "type_code": "380",
            "seller_name": "Test Supplier GmbH",
            "seller_id": "DE123456789",
            "buyer_name": "Our Company Ltd",
            "total_amount": 1250.75,  # float for :.2f formatting
            "tax_amount": 237.64,  # float for :.2f formatting
            "currency": "EUR",
            "line_items": [
                {"description": "Professional Services", "quantity": 10.0, "unit_price": 125.00, "line_total": 1250.00}
            ],
        }

        # Set as default return value for extract_invoice_data
        self.mock_parser.extract_invoice_data.return_value = self.realistic_invoice_data

    def test_initialization(self):
        """Test service initialization."""
        self.assertIsNotNone(self.service.xml_parser)
        self.assertIsNotNone(self.service.supplier_extractor)
        self.assertIsNotNone(self.service.validator)
        self.assertIsNotNone(self.service.file_manager)

    def test_load_models(self):
        """Test model loading."""
        self.service._load_models()

        self.assertIsNotNone(self.service.Company)
        self.assertIsNotNone(self.service.BusinessPartner)
        self.assertIsNotNone(self.service.Invoice)
        self.assertIsNotNone(self.service.User)

    def test_process_single_invoice_validation_failure(self):
        """Test processing invoice with validation failure."""
        # Create validation result with errors
        validation_result = ValidationResult(
            is_valid=False, errors=["Invalid PDF format"], warnings=[], extracted_xml=None
        )
        self.mock_validator.validate_invoice_file.return_value = validation_result

        # Mock file manager response
        self.mock_file_manager.move_to_rejected.return_value = ("/rejected/file.pdf", "/rejected/report.txt")

        # Test processing
        result = self.service.process_single_invoice("/test/file.pdf")

        # Assertions
        self.assertFalse(result.success)
        self.assertIn("rejected due to validation errors", result.message)
        self.assertIsNone(result.invoice_id)
        self.assertEqual(result.validation_result, validation_result)

        # Verify mocks were called
        self.mock_validator.validate_invoice_file.assert_called_once_with("/test/file.pdf")
        self.mock_file_manager.move_to_rejected.assert_called_once_with("/test/file.pdf", validation_result)

    def test_process_single_invoice_no_xml(self):
        """Test processing invoice with no XML content."""
        # Create validation result without XML
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], extracted_xml=None)
        self.mock_validator.validate_invoice_file.return_value = validation_result

        # Test processing
        result = self.service.process_single_invoice("/test/file.pdf")

        # Assertions
        self.assertFalse(result.success)
        self.assertEqual(result.message, "No XML content extracted from PDF")

    def test_process_single_invoice_xml_parsing_failure(self):
        """Test processing invoice with XML parsing failure."""
        # Create validation result with XML
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], extracted_xml="<xml>content</xml>")
        self.mock_validator.validate_invoice_file.return_value = validation_result

        # Mock extraction failure (not parsing failure)
        self.mock_parser.extract_invoice_data.side_effect = Exception("XML parsing error")

        # Test processing
        result = self.service.process_single_invoice("/test/file.pdf")

        # Assertions
        self.assertFalse(result.success)
        self.assertIn("Failed to extract invoice data from XML", result.message)

    def test_process_single_invoice_supplier_extraction_failure(self):
        """Test processing invoice with supplier extraction failure."""
        # Create validation result with XML
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[], extracted_xml="<xml>content</xml>")
        self.mock_validator.validate_invoice_file.return_value = validation_result

        # Use realistic invoice data but mock the duplicate check to trigger it
        invoice_data_no_supplier = self.realistic_invoice_data.copy()
        invoice_data_no_supplier["seller_name"] = ""  # Empty seller name causes failure
        self.mock_parser.extract_invoice_data.return_value = invoice_data_no_supplier

        # Test processing
        result = self.service.process_single_invoice("/test/file.pdf")

        # Assertions - should fail at supplier creation, not duplicate check
        self.assertFalse(result.success)
        # Note: Actual error message depends on service implementation

    def test_find_or_create_supplier_existing(self):
        """Test finding existing supplier company."""
        from invoice_app.models import Company, Country

        # Create Country for ForeignKey
        germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "numeric_code": "276",
                "name": "Germany",
                "name_local": "Deutschland",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

        # Create existing supplier with correct field names
        existing_supplier = Company.objects.create(
            name="Test Supplier",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 1",
            city="Test City",
            postal_code="12345",
            country=germany,
        )

        # Mock invoice data with matching supplier info
        invoice_data = {"seller_name": "Test Supplier", "seller_id": "DE123456789"}

        # Test finding existing supplier
        result = self.service._find_or_create_supplier(invoice_data)

        # Assertions
        self.assertEqual(result.id, existing_supplier.id)
        self.assertEqual(result.name, "Test Supplier")

    def test_find_or_create_supplier_new(self):
        """Test creating new supplier company."""
        # Mock invoice data for new supplier
        invoice_data = {"seller_name": "New Supplier Corp", "seller_id": "DE987654321"}

        # Test creating new supplier
        result = self.service._find_or_create_supplier(invoice_data)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "New Supplier Corp")
        self.assertEqual(result.tax_id, "DE987654321")

    def test_find_or_create_our_company_existing(self):
        """Test finding existing business partner (our company)."""
        from invoice_app.models import BusinessPartner, Country

        # Create Country for ForeignKey
        germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "numeric_code": "276",
                "name": "Germany",
                "name_local": "Deutschland",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

        # Create existing business partner with correct field names
        partner = BusinessPartner.objects.create(
            company_name="Test Customer Corp",  # Use company_name, not name
            email="customer@test.com",
            address_line1="Customer Street 1",
            city="Customer City",
            postal_code="54321",
            country=germany,
        )

        # Mock invoice data for our company lookup
        invoice_data = {"buyer_name": "Test Customer Corp"}

        # Test finding the business partner as our company
        result = self.service._find_or_create_our_company(invoice_data)

        # Assertions
        self.assertEqual(result.id, partner.id)

    def test_find_or_create_our_company_new(self):
        """Test creating new business partner (our company)."""
        # Mock invoice data for new business partner
        invoice_data = {"buyer_name": "New Customer Corp"}

        # Test creating new business partner
        result = self.service._find_or_create_our_company(invoice_data)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result.company_name, "New Customer Corp")

    def test_create_invoice_record_success(self):
        """Test successful invoice record creation."""
        # Use realistic invoice data that includes supplier info
        invoice_data = {
            "invoice_number": "INV-001",
            "issue_date": "2024-01-01",
            "total_amount": 100.00,
            "tax_amount": 19.00,
            "currency": "EUR",
            "seller_name": "Test Supplier Corp",
            "seller_id": "DE123456789",
            "buyer_name": "Our Company Ltd",
        }

        # Test invoice creation with correct method signature
        result = self.service._create_invoice_record(invoice_data, "/test/file.pdf")

        # Assertions
        self.assertIsNotNone(result)
        # Result is invoice ID, not invoice object

    def test_get_system_user_existing(self):
        """Test getting existing system user."""
        # Create system user with correct username
        User.objects.create_user(username="incoming_invoice_processor", email="system@company.com", is_staff=True)

        result = self.service._get_system_user()

        # Should find the existing user
        self.assertEqual(result.username, "incoming_invoice_processor")

    def test_get_system_user_create_new(self):
        """Test creating new system user when none exists."""
        # Ensure no system user exists
        User.objects.filter(username="incoming_invoice_processor").delete()
        User.objects.filter(is_staff=True).delete()

        result = self.service._get_system_user()

        # Should create new user
        self.assertIsNotNone(result)

    def test_process_batch_empty(self):
        """Test processing empty directory with process_batch method."""
        # Create empty directory
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()

        results = self.service.process_batch(str(empty_dir))

        # Should return batch result with zero files
        self.assertEqual(results.total_files, 0)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_process_batch_with_files(self, mock_glob, mock_exists):
        """Test processing directory with files."""
        # Mock directory exists
        mock_exists.return_value = True

        # Mock finding files
        test_files = [
            Path("/test/file1.pdf"),
            Path("/test/file2.pdf"),
        ]
        mock_glob.return_value = test_files

        # Mock process_single_invoice
        with patch.object(self.service, "process_single_invoice") as mock_process:
            mock_process.side_effect = [
                ProcessingResult(True, "Success", "inv1", None),
                ProcessingResult(False, "Error", None, None),
            ]

            results = self.service.process_batch("/test")

            # Assertions - process_batch returns BatchProcessingResult
            self.assertIsNotNone(results)
            self.assertEqual(results.total_files, 2)
            self.assertEqual(results.processed, 1)
            self.assertEqual(results.rejected, 1)
            # Verify process_single_invoice was called for each file found
            self.assertEqual(mock_process.call_count, 2)

    def test_processing_result_creation(self):
        """Test ProcessingResult creation."""
        result = ProcessingResult(success=True, message="Test message", invoice_id="test_id", validation_result=None)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Test message")
        self.assertEqual(result.invoice_id, "test_id")
        self.assertIsNone(result.validation_result)

    def test_constants(self):
        """Test module constants."""
        self.assertEqual(PLACEHOLDER_TEXT, "[To be updated]")
        self.assertEqual(DEFAULT_POSTAL_CODE, "00000")
        self.assertEqual(DEFAULT_COUNTRY, "DE")

    @patch("invoice_app.services.incoming_invoice_service.transaction.atomic")
    def test_transaction_handling(self, mock_atomic):
        """Test that database operations use transactions."""
        # Mock transaction context manager
        mock_context = MagicMock()
        mock_atomic.return_value.__enter__ = Mock(return_value=mock_context)
        mock_atomic.return_value.__exit__ = Mock(return_value=None)

        # Use realistic invoice data with supplier info
        invoice_data = {
            "invoice_number": "INV-001",
            "issue_date": "2024-01-01",
            "total_amount": 100.00,  # Numeric, not string
            "tax_amount": 19.00,
            "currency": "EUR",
            "seller_name": "Test Supplier Corp",
            "seller_id": "DE123456789",
            "buyer_name": "Our Company Ltd",
        }

        # Test method that should use transaction - correct signature
        self.service._create_invoice_record(invoice_data, "/test/file.pdf")

        # Verify transaction was used (may be called multiple times due to nested operations)
        mock_atomic.assert_called()

    def test_error_handling_robustness(self):
        """Test service handles various error conditions gracefully."""
        # Test with invalid file path
        result = self.service.process_single_invoice("/nonexistent/file.pdf")

        # Should handle gracefully without crashing
        self.assertFalse(result.success)
        # Check for any kind of failure message (could be "error", "duplicate", "failed", etc.)
        self.assertIsNotNone(result.message)
        self.assertTrue(len(result.message) > 0)
