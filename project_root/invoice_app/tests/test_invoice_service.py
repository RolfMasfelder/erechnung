"""
Tests for the invoice service.
"""

from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine
from invoice_app.services.invoice_service import InvoiceService


class TestInvoiceService(TestCase):
    """Test suite for the Invoice Service."""

    def setUp(self):
        """Set up test data and models."""
        # Create Country for ForeignKey
        self.germany = Country.objects.get_or_create(
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

        # Create test company and customer
        self.supplier = Company.objects.create(
            name="Test Supplier GmbH",
            tax_id="DE123456789",
            vat_id="DE987654321",
            address_line1="Supplier Street 123",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
            email="contact@supplier.com",
        )

        self.business_partner = BusinessPartner.objects.create(
            company_name="Test Customer AG",
            tax_id="DE987654321",
            address_line1="Customer Avenue 456",
            postal_code="80333",
            city="Munich",
            country=self.germany,
            email="info@customer.com",
        )

        # Create test invoice
        today = timezone.now().date()
        due_date = today + timezone.timedelta(days=30)

        self.invoice = Invoice.objects.create(
            invoice_number="INV-2023-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.supplier,
            business_partner=self.business_partner,
            issue_date=today,
            due_date=due_date,
            currency="EUR",
            subtotal=Decimal("250.00"),
            tax_amount=Decimal("47.50"),
            total_amount=Decimal("297.50"),
            status=Invoice.InvoiceStatus.DRAFT,
        )

        # Create invoice lines
        self.line1 = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Product A",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("200.00"),
            product_code="PROD-A",
            unit_of_measure=1,
        )

        self.line2 = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Product B",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("50.00"),
            product_code="PROD-B",
            unit_of_measure=1,
        )

        # Initialize service
        self.invoice_service = InvoiceService()

    def test_convert_model_to_dict(self):
        """Test conversion of Django model to dictionary."""
        # Convert the model to a dictionary
        invoice_dict = self.invoice_service.convert_model_to_dict(self.invoice)

        # Check that the dictionary contains the expected data
        self.assertEqual(invoice_dict["number"], "INV-2023-001")
        self.assertEqual(invoice_dict["currency"], "EUR")
        self.assertEqual(invoice_dict["subtotal"], 250.0)
        self.assertEqual(invoice_dict["tax_amount"], 47.5)
        self.assertEqual(invoice_dict["total_amount"], 297.5)

        # Check customer and supplier data
        self.assertEqual(invoice_dict["customer"]["name"], "Test Customer AG")
        self.assertEqual(invoice_dict["issuer"]["name"], "Test Supplier GmbH")

        # Check items
        self.assertEqual(len(invoice_dict["items"]), 2)
        self.assertEqual(invoice_dict["items"][0]["product_name"], "Product A")
        self.assertEqual(invoice_dict["items"][0]["quantity"], 2.0)
        self.assertEqual(invoice_dict["items"][0]["price"], 100.0)
        self.assertEqual(invoice_dict["items"][1]["product_name"], "Product B")

    @mock.patch("invoice_app.services.invoice_service.ZugferdXmlGenerator")
    @mock.patch("invoice_app.services.invoice_service.ZugferdXmlValidator")
    @mock.patch("invoice_app.services.invoice_service.PdfA3Generator")
    def test_generate_invoice_files(self, mock_pdf_generator, mock_xml_validator, mock_xml_generator):
        """Test generation of invoice files."""
        # Set up mocks
        mock_xml_instance = mock_xml_generator.return_value
        mock_xml_instance.generate_xml.return_value = "<xml>Test</xml>"

        # Mock the xml_validator instance on the service
        mock_validator = mock.Mock()
        mock_validator.validate_xml.return_value = (True, [])
        self.invoice_service.xml_validator = mock_validator

        # Mock the pdf_generator instance on the service
        mock_pdf = mock.Mock()
        mock_pdf.generate_invoice_pdf.return_value = {
            "pdf_path": "/tmp/invoice.pdf",
            "xml_path": "/tmp/invoice.xml",
        }
        self.invoice_service.pdf_generator = mock_pdf

        # Call the method under test
        result = self.invoice_service.generate_invoice_files(self.invoice, "BASIC")

        # Verify XML generation was called
        mock_xml_instance.generate_xml.assert_called_once()

        # Verify XML validation was called
        mock_validator.validate_xml.assert_called_once()

        # Verify PDF generation was called
        mock_pdf.generate_invoice_pdf.assert_called_once()

        # Check the result
        self.assertEqual(result["pdf_path"], "/tmp/invoice.pdf")
        self.assertEqual(result["xml_path"], "/tmp/invoice.xml")
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["validation_errors"], [])

        # Check that the invoice model was updated
        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.pdf_file)
        self.assertIsNotNone(self.invoice.xml_file)

    @mock.patch("pikepdf.open")
    def test_extract_xml_from_pdf(self, mock_pikepdf_open):
        """Test extraction of XML from PDF."""
        # Set up mock PDF with embedded XML
        mock_pdf = mock.MagicMock()

        # Create a mock Root that supports both dict-style and attribute access
        mock_root = mock.MagicMock()

        # Set up the EmbeddedFiles structure
        mock_embedded_files = mock.MagicMock()
        mock_embedded_files.Names = ["invoice.xml", mock.MagicMock()]

        # Set up XML stream mock
        xml_stream = mock.MagicMock()
        xml_stream.read.return_value = b"<xml>Test</xml>"
        mock_embedded_files.Names[1].EF.F = xml_stream

        # Configure the mock Root to handle both access patterns
        mock_root.EmbeddedFiles = mock_embedded_files
        mock_root.__contains__ = mock.MagicMock(return_value=True)  # For "/EmbeddedFiles" in check

        # Configure the mock PDF
        mock_pdf.Root = mock_root

        # Configure pikepdf.open to return our mock
        mock_pikepdf_open.return_value.__enter__.return_value = mock_pdf

        # Call the method under test
        xml_content = self.invoice_service.extract_xml_from_pdf("/path/to/invoice.pdf")

        # Verify pikepdf.open was called
        mock_pikepdf_open.assert_called_once_with("/path/to/invoice.pdf")

        # Check the result
        self.assertEqual(xml_content, "<xml>Test</xml>")

    @mock.patch("pikepdf.open")
    def test_extract_xml_from_pdf_no_embedded_files(self, mock_pikepdf_open):
        """Test extraction of XML from PDF with no embedded files."""
        # Set up mock PDF with no embedded files
        mock_pdf = mock.MagicMock()
        mock_pdf.Root = {}

        # Configure pikepdf.open to return our mock
        mock_pikepdf_open.return_value.__enter__.return_value = mock_pdf

        # Call the method under test
        xml_content = self.invoice_service.extract_xml_from_pdf("/path/to/invoice.pdf")

        # Check the result
        self.assertIsNone(xml_content)
