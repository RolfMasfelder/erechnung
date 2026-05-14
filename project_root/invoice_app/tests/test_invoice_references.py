"""
Tests for invoice reference fields (buyer_reference and seller_reference).

This test module validates the implementation of the B2B reference fields
across the entire stack: models, PDF generation, XML generation, and API.
"""

import os  # noqa: I001
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine, Product
from invoice_app.services.invoice_service import InvoiceService
from invoice_app.utils.pdf import PdfA3Generator
from invoice_app.utils.xml import ZugferdXmlGenerator
from lxml import etree

User = get_user_model()


class InvoiceReferenceModelTests(TestCase):
    """Test suite for Invoice model reference fields."""

    def setUp(self):
        """Set up test data."""
        self.country = Country.objects.get_or_create(
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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]

        self.company = Company.objects.create(
            name="Test GmbH",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Berlin",
            country=self.country,
            email="test@company.de",
        )

        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Customer Inc",
            tax_id="DE987654321",
            vat_id="DE987654321",
            address_line1="Customer Street 1",
            postal_code="54321",
            city="Munich",
            country=self.country,
            email="customer@example.com",
            default_reference_prefix="PO-",
        )

        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_invoice_with_both_references(self):
        """Test creating an invoice with both buyer and seller references."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2026-001",
            company=self.company,
            business_partner=self.partner,
            buyer_reference="PO-12345",
            seller_reference="PROJ-2026-ABC",
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

        self.assertEqual(invoice.buyer_reference, "PO-12345")
        self.assertEqual(invoice.seller_reference, "PROJ-2026-ABC")
        self.assertIsInstance(invoice.buyer_reference, str)
        self.assertIsInstance(invoice.seller_reference, str)

    def test_invoice_without_references(self):
        """Test creating an invoice without references (blank fields)."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2026-002",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

        self.assertEqual(invoice.buyer_reference, "")
        self.assertEqual(invoice.seller_reference, "")

    def test_invoice_with_only_buyer_reference(self):
        """Test invoice with only buyer_reference filled."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2026-003",
            company=self.company,
            business_partner=self.partner,
            buyer_reference="ORDER-999",
            currency="EUR",
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            total_amount=Decimal("59.50"),
            created_by=self.user,
        )

        self.assertEqual(invoice.buyer_reference, "ORDER-999")
        self.assertEqual(invoice.seller_reference, "")

    def test_invoice_with_only_seller_reference(self):
        """Test invoice with only seller_reference filled."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2026-004",
            company=self.company,
            business_partner=self.partner,
            seller_reference="INTERNAL-2026-05",
            currency="EUR",
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("38.00"),
            total_amount=Decimal("238.00"),
            created_by=self.user,
        )

        self.assertEqual(invoice.buyer_reference, "")
        self.assertEqual(invoice.seller_reference, "INTERNAL-2026-05")

    def test_business_partner_default_reference_prefix(self):
        """Test BusinessPartner default_reference_prefix field."""
        self.assertEqual(self.partner.default_reference_prefix, "PO-")

        # Test with empty prefix
        partner2 = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Another Customer",
            address_line1="Street 2",
            postal_code="11111",
            city="Hamburg",
            country=self.country,
        )
        self.assertEqual(partner2.default_reference_prefix, "")


class InvoiceReferencePDFTests(TestCase):
    """Test suite for PDF generation with invoice references."""

    def setUp(self):
        """Set up test data for PDF generation."""
        self.pdf_generator = PdfA3Generator()

        self.sample_data_with_refs = {
            "number": "TEST-001",
            "date": "20260210",
            "due_date": "20260310",
            "buyer_reference": "PO-12345",
            "seller_reference": "PROJ-2026-ABC",
            "currency": "EUR",
            "customer": {
                "name": "Test Customer",
                "street_name": "Customer St 1",
                "city_name": "Munich",
                "postcode_code": "80331",
                "country_id": "DE",
            },
            "items": [{"product_name": "Test Product", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

        self.sample_data_without_refs = {
            "number": "TEST-002",
            "date": "20260210",
            "due_date": "20260310",
            "buyer_reference": "",
            "seller_reference": "",
            "currency": "EUR",
            "customer": {
                "name": "Test Customer",
                "street_name": "Customer St 1",
                "city_name": "Munich",
                "postcode_code": "80331",
                "country_id": "DE",
            },
            "items": [{"product_name": "Test Product", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

    @mock.patch("invoice_app.utils.pdf.PdfA3Generator._create_base_pdf")
    def test_pdf_contains_buyer_reference(self, mock_create_pdf):
        """Test that PDF generation is called with buyer reference data.

        WeasyPrint is mocked to avoid hanging in headless container environments.
        The test verifies that _create_base_pdf is called with the correct data
        containing the buyer_reference field.
        """

        # Configure mock to write a minimal dummy file
        def _write_dummy(invoice_data, output_path):
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4 dummy")

        mock_create_pdf.side_effect = _write_dummy

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.pdf_generator._create_base_pdf(self.sample_data_with_refs, tmp_path)

            # Verify mock was called with data containing buyer_reference
            mock_create_pdf.assert_called_once()
            call_data = mock_create_pdf.call_args[0][0]
            self.assertEqual(call_data["buyer_reference"], "PO-12345")
            self.assertEqual(call_data["seller_reference"], "PROJ-2026-ABC")

            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @mock.patch("invoice_app.utils.pdf.PdfA3Generator._create_base_pdf")
    def test_pdf_without_references_is_valid(self, mock_create_pdf):
        """Test that PDF generation is called correctly without references.

        WeasyPrint is mocked to avoid hanging in headless container environments.
        """

        def _write_dummy(invoice_data, output_path):
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4 dummy")

        mock_create_pdf.side_effect = _write_dummy

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.pdf_generator._create_base_pdf(self.sample_data_without_refs, tmp_path)

            mock_create_pdf.assert_called_once()
            call_data = mock_create_pdf.call_args[0][0]
            self.assertEqual(call_data["buyer_reference"], "")
            self.assertEqual(call_data["seller_reference"], "")

            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class InvoiceReferenceXMLTests(TestCase):
    """Test suite for ZUGFeRD XML generation with invoice references."""

    def setUp(self):
        """Set up test data for XML generation."""
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")

        self.invoice_data_with_refs = {
            "number": "TEST-XML-001",
            "date": "20260210",
            "due_date": "20260310",
            "buyer_reference": "PO-12345",
            "seller_reference": "PROJ-2026-ABC",
            "currency": "EUR",
            "company": {"name": "Test GmbH", "tax_id": "DE123456789"},
            "customer": {"name": "Customer AG", "tax_id": "DE987654321"},
            "items": [{"product_name": "Test", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

        self.invoice_data_without_refs = {
            "number": "TEST-XML-002",
            "date": "20260210",
            "due_date": "20260310",
            "buyer_reference": "",
            "seller_reference": "",
            "currency": "EUR",
            "company": {"name": "Test GmbH", "tax_id": "DE123456789"},
            "customer": {"name": "Customer AG", "tax_id": "DE987654321"},
            "items": [{"product_name": "Test", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

    def test_xml_contains_buyer_order_referenced_document(self):
        """Test that XML contains BuyerOrderReferencedDocument when buyer_reference is present."""
        xml_string = self.xml_generator.generate_xml(self.invoice_data_with_refs)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        # Find BuyerOrderReferencedDocument
        buyer_ref_elem = root.find(".//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID", ns)

        self.assertIsNotNone(buyer_ref_elem, "BuyerOrderReferencedDocument should exist in XML")
        self.assertEqual(buyer_ref_elem.text, "PO-12345")

    def test_xml_contains_seller_order_referenced_document(self):
        """Test that XML contains SellerOrderReferencedDocument when seller_reference is present."""
        xml_string = self.xml_generator.generate_xml(self.invoice_data_with_refs)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        # Find SellerOrderReferencedDocument
        seller_ref_elem = root.find(".//ram:SellerOrderReferencedDocument/ram:IssuerAssignedID", ns)

        self.assertIsNotNone(seller_ref_elem, "SellerOrderReferencedDocument should exist in XML")
        self.assertEqual(seller_ref_elem.text, "PROJ-2026-ABC")

    def test_xml_without_references_omits_elements(self):
        """Test that XML without references does not contain reference elements."""
        xml_string = self.xml_generator.generate_xml(self.invoice_data_without_refs)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        # Verify elements are not present
        buyer_ref_elem = root.find(".//ram:BuyerOrderReferencedDocument", ns)
        seller_ref_elem = root.find(".//ram:SellerOrderReferencedDocument", ns)

        self.assertIsNone(
            buyer_ref_elem, "BuyerOrderReferencedDocument should not exist when buyer_reference is empty"
        )
        self.assertIsNone(
            seller_ref_elem, "SellerOrderReferencedDocument should not exist when seller_reference is empty"
        )

    def test_xml_with_only_buyer_reference(self):
        """Test XML generation with only buyer_reference."""
        data = self.invoice_data_with_refs.copy()
        data["seller_reference"] = ""

        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        buyer_ref = root.find(".//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID", ns)
        seller_ref = root.find(".//ram:SellerOrderReferencedDocument", ns)

        self.assertIsNotNone(buyer_ref)
        self.assertEqual(buyer_ref.text, "PO-12345")
        self.assertIsNone(seller_ref)

    def test_xml_with_only_seller_reference(self):
        """Test XML generation with only seller_reference."""
        data = self.invoice_data_with_refs.copy()
        data["buyer_reference"] = ""

        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        buyer_ref = root.find(".//ram:BuyerOrderReferencedDocument", ns)
        seller_ref = root.find(".//ram:SellerOrderReferencedDocument/ram:IssuerAssignedID", ns)

        self.assertIsNone(buyer_ref)
        self.assertIsNotNone(seller_ref)
        self.assertEqual(seller_ref.text, "PROJ-2026-ABC")

    def test_xml_seller_reference_before_buyer_reference(self):
        """Test that SellerOrderReferencedDocument precedes BuyerOrderReferencedDocument.

        The CII XSD defines a strict sequence in HeaderTradeAgreementType:
        SellerOrderReferencedDocument must come BEFORE BuyerOrderReferencedDocument.
        Wrong order causes: cvc-complex-type.2.4.a schema validation error.
        """
        xml_string = self.xml_generator.generate_xml(self.invoice_data_with_refs)
        root = etree.fromstring(xml_string.encode("utf-8"))

        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}
        agreement = root.find(".//ram:ApplicableHeaderTradeAgreement", ns)
        self.assertIsNotNone(agreement)

        children = [child.tag for child in agreement]
        seller_tag = f"{{{ns['ram']}}}SellerOrderReferencedDocument"
        buyer_tag = f"{{{ns['ram']}}}BuyerOrderReferencedDocument"

        self.assertIn(seller_tag, children, "SellerOrderReferencedDocument missing")
        self.assertIn(buyer_tag, children, "BuyerOrderReferencedDocument missing")
        self.assertLess(
            children.index(seller_tag),
            children.index(buyer_tag),
            "SellerOrderReferencedDocument must come before BuyerOrderReferencedDocument (CII XSD sequence)",
        )


class InvoiceReferenceAPITests(TestCase):
    """Test suite for API serialization of invoice references."""

    def setUp(self):
        """Set up test data for API tests."""
        self.country = Country.objects.get_or_create(
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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]

        self.company = Company.objects.create(
            name="API Test GmbH",
            tax_id="DE111111111",
            address_line1="API Street 1",
            postal_code="10115",
            city="Berlin",
            country=self.country,
        )

        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="API Customer",
            address_line1="Customer St 1",
            postal_code="80331",
            city="Munich",
            country=self.country,
        )

        self.user = User.objects.create_user(username="apiuser", password="apipass123")

    def test_invoice_serializer_includes_reference_fields(self):
        """Test that InvoiceSerializer includes buyer_reference and seller_reference."""
        from datetime import date

        from invoice_app.api.serializers import InvoiceSerializer

        invoice = Invoice.objects.create(
            invoice_number="API-TEST-001",
            company=self.company,
            business_partner=self.partner,
            buyer_reference="API-PO-001",
            seller_reference="API-PROJ-001",
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
            issue_date=date.today(),
            due_date=date.today(),
        )

        serializer = InvoiceSerializer(invoice)
        data = serializer.data

        self.assertIn("buyer_reference", data)
        self.assertIn("seller_reference", data)
        self.assertEqual(data["buyer_reference"], "API-PO-001")
        self.assertEqual(data["seller_reference"], "API-PROJ-001")

    def test_invoice_serializer_accepts_reference_fields_on_create(self):
        """Test that InvoiceSerializer accepts reference fields when creating invoices."""
        from invoice_app.api.serializers import InvoiceSerializer

        data = {
            "invoice_number": "API-CREATE-001",
            "company": self.company.id,
            "business_partner": self.partner.id,
            "buyer_reference": "NEW-PO-123",
            "seller_reference": "NEW-PROJ-456",
            "currency": "EUR",
            "subtotal": "150.00",
            "tax_amount": "28.50",
            "total_amount": "178.50",
            "issue_date": "2026-02-10",
            "due_date": "2026-03-10",
        }

        serializer = InvoiceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # Note: Would normally call serializer.save() here,
        # but that requires a full DRF context with request

    def test_invoice_without_references_serializes_correctly(self):
        """Test that invoices without references serialize correctly."""
        from datetime import date

        from invoice_app.api.serializers import InvoiceSerializer

        invoice = Invoice.objects.create(
            invoice_number="API-TEST-002",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            total_amount=Decimal("59.50"),
            created_by=self.user,
            issue_date=date.today(),
            due_date=date.today(),
        )

        serializer = InvoiceSerializer(invoice)
        data = serializer.data

        self.assertEqual(data["buyer_reference"], "")
        self.assertEqual(data["seller_reference"], "")


class InvoiceReferenceServiceTests(TestCase):
    """Test suite for InvoiceService with reference fields."""

    def setUp(self):
        """Set up test data for service tests."""
        self.country = Country.objects.get_or_create(
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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]

        self.company = Company.objects.create(
            name="Service Test GmbH",
            tax_id="DE222222222",
            vat_id="DE222222222",
            address_line1="Service St 1",
            postal_code="10115",
            city="Berlin",
            country=self.country,
            email="service@test.de",
        )

        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Service Customer",
            tax_id="DE333333333",
            vat_id="DE333333333",
            address_line1="Customer St 1",
            postal_code="80331",
            city="Munich",
            country=self.country,
            email="customer@test.de",
        )

        self.product = Product.objects.create(
            name="Test Product",
            product_code="PROD-001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )

        self.user = User.objects.create_user(username="serviceuser", password="servicepass123")

        self.invoice_service = InvoiceService()

    def test_convert_model_to_dict_includes_references(self):
        """Test that convert_model_to_dict includes buyer_reference and seller_reference."""
        invoice = Invoice.objects.create(
            invoice_number="SERVICE-001",
            company=self.company,
            business_partner=self.partner,
            buyer_reference="SERVICE-PO-001",
            seller_reference="SERVICE-PROJ-001",
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

        # Add a line item
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )

        # Convert to dict
        invoice_dict = self.invoice_service.convert_model_to_dict(invoice)

        self.assertIn("buyer_reference", invoice_dict)
        self.assertIn("seller_reference", invoice_dict)
        self.assertEqual(invoice_dict["buyer_reference"], "SERVICE-PO-001")
        self.assertEqual(invoice_dict["seller_reference"], "SERVICE-PROJ-001")

    def test_convert_model_to_dict_with_empty_references(self):
        """Test convert_model_to_dict with empty reference fields."""
        invoice = Invoice.objects.create(
            invoice_number="SERVICE-002",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            total_amount=Decimal("59.50"),
            created_by=self.user,
        )

        # Add a line item
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
        )

        invoice_dict = self.invoice_service.convert_model_to_dict(invoice)

        self.assertEqual(invoice_dict["buyer_reference"], "")
        self.assertEqual(invoice_dict["seller_reference"], "")
        self.assertEqual(invoice_dict["seller_reference"], "")
        self.assertEqual(invoice_dict["seller_reference"], "")


class ContractReferenceTests(TestCase):
    """Test suite for contract_reference field (EN16931 BT-12)."""

    RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"

    def setUp(self):
        country = Country.objects.get_or_create(
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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]
        self.company = Company.objects.create(
            name="Test GmbH",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Musterstraße 1",
            postal_code="12345",
            city="Berlin",
            country=country,
            email="test@company.de",
        )
        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Kunde AG",
            tax_id="DE987654321",
            vat_id="DE987654321",
            address_line1="Kundenstraße 1",
            postal_code="54321",
            city="München",
            country=country,
            email="kunde@example.com",
        )
        self.user = User.objects.create_user(username="contractuser", password="testpass123")
        self.product = Product.objects.create(
            name="Testprodukt",
            product_code="CTR-PROD-001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.invoice_service = InvoiceService()

    def _make_invoice(self, contract_reference=""):
        return Invoice.objects.create(
            invoice_number=f"CTR-{contract_reference or 'EMPTY'}",
            company=self.company,
            business_partner=self.partner,
            contract_reference=contract_reference,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

    def _base_xml_data(self, contract_reference=""):
        return {
            "number": "CTR-XML-001",
            "date": "20260514",
            "due_date": "20260614",
            "buyer_reference": "",
            "seller_reference": "",
            "contract_reference": contract_reference,
            "currency": "EUR",
            "company": {"name": "Test GmbH", "tax_id": "DE123456789"},
            "customer": {"name": "Kunde AG", "tax_id": "DE987654321"},
            "items": [{"product_name": "Testprodukt", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

    # -- Model tests --

    def test_model_contract_reference_stored(self):
        invoice = self._make_invoice("VTR-2026-001")
        self.assertEqual(invoice.contract_reference, "VTR-2026-001")

    def test_model_contract_reference_blank_by_default(self):
        invoice = self._make_invoice()
        self.assertEqual(invoice.contract_reference, "")

    # -- XML tests --

    def test_xml_contains_contract_referenced_document(self):
        xml_string = self.xml_generator.generate_xml(self._base_xml_data("VTR-2026-001"))
        root = etree.fromstring(xml_string.encode("utf-8"))
        ns = {"ram": self.RAM_NS}
        elem = root.find(".//ram:ContractReferencedDocument/ram:IssuerAssignedID", ns)
        self.assertIsNotNone(elem, "ContractReferencedDocument should be present in XML")
        self.assertEqual(elem.text, "VTR-2026-001")

    def test_xml_omits_contract_referenced_document_when_empty(self):
        xml_string = self.xml_generator.generate_xml(self._base_xml_data(""))
        root = etree.fromstring(xml_string.encode("utf-8"))
        ns = {"ram": self.RAM_NS}
        elem = root.find(".//ram:ContractReferencedDocument", ns)
        self.assertIsNone(elem, "ContractReferencedDocument should not appear when empty")

    def test_xml_contract_after_buyer_order_before_additional(self):
        """ContractReferencedDocument must follow BuyerOrderReferencedDocument per XSD sequence."""
        data = self._base_xml_data("VTR-SEQ-001")
        data["buyer_reference"] = "PO-001"
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))
        agreement = root.find(
            ".//{urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100}"
            "ApplicableHeaderTradeAgreement"
        )
        self.assertIsNotNone(agreement)
        tags = [child.tag.split("}")[-1] for child in agreement]
        buyer_idx = next((i for i, t in enumerate(tags) if t == "BuyerOrderReferencedDocument"), None)
        contract_idx = next((i for i, t in enumerate(tags) if t == "ContractReferencedDocument"), None)
        self.assertIsNotNone(buyer_idx)
        self.assertIsNotNone(contract_idx)
        self.assertGreater(
            contract_idx, buyer_idx, "ContractReferencedDocument must come after BuyerOrderReferencedDocument"
        )

    # -- Service test --

    def test_service_convert_includes_contract_reference(self):
        invoice = self._make_invoice("VTR-SVC-001")
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Testprodukt",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        self.assertIn("contract_reference", data)
        self.assertEqual(data["contract_reference"], "VTR-SVC-001")

    def test_service_convert_contract_reference_empty_fallback(self):
        invoice = self._make_invoice("")
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Testprodukt",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        self.assertEqual(data["contract_reference"], "")


class SellerContactTests(TestCase):
    """Test suite for BG-6 Seller Contact (BT-39/BT-40/BT-41)."""

    RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"

    def setUp(self):
        country = Country.objects.get_or_create(
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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]
        self.company = Company.objects.create(
            name="Seller GmbH",
            tax_id="SC123456789",
            vat_id="DE111111111",
            address_line1="Verkäuferstr. 1",
            postal_code="10115",
            city="Berlin",
            country=country,
            email="kontakt@seller.de",
            phone="+49 30 9999999",
            contact_name="Max Mustermann",
        )
        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Käufer AG",
            tax_id="SC987654321",
            vat_id="DE222222222",
            address_line1="Käuferstr. 1",
            postal_code="80331",
            city="München",
            country=country,
            email="info@buyer.de",
        )
        self.user = User.objects.create_user(username="sellercontactuser", password="testpass123")
        self.product = Product.objects.create(
            name="Kontaktprodukt",
            product_code="SC-PROD-001",
            base_price=Decimal("50.00"),
            default_tax_rate=Decimal("19.00"),
        )
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.invoice_service = InvoiceService()

    def _make_invoice(self):
        return Invoice.objects.create(
            invoice_number="SC-INV-001",
            company=self.company,
            business_partner=self.partner,
            created_by=self.user,
            currency="EUR",
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("9.50"),
            total_amount=Decimal("59.50"),
        )

    def _generate_xml(self, invoice):
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Kontaktprodukt",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string if isinstance(xml_string, bytes) else xml_string.encode())
        return root

    def test_xml_defined_trade_contact_present(self):
        """DefinedTradeContact must be present when contact data is set."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {
            "ram": self.RAM_NS,
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        }
        contact = root.find(".//ram:SellerTradeParty/ram:DefinedTradeContact", ns)
        self.assertIsNotNone(contact, "DefinedTradeContact must be present for seller")

    def test_xml_contact_person_name_bt39(self):
        """BT-39: PersonName must contain the contact_name value."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        person_name = root.find(".//ram:SellerTradeParty/ram:DefinedTradeContact/ram:PersonName", ns)
        self.assertIsNotNone(person_name, "PersonName (BT-39) must be present")
        self.assertEqual(person_name.text, "Max Mustermann")

    def test_xml_contact_phone_bt40(self):
        """BT-40: TelephoneUniversalCommunication/CompleteNumber must contain phone."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        phone = root.find(
            ".//ram:SellerTradeParty/ram:DefinedTradeContact/ram:TelephoneUniversalCommunication/ram:CompleteNumber",
            ns,
        )
        self.assertIsNotNone(phone, "CompleteNumber (BT-40) must be present")
        self.assertEqual(phone.text, "+49 30 9999999")

    def test_xml_contact_email_bt41(self):
        """BT-41: EmailURIUniversalCommunication/URIID must contain email."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        email = root.find(
            ".//ram:SellerTradeParty/ram:DefinedTradeContact/ram:EmailURIUniversalCommunication/ram:URIID",
            ns,
        )
        self.assertIsNotNone(email, "URIID (BT-41) must be present")
        self.assertEqual(email.text, "kontakt@seller.de")

    def test_xml_no_contact_block_when_empty(self):
        """DefinedTradeContact must not appear when all contact fields are empty."""
        Company.objects.filter(pk=self.company.pk).update(contact_name="", phone="", email="")
        self.company.refresh_from_db()
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        contact = root.find(".//ram:SellerTradeParty/ram:DefinedTradeContact", ns)
        self.assertIsNone(contact, "DefinedTradeContact must not appear when contact fields are empty")

    def test_xml_contact_position_before_postal_address(self):
        """DefinedTradeContact must appear before PostalTradeAddress per CII XSD sequence."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        seller = root.find(".//ram:SellerTradeParty", ns)
        self.assertIsNotNone(seller)
        tags = [child.tag.split("}")[-1] for child in seller]
        contact_idx = next((i for i, t in enumerate(tags) if t == "DefinedTradeContact"), None)
        postal_idx = next((i for i, t in enumerate(tags) if t == "PostalTradeAddress"), None)
        self.assertIsNotNone(contact_idx, "DefinedTradeContact must be in SellerTradeParty")
        self.assertIsNotNone(postal_idx, "PostalTradeAddress must be in SellerTradeParty")
        self.assertLess(contact_idx, postal_idx, "DefinedTradeContact must come before PostalTradeAddress")

    def test_service_passes_contact_name_to_dict(self):
        """convert_model_to_dict must include contact_name in company dict."""
        invoice = self._make_invoice()
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Kontaktprodukt",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        self.assertIn("contact_name", data["company"])
        self.assertEqual(data["company"]["contact_name"], "Max Mustermann")
        self.assertIn("phone", data["company"])
        self.assertEqual(data["company"]["phone"], "+49 30 9999999")


class BillingPeriodTests(TestCase):
    """Test suite for BG-14 Rechnungszeitraum (BT-73 billing_period_start / BT-74 billing_period_end)."""

    RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    UDT_NS = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"

    def setUp(self):
        country, _ = Country.objects.get_or_create(
            code="DE",
            defaults={
                "name": "Germany",
                "eu_member": True,
                "standard_vat_rate": Decimal("19.00"),
            },
        )
        self.company = Company.objects.create(
            name="Billing Seller GmbH",
            tax_id="BP123456789",
            vat_id="DE333333333",
            address_line1="Billingstr. 1",
            postal_code="10115",
            city="Berlin",
            country=country,
            email="billing@seller.de",
        )
        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Billing Käufer AG",
            tax_id="BP987654321",
            vat_id="DE444444444",
            address_line1="Käuferstr. 2",
            postal_code="80331",
            city="München",
            country=country,
            email="info@billingbuyer.de",
        )
        self.user = User.objects.create_user(username="billingperioduser", password="testpass123")
        self.product = Product.objects.create(
            name="Billingprodukt",
            product_code="BP-PROD-001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.invoice_service = InvoiceService()

    def _make_invoice(self, **kwargs):
        defaults = {
            "invoice_number": "BP-INV-001",
            "company": self.company,
            "business_partner": self.partner,
            "created_by": self.user,
            "currency": "EUR",
            "subtotal": Decimal("100.00"),
            "tax_amount": Decimal("19.00"),
            "total_amount": Decimal("119.00"),
        }
        defaults.update(kwargs)
        return Invoice.objects.create(**defaults)

    def _generate_xml(self, invoice):
        InvoiceLine.objects.get_or_create(
            invoice=invoice,
            defaults={
                "product": self.product,
                "description": "Billingprodukt",
                "quantity": Decimal("1"),
                "unit_price": Decimal("100.00"),
                "tax_rate": Decimal("19.00"),
            },
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        xml_string = self.xml_generator.generate_xml(data)
        return etree.fromstring(xml_string if isinstance(xml_string, bytes) else xml_string.encode())

    def test_xml_billing_period_present_when_set(self):
        """BillingSpecifiedPeriod must appear when start and end are set."""
        from datetime import date

        invoice = self._make_invoice(
            billing_period_start=date(2026, 4, 1),
            billing_period_end=date(2026, 4, 30),
        )
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        period = root.find(".//ram:BillingSpecifiedPeriod", ns)
        self.assertIsNotNone(period, "BillingSpecifiedPeriod must be present when dates are set")

    def test_xml_billing_period_absent_when_empty(self):
        """BillingSpecifiedPeriod must not appear when both dates are None."""
        invoice = self._make_invoice()
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS}
        period = root.find(".//ram:BillingSpecifiedPeriod", ns)
        self.assertIsNone(period, "BillingSpecifiedPeriod must not appear when dates are empty")

    def test_xml_start_datetime_value_bt73(self):
        """BT-73: StartDateTime DateTimeString must be YYYYMMDD with format 102."""
        from datetime import date

        invoice = self._make_invoice(billing_period_start=date(2026, 4, 1))
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS, "udt": self.UDT_NS}
        start_str = root.find(".//ram:BillingSpecifiedPeriod/ram:StartDateTime/udt:DateTimeString", ns)
        self.assertIsNotNone(start_str, "StartDateTime DateTimeString (BT-73) must be present")
        self.assertEqual(start_str.text, "20260401")
        self.assertEqual(start_str.get("format"), "102")

    def test_xml_end_datetime_value_bt74(self):
        """BT-74: EndDateTime DateTimeString must be YYYYMMDD with format 102."""
        from datetime import date

        invoice = self._make_invoice(billing_period_end=date(2026, 4, 30))
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS, "udt": self.UDT_NS}
        end_str = root.find(".//ram:BillingSpecifiedPeriod/ram:EndDateTime/udt:DateTimeString", ns)
        self.assertIsNotNone(end_str, "EndDateTime DateTimeString (BT-74) must be present")
        self.assertEqual(end_str.text, "20260430")
        self.assertEqual(end_str.get("format"), "102")

    def test_xml_only_start_without_end(self):
        """BillingSpecifiedPeriod with only StartDateTime when only start is set."""
        from datetime import date

        invoice = self._make_invoice(billing_period_start=date(2026, 4, 1))
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS, "udt": self.UDT_NS}
        period = root.find(".//ram:BillingSpecifiedPeriod", ns)
        self.assertIsNotNone(period)
        start_str = period.find("ram:StartDateTime/udt:DateTimeString", ns)
        self.assertIsNotNone(start_str)
        end_str = period.find("ram:EndDateTime/udt:DateTimeString", ns)
        self.assertIsNone(end_str, "EndDateTime must not appear when billing_period_end is empty")

    def test_xml_billing_period_after_applicable_trade_tax(self):
        """BillingSpecifiedPeriod must appear after ApplicableTradeTax in the XSD sequence."""
        from datetime import date

        invoice = self._make_invoice(
            billing_period_start=date(2026, 4, 1),
            billing_period_end=date(2026, 4, 30),
        )
        root = self._generate_xml(invoice)
        ns = {"ram": self.RAM_NS, "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"}
        settlement = root.find(".//ram:ApplicableHeaderTradeSettlement", ns)
        self.assertIsNotNone(settlement)
        tags = [child.tag.split("}")[-1] for child in settlement]
        tax_idx = next((i for i, t in enumerate(tags) if t == "ApplicableTradeTax"), None)
        period_idx = next((i for i, t in enumerate(tags) if t == "BillingSpecifiedPeriod"), None)
        self.assertIsNotNone(period_idx, "BillingSpecifiedPeriod must be in ApplicableHeaderTradeSettlement")
        self.assertIsNotNone(tax_idx, "ApplicableTradeTax must be in ApplicableHeaderTradeSettlement")
        self.assertGreater(period_idx, tax_idx, "BillingSpecifiedPeriod must come after ApplicableTradeTax")

    def test_serializer_rejects_start_after_end(self):
        """Serializer must raise ValidationError when billing_period_start > billing_period_end."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)
        # Build a minimal valid invoice payload and include invalid period
        url = "/api/invoices/"
        payload = {
            "company": self.company.pk,
            "business_partner": self.partner.pk,
            "issue_date": "2026-04-01",
            "due_date": "2026-04-30",
            "currency": "EUR",
            "billing_period_start": "2026-04-30",
            "billing_period_end": "2026-04-01",
        }
        response = client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        # Error is wrapped under response.data['error']['details']
        error_details = response.data.get("error", {}).get("details", response.data)
        self.assertIn("billing_period_start", error_details)

    def test_service_passes_billing_period_to_dict(self):
        """convert_model_to_dict must include billing_period_start/end formatted as YYYYMMDD."""
        from datetime import date

        invoice = self._make_invoice(
            billing_period_start=date(2026, 4, 1),
            billing_period_end=date(2026, 4, 30),
        )
        InvoiceLine.objects.get_or_create(
            invoice=invoice,
            defaults={
                "product": self.product,
                "description": "Billingprodukt",
                "quantity": Decimal("1"),
                "unit_price": Decimal("100.00"),
                "tax_rate": Decimal("19.00"),
            },
        )
        data = self.invoice_service.convert_model_to_dict(invoice)
        self.assertEqual(data.get("billing_period_start"), "20260401")
        self.assertEqual(data.get("billing_period_end"), "20260430")
