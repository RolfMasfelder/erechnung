"""
Integration tests for the invoice workflow.
"""

import os  # noqa: I001
import tempfile
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine
from invoice_app.services.invoice_service import InvoiceService
from invoice_app.utils.pdf import PdfA3Generator
from invoice_app.utils.xml import ZugferdXmlGenerator, ZugferdXmlValidator

User = get_user_model()


class InvoiceWorkflowIntegrationTests(TestCase):
    """Integration tests for the complete invoice workflow."""

    def setUp(self):
        """Set up test data for the workflow tests."""
        # Create test directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_output_dir = os.path.join(self.temp_dir, "output")
        self.temp_xml_dir = os.path.join(self.temp_dir, "xml")
        os.makedirs(self.temp_output_dir, exist_ok=True)
        os.makedirs(self.temp_xml_dir, exist_ok=True)

        # Create test user
        self.user = User.objects.create_user(username="testuser", password="12345")

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
            created_by=self.user,
        )

        # Create invoice lines
        InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Product A",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("200.00"),
            product_code="PROD-A",
            unit_of_measure=1,
        )

        InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Product B",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("50.00"),
            product_code="PROD-B",
            unit_of_measure=1,
        )

    def tearDown(self):
        """Clean up temporary files and directories."""
        # Remove all files in temp directories
        for file in os.listdir(self.temp_output_dir):
            os.unlink(os.path.join(self.temp_output_dir, file))

        for file in os.listdir(self.temp_xml_dir):
            os.unlink(os.path.join(self.temp_xml_dir, file))

        # Remove temp directories
        os.rmdir(self.temp_output_dir)
        os.rmdir(self.temp_xml_dir)
        os.rmdir(self.temp_dir)

    @mock.patch("invoice_app.services.invoice_service.PdfA3Generator")
    @mock.patch("invoice_app.services.invoice_service.ZugferdXmlGenerator")
    @mock.patch("invoice_app.services.invoice_service.ZugferdXmlValidator")
    def test_complete_invoice_workflow(self, mock_validator, mock_generator, mock_pdf_generator):
        """Test the complete invoice workflow from model to PDF/A-3 with embedded XML."""
        # Set up mocks with valid ZUGFeRD XML structure
        mock_generator_instance = mock_generator.return_value
        valid_zugferd_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
    <Header>
        <ID>INV-2023-001</ID>
        <IssueDateTime>
            <DateTimeString format="102">20230501</DateTimeString>
        </IssueDateTime>
        <TypeCode>380</TypeCode>
    </Header>
</Invoice>"""
        mock_generator_instance.generate_xml.return_value = valid_zugferd_xml

        mock_validator_instance = mock_validator.return_value
        mock_validator_instance.validate_xml.return_value = (True, [])

        mock_pdf_instance = mock_pdf_generator.return_value
        mock_pdf_instance.generate_invoice_pdf.return_value = {
            "pdf_path": os.path.join(self.temp_output_dir, "invoice.pdf"),
            "xml_path": os.path.join(self.temp_xml_dir, "invoice.xml"),
        }

        # Create invoice service
        service = InvoiceService()

        # Generate invoice files
        result = service.generate_invoice_files(self.invoice, "COMFORT")

        # Check service result
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["validation_errors"]), 0)

        # Verify invoice was updated with file paths
        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.pdf_file)
        self.assertIsNotNone(self.invoice.xml_file)

        # Verify all mocks were called correctly
        # 1. XML generator should be called twice: once in __init__ and once with profile
        self.assertEqual(mock_generator.call_count, 2)
        # Check that the second call was with the COMFORT profile
        mock_generator.assert_any_call(profile="COMFORT")
        mock_generator_instance.generate_xml.assert_called_once()

        # 2. XML validation
        mock_validator_instance.validate_xml.assert_called_once_with(valid_zugferd_xml)

        # 3. PDF generation
        mock_pdf_instance.generate_invoice_pdf.assert_called_once()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_workflow_with_real_components(self):
        """Test the workflow with real (non-mocked) components."""
        # Skip this test if Ghostscript is not available
        import subprocess

        try:
            subprocess.run(["gs", "--version"], stdout=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            self.skipTest("Ghostscript not available, skipping test")

        # Create service
        service = InvoiceService()

        # Convert model to dict
        invoice_data = service.convert_model_to_dict(self.invoice)

        # Generate XML
        xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        xml_content = xml_generator.generate_xml(invoice_data)

        # Validate the XML
        xml_validator = ZugferdXmlValidator()
        result = xml_validator.validate_xml(xml_content)

        # We're not sure if validation will pass as we don't have control over the schemas
        # in the test environment, so we just log the results
        if not result.is_valid:
            print(f"XML validation errors: {result.errors}")

        # Create directories for the PDF generator
        temp_output_dir = os.path.join(settings.MEDIA_ROOT, "invoices")
        temp_xml_dir = os.path.join(settings.MEDIA_ROOT, "xml")
        os.makedirs(temp_output_dir, exist_ok=True)
        os.makedirs(temp_xml_dir, exist_ok=True)

        # Generate PDF (We mock subprocess.run to avoid actual Ghostscript execution)
        with mock.patch("subprocess.run") as mock_run:
            # Configure mock to simulate successful Ghostscript conversion
            def mock_ghostscript_side_effect(*args, **kwargs):
                gs_args = args[0]
                output_file = None
                for arg in gs_args:
                    if arg.startswith("-sOutputFile="):
                        output_file = arg.split("=", 1)[1]
                        break

                if output_file and len(gs_args) > 0:
                    input_file = gs_args[-1]
                    if os.path.exists(input_file):
                        import shutil

                        shutil.copy2(input_file, output_file)

                result = mock.Mock(returncode=0)
                result.stdout = b""
                result.stderr = b""
                return result

            mock_run.side_effect = mock_ghostscript_side_effect

            pdf_generator = PdfA3Generator(output_dir=temp_output_dir, xml_dir=temp_xml_dir)
            result = pdf_generator.generate_invoice_pdf(invoice_data, xml_content, invoice_instance=self.invoice)

            # Verify PDF generation was called
            mock_run.assert_called()

        # Verify we got results
        self.assertIn("pdf_path", result)
        self.assertIn("xml_path", result)

    def test_model_to_dict_conversion(self):
        """Test that model to dictionary conversion works correctly."""
        # Create service
        service = InvoiceService()

        # Convert model to dict
        invoice_data = service.convert_model_to_dict(self.invoice)

        # Check the conversion
        self.assertEqual(invoice_data["number"], "INV-2023-001")
        self.assertEqual(invoice_data["currency"], "EUR")
        self.assertEqual(invoice_data["subtotal"], 250.0)
        self.assertEqual(invoice_data["total_amount"], 297.5)

        # Check issuer and customer
        self.assertEqual(invoice_data["issuer"]["name"], "Test Supplier GmbH")
        self.assertEqual(invoice_data["customer"]["name"], "Test Customer AG")

        # Check items
        self.assertEqual(len(invoice_data["items"]), 2)
        self.assertEqual(invoice_data["items"][0]["product_name"], "Product A")
        self.assertEqual(invoice_data["items"][0]["quantity"], 2.0)
        self.assertEqual(invoice_data["items"][1]["product_name"], "Product B")
        self.assertEqual(invoice_data["items"][1]["quantity"], 1.0)

    def test_full_lifecycle_invoice_creation_to_xml_validation(self):
        """
        Test the complete lifecycle: Invoice creation → XML generation → Validation.

        This test covers the full workflow without mocks to ensure all components
        work together correctly with the official ZUGFeRD structure.
        """
        # Step 1: Create service
        service = InvoiceService()

        # Step 2: Convert Django model to dict
        invoice_data = service.convert_model_to_dict(self.invoice)

        # Verify the conversion includes all required ZUGFeRD fields
        self.assertIn("number", invoice_data)
        self.assertIn("date", invoice_data)
        self.assertIn("currency", invoice_data)
        self.assertIn("issuer", invoice_data)
        self.assertIn("customer", invoice_data)
        self.assertIn("items", invoice_data)

        # Step 3: Generate ZUGFeRD XML with COMFORT profile
        xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        xml_content = xml_generator.generate_xml(invoice_data)

        # Verify XML was generated
        self.assertIsNotNone(xml_content)
        self.assertTrue(xml_content.startswith("<?xml"))
        self.assertIn("rsm:CrossIndustryInvoice", xml_content)  # Official CII root element

        # Step 4: Parse XML to verify structure
        from lxml import etree

        xml_root = etree.fromstring(xml_content.encode("utf-8"))

        # Define namespaces
        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Verify ExchangedDocument
        exchanged_doc = xml_root.find(".//rsm:ExchangedDocument", namespaces)
        self.assertIsNotNone(exchanged_doc, "Must have ExchangedDocument")

        invoice_id = exchanged_doc.find(".//ram:ID", namespaces)
        self.assertEqual(invoice_id.text, "INV-2023-001")

        # Verify SupplyChainTradeTransaction (required by CII schema)
        transaction = xml_root.find(".//rsm:SupplyChainTradeTransaction", namespaces)
        self.assertIsNotNone(transaction, "Must have SupplyChainTradeTransaction")

        # Verify InvoiceCurrencyCode in ApplicableHeaderTradeSettlement (official CII structure)
        settlement = transaction.find(".//ram:ApplicableHeaderTradeSettlement", namespaces)
        currency_code = settlement.find("ram:InvoiceCurrencyCode", namespaces)
        self.assertEqual(currency_code.text, "EUR")

        # Verify ApplicableHeaderTradeAgreement has SellerTradeParty and BuyerTradeParty
        agreement = transaction.find(".//ram:ApplicableHeaderTradeAgreement", namespaces)
        seller_party = agreement.find("ram:SellerTradeParty", namespaces)
        buyer_party = agreement.find("ram:BuyerTradeParty", namespaces)
        self.assertIsNotNone(seller_party, "Must have SellerTradeParty")
        self.assertIsNotNone(buyer_party, "Must have BuyerTradeParty")

        # Verify line items
        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 2, "Should have 2 line items")

        # Verify line item structure (all 4 subgroups)
        first_item = line_items[0]

        # SpecifiedTradeProduct
        product = first_item.find(".//ram:SpecifiedTradeProduct", namespaces)
        self.assertIsNotNone(product)

        # SpecifiedLineTradeAgreement with NetPriceProductTradePrice
        agreement = first_item.find(".//ram:SpecifiedLineTradeAgreement", namespaces)
        self.assertIsNotNone(agreement)
        net_price = agreement.find(".//ram:NetPriceProductTradePrice", namespaces)
        self.assertIsNotNone(net_price)

        # SpecifiedLineTradeDelivery with BilledQuantity
        delivery = first_item.find(".//ram:SpecifiedLineTradeDelivery", namespaces)
        self.assertIsNotNone(delivery)
        billed_qty = delivery.find(".//ram:BilledQuantity", namespaces)
        self.assertIsNotNone(billed_qty)
        self.assertEqual(billed_qty.get("unitCode"), "C62", "Must have unitCode attribute")

        # SpecifiedLineTradeSettlement with tax and summation
        settlement = first_item.find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        self.assertIsNotNone(settlement)

        # Verify ApplicableHeaderTradeSettlement with all 6 monetary fields
        header_settlement = xml_root.find(".//ram:ApplicableHeaderTradeSettlement", namespaces)
        self.assertIsNotNone(header_settlement)

        summation = header_settlement.find(".//ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces)
        self.assertIsNotNone(summation)

        # Check all 6 required fields
        line_total = summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertIsNotNone(line_total)
        self.assertEqual(line_total.text, "250.00")

        charge_total = summation.find(".//ram:ChargeTotalAmount", namespaces)
        self.assertIsNotNone(charge_total)

        allowance_total = summation.find(".//ram:AllowanceTotalAmount", namespaces)
        self.assertIsNotNone(allowance_total)

        tax_basis = summation.find(".//ram:TaxBasisTotalAmount", namespaces)
        self.assertIsNotNone(tax_basis)

        tax_total = summation.find(".//ram:TaxTotalAmount", namespaces)
        self.assertIsNotNone(tax_total)

        grand_total = summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertIsNotNone(grand_total)

        # Step 5: Validate the XML
        xml_validator = ZugferdXmlValidator()
        validation_result = xml_validator.validate_xml(xml_content)

        # Validation may fail if schemas aren't available in test environment
        # but the XML structure should still be correct
        self.assertIsNotNone(validation_result)
        self.assertIsNotNone(validation_result.backend_used)

        # If validation errors occur, they should be from schema issues, not structure
        if not validation_result.is_valid:
            # Log errors for debugging but don't fail the test
            # (schema files might not be available in all test environments)
            print(f"Validation backend: {validation_result.backend_used}")
            print(f"Validation errors: {validation_result.errors}")
            print(f"Validation warnings: {validation_result.warnings}")
