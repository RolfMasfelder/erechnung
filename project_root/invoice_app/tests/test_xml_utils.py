"""
Tests for the XML generation and validation utilities.
"""

import os
import tempfile

from django.test import TestCase
from lxml import etree

from invoice_app.utils.xml import ZugferdXmlGenerator, ZugferdXmlValidator


class TestZugferdXmlGenerator(TestCase):
    """Test suite for the ZUGFeRD XML generator."""

    def setUp(self):
        """Set up test data for XML generation."""
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")

        # Sample invoice data for testing
        self.sample_invoice_data = {
            "number": "INV-2023-001",
            "date": "20230501",
            "due_date": "20230531",
            "currency": "EUR",
            "issuer": {
                "name": "Test Supplier GmbH",
                "tax_id": "DE123456789",
                "address": "Supplier Street 123, Berlin",
                "email": "contact@supplier.com",
            },
            "customer": {
                "name": "Test Customer AG",
                "tax_id": "DE987654321",
                "address": "Customer Avenue 456, Munich",
                "email": "info@customer.com",
            },
            "items": [
                {"product_name": "Product A", "quantity": 2, "price": 100.00, "tax_rate": 19.0},
                {"product_name": "Product B", "quantity": 1, "price": 50.00, "tax_rate": 7.0},
            ],
        }

    def test_generate_xml_returns_string(self):
        """Test that the XML generator returns a string."""
        xml_string = self.xml_generator.generate_xml(self.sample_invoice_data)
        self.assertIsInstance(xml_string, str)
        self.assertTrue(xml_string.startswith("<?xml"))

    def test_generate_xml_contains_required_elements(self):
        """Test that the generated XML contains required elements."""
        xml_string = self.xml_generator.generate_xml(self.sample_invoice_data)

        # Parse the XML string
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        # Define namespaces for XPath queries
        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
        }

        # Check for ExchangedDocumentContext (required by CII schema)
        doc_context = xml_root.find(".//rsm:ExchangedDocumentContext", namespaces)
        self.assertIsNotNone(doc_context, "ExchangedDocumentContext element should exist")

        # Check for ExchangedDocument (new official structure)
        exchanged_doc = xml_root.find(".//rsm:ExchangedDocument", namespaces)
        self.assertIsNotNone(exchanged_doc, "ExchangedDocument element should exist")

        # Check for the invoice number in ExchangedDocument
        invoice_id = exchanged_doc.find(".//ram:ID", namespaces)
        self.assertIsNotNone(invoice_id, "ID element should exist in ExchangedDocument")
        self.assertEqual(invoice_id.text, self.sample_invoice_data["number"])

        # Check for TypeCode
        type_code = exchanged_doc.find(".//ram:TypeCode", namespaces)
        self.assertIsNotNone(type_code, "TypeCode should exist")
        self.assertEqual(type_code.text, "380")

        # Check for IssueDateTime
        issue_date = exchanged_doc.find(".//ram:IssueDateTime", namespaces)
        self.assertIsNotNone(issue_date, "IssueDateTime should exist")

        # Check for SupplyChainTradeTransaction (required by CII schema)
        transaction = xml_root.find(".//rsm:SupplyChainTradeTransaction", namespaces)
        self.assertIsNotNone(transaction, "SupplyChainTradeTransaction should exist")

        # Check for InvoiceCurrencyCode in ApplicableHeaderTradeSettlement
        settlement = transaction.find(".//ram:ApplicableHeaderTradeSettlement", namespaces)
        self.assertIsNotNone(settlement, "ApplicableHeaderTradeSettlement should exist")
        currency_code = settlement.find("ram:InvoiceCurrencyCode", namespaces)
        self.assertIsNotNone(currency_code, "InvoiceCurrencyCode should exist")
        self.assertEqual(currency_code.text, "EUR")

        # Check for ApplicableHeaderTradeAgreement with Seller and Buyer
        agreement = transaction.find(".//ram:ApplicableHeaderTradeAgreement", namespaces)
        self.assertIsNotNone(agreement, "ApplicableHeaderTradeAgreement should exist")

        # Check Seller party
        seller_party = agreement.find("ram:SellerTradeParty", namespaces)
        self.assertIsNotNone(seller_party, "SellerTradeParty should exist")
        seller_name = seller_party.find("ram:Name", namespaces)
        self.assertIsNotNone(seller_name, "Seller must have a Name")

        # Check seller address elements (official ZUGFeRD structure)
        seller_address = seller_party.find("ram:PostalTradeAddress", namespaces)
        self.assertIsNotNone(seller_address, "Seller must have PostalTradeAddress")
        city = seller_address.find("ram:CityName", namespaces)
        self.assertIsNotNone(city, "Address must have CityName")
        postcode = seller_address.find("ram:PostcodeCode", namespaces)
        self.assertIsNotNone(postcode, "Address must have PostcodeCode")
        country = seller_address.find("ram:CountryID", namespaces)
        self.assertIsNotNone(country, "Address must have CountryID")

        # Check Buyer party
        buyer_party = agreement.find("ram:BuyerTradeParty", namespaces)
        self.assertIsNotNone(buyer_party, "BuyerTradeParty should exist")
        buyer_name = buyer_party.find("ram:Name", namespaces)
        self.assertIsNotNone(buyer_name, "Buyer must have a Name")
        buyer_address = buyer_party.find("ram:PostalTradeAddress", namespaces)
        self.assertIsNotNone(buyer_address, "Buyer must have PostalTradeAddress")

    def test_line_items_structure(self):
        """Test that line items follow the official ZUGFeRD structure."""
        xml_string = self.xml_generator.generate_xml(self.sample_invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
        }

        # Should have 2 line items (from sample_invoice_data)
        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 2, "Should have 2 IncludedSupplyChainTradeLineItem elements")

        # Check first line item structure
        first_item = line_items[0]

        # 1. SpecifiedTradeProduct group
        product = first_item.find(".//ram:SpecifiedTradeProduct", namespaces)
        self.assertIsNotNone(product, "Must have SpecifiedTradeProduct")
        product_name = product.find(".//ram:Name", namespaces)
        self.assertIsNotNone(product_name, "Product must have Name")
        self.assertEqual(product_name.text, "Product A")

        # 2. SpecifiedLineTradeAgreement group
        agreement = first_item.find(".//ram:SpecifiedLineTradeAgreement", namespaces)
        self.assertIsNotNone(agreement, "Must have SpecifiedLineTradeAgreement")

        # NetPriceProductTradePrice
        net_price = agreement.find(".//ram:NetPriceProductTradePrice", namespaces)
        self.assertIsNotNone(net_price, "Must have NetPriceProductTradePrice")

        # BasisQuantity with unitCode attribute
        basis_qty = net_price.find(".//ram:BasisQuantity", namespaces)
        self.assertIsNotNone(basis_qty, "Must have BasisQuantity")
        self.assertEqual(basis_qty.get("unitCode"), "C62", "BasisQuantity must have unitCode='C62' (piece)")
        self.assertEqual(basis_qty.text, "1")  # Quantity for price basis

        # ChargeAmount
        charge_amount = net_price.find(".//ram:ChargeAmount", namespaces)
        self.assertIsNotNone(charge_amount, "Must have ChargeAmount")
        self.assertEqual(charge_amount.text, "100.00")

        # 3. SpecifiedLineTradeDelivery group
        delivery = first_item.find(".//ram:SpecifiedLineTradeDelivery", namespaces)
        self.assertIsNotNone(delivery, "Must have SpecifiedLineTradeDelivery")

        # BilledQuantity with MANDATORY unitCode attribute
        billed_qty = delivery.find(".//ram:BilledQuantity", namespaces)
        self.assertIsNotNone(billed_qty, "Must have BilledQuantity")
        self.assertEqual(billed_qty.get("unitCode"), "C62", "BilledQuantity MUST have unitCode attribute")
        self.assertEqual(billed_qty.text, "2.00")

        # 4. SpecifiedLineTradeSettlement group
        settlement = first_item.find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        self.assertIsNotNone(settlement, "Must have SpecifiedLineTradeSettlement")

        # ApplicableTradeTax
        trade_tax = settlement.find(".//ram:ApplicableTradeTax", namespaces)
        self.assertIsNotNone(trade_tax, "Must have ApplicableTradeTax")

        # TypeCode (always "VAT")
        type_code = trade_tax.find(".//ram:TypeCode", namespaces)
        self.assertIsNotNone(type_code, "Must have TypeCode")
        self.assertEqual(type_code.text, "VAT")

        # CategoryCode (S for standard rate, Z for zero rate)
        category_code = trade_tax.find(".//ram:CategoryCode", namespaces)
        self.assertIsNotNone(category_code, "Must have CategoryCode")
        self.assertEqual(category_code.text, "S", "19% tax should map to 'S' (standard)")

        # RateApplicablePercent
        rate_percent = trade_tax.find(".//ram:RateApplicablePercent", namespaces)
        self.assertIsNotNone(rate_percent, "Must have RateApplicablePercent")
        self.assertEqual(rate_percent.text, "19.00")

        # SpecifiedTradeSettlementLineMonetarySummation
        monetary_sum = settlement.find(".//ram:SpecifiedTradeSettlementLineMonetarySummation", namespaces)
        self.assertIsNotNone(monetary_sum, "Must have SpecifiedTradeSettlementLineMonetarySummation")

        # LineTotalAmount
        line_total = monetary_sum.find(".//ram:LineTotalAmount", namespaces)
        self.assertIsNotNone(line_total, "Must have LineTotalAmount")
        self.assertEqual(line_total.text, "200.00", "2 x 100.00 = 200.00")

        # Check second line item (7% tax rate should map to 'S')
        second_item = line_items[1]
        second_settlement = second_item.find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        second_tax = second_settlement.find(".//ram:ApplicableTradeTax", namespaces)
        second_category = second_tax.find(".//ram:CategoryCode", namespaces)
        self.assertEqual(second_category.text, "S", "7% tax should also map to 'S' (standard)")

    def test_applicable_header_trade_settlement(self):
        """Test ApplicableHeaderTradeSettlement with all 6 required monetary summary fields."""
        xml_string = self.xml_generator.generate_xml(self.sample_invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Find ApplicableHeaderTradeSettlement element
        settlement = xml_root.find(".//ram:ApplicableHeaderTradeSettlement", namespaces)
        self.assertIsNotNone(settlement, "Must have ApplicableHeaderTradeSettlement")

        # Find SpecifiedTradeSettlementHeaderMonetarySummation
        summation = settlement.find(".//ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces)
        self.assertIsNotNone(summation, "Must have SpecifiedTradeSettlementHeaderMonetarySummation")

        # === Check all 6 required fields ===

        # 1. LineTotalAmount (sum of line items: 2*100 + 1*50 = 250.00)
        line_total = summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertIsNotNone(line_total, "Must have LineTotalAmount")
        self.assertEqual(line_total.text, "250.00", "LineTotalAmount should be 2*100 + 1*50 = 250.00")

        # 2. ChargeTotalAmount (default 0.00)
        charge_total = summation.find(".//ram:ChargeTotalAmount", namespaces)
        self.assertIsNotNone(charge_total, "Must have ChargeTotalAmount")
        self.assertEqual(charge_total.text, "0.00", "ChargeTotalAmount should default to 0.00")

        # 3. AllowanceTotalAmount (default 0.00)
        allowance_total = summation.find(".//ram:AllowanceTotalAmount", namespaces)
        self.assertIsNotNone(allowance_total, "Must have AllowanceTotalAmount")
        self.assertEqual(allowance_total.text, "0.00", "AllowanceTotalAmount should default to 0.00")

        # 4. TaxBasisTotalAmount (LineTotalAmount - AllowanceTotalAmount + ChargeTotalAmount = 250.00 - 0 + 0)
        tax_basis = summation.find(".//ram:TaxBasisTotalAmount", namespaces)
        self.assertIsNotNone(tax_basis, "Must have TaxBasisTotalAmount")
        self.assertEqual(tax_basis.text, "250.00", "TaxBasisTotalAmount should be 250.00 - 0.00 + 0.00 = 250.00")

        # 5. TaxTotalAmount (2*100*0.19 + 1*50*0.07 = 38.00 + 3.50 = 41.50)
        tax_total = summation.find(".//ram:TaxTotalAmount", namespaces)
        self.assertIsNotNone(tax_total, "Must have TaxTotalAmount")
        self.assertEqual(tax_total.text, "41.50", "TaxTotalAmount should be 38.00 + 3.50 = 41.50")

        # 6. GrandTotalAmount (TaxBasisTotalAmount + TaxTotalAmount = 250.00 + 41.50 = 291.50)
        grand_total = summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertIsNotNone(grand_total, "Must have GrandTotalAmount")
        self.assertEqual(grand_total.text, "291.50", "GrandTotalAmount should be 250.00 + 41.50 = 291.50")

    def test_applicable_header_trade_settlement_with_charges_and_allowances(self):
        """Test ApplicableHeaderTradeSettlement with charges and allowances."""
        # Add charges and allowances to invoice data
        invoice_data_with_extras = self.sample_invoice_data.copy()
        invoice_data_with_extras["charge_total"] = 10.00  # Shipping charge
        invoice_data_with_extras["allowance_total"] = 20.00  # Discount

        xml_string = self.xml_generator.generate_xml(invoice_data_with_extras)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        summation = xml_root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces
        )
        self.assertIsNotNone(summation, "Must have SpecifiedTradeSettlementHeaderMonetarySummation")

        # LineTotalAmount (2*100 + 1*50 = 250.00)
        line_total = summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertEqual(line_total.text, "250.00")

        # ChargeTotalAmount (10.00)
        charge_total = summation.find(".//ram:ChargeTotalAmount", namespaces)
        self.assertEqual(charge_total.text, "10.00", "ChargeTotalAmount should be 10.00")

        # AllowanceTotalAmount (20.00)
        allowance_total = summation.find(".//ram:AllowanceTotalAmount", namespaces)
        self.assertEqual(allowance_total.text, "20.00", "AllowanceTotalAmount should be 20.00")

        # TaxBasisTotalAmount (250.00 - 20.00 + 10.00 = 240.00)
        tax_basis = summation.find(".//ram:TaxBasisTotalAmount", namespaces)
        self.assertEqual(tax_basis.text, "240.00", "TaxBasisTotalAmount should be 250.00 - 20.00 + 10.00 = 240.00")

        # TaxTotalAmount: adjusted per EN16931 (allowance/charge affect the taxable basis).
        # AllowanceTotalAmount(20) - ChargeTotalAmount(10) = net_discount 10.
        # 19%-group share 200/250=0.8 → adjusted_basis=192 → tax=36.48
        # 7%-group  share  50/250=0.2 → adjusted_basis= 48 → tax= 3.36
        # TaxTotalAmount = 36.48 + 3.36 = 39.84
        tax_total = summation.find(".//ram:TaxTotalAmount", namespaces)
        self.assertAlmostEqual(float(tax_total.text), 39.84, places=2)

        # GrandTotalAmount (240.00 + 39.84 = 279.84)
        grand_total = summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertAlmostEqual(
            float(grand_total.text), 279.84, places=2, msg="GrandTotalAmount should be 240.00 + 39.84 = 279.84"
        )

    def test_different_profiles(self):
        """Test XML generation with different profiles."""
        # NOTE: Profile-specific elements are currently not included in ExchangedDocument
        # This will be addressed in later phases when implementing full ZUGFeRD profile support
        # For now, we just verify that the generator accepts different profile parameters

        # Test with BASIC profile
        xml_basic = ZugferdXmlGenerator(profile="BASIC").generate_xml(self.sample_invoice_data)
        basic_root = etree.fromstring(xml_basic.encode("utf-8"))
        self.assertIsNotNone(basic_root, "XML should be generated for BASIC profile")

        # Test with COMFORT profile
        xml_comfort = ZugferdXmlGenerator(profile="COMFORT").generate_xml(self.sample_invoice_data)
        comfort_root = etree.fromstring(xml_comfort.encode("utf-8"))
        self.assertIsNotNone(comfort_root, "XML should be generated for COMFORT profile")

        # Test with EXTENDED profile
        xml_extended = ZugferdXmlGenerator(profile="EXTENDED").generate_xml(self.sample_invoice_data)
        extended_root = etree.fromstring(xml_extended.encode("utf-8"))
        self.assertIsNotNone(extended_root, "XML should be generated for EXTENDED profile")


class TestZugferdXmlValidator(TestCase):
    """Test suite for the ZUGFeRD XML validator."""

    def setUp(self):
        """Set up test data for XML validation."""
        self.xml_validator = ZugferdXmlValidator()
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")

        # Sample invoice data for testing
        self.sample_invoice_data = {
            "number": "INV-2023-001",
            "date": "20230501",
            "due_date": "20230531",
            "currency": "EUR",
            "issuer": {
                "name": "Test Supplier GmbH",
                "tax_id": "DE123456789",
                "vat_id": "DE123456789",
                "address": "Supplier Street 123, Berlin",
                "email": "contact@supplier.com",
            },
            "customer": {
                "name": "Test Customer AG",
                "tax_id": "DE987654321",
                "address": "Customer Avenue 456, Munich",
                "email": "info@customer.com",
            },
            "items": [
                {"product_name": "Product A", "quantity": 2, "price": 100.00, "tax_rate": 19.0},
            ],
        }

        # Generate valid XML
        self.valid_xml = self.xml_generator.generate_xml(self.sample_invoice_data)

    def test_validate_valid_xml(self):
        """Test validation of valid XML."""
        # Write XML to temporary file
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp_file:
            temp_file.write(self.valid_xml.encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            # Validate the XML file
            result = self.xml_validator.validate_file(temp_file_path)

            # Assuming our XML passes validation against our test schemas
            self.assertTrue(result.is_valid)
            self.assertEqual(len(result.errors), 0)
        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_validate_invalid_xml(self):
        """Test validation of invalid XML."""
        # Create invalid XML by removing required elements
        invalid_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rsm:Invoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <!-- Missing required elements -->
        </rsm:Invoice>
        """

        # Write XML to temporary file
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp_file:
            temp_file.write(invalid_xml.encode("utf-8"))
            temp_file_path = temp_file.name

        try:
            # Validate the XML file
            result = self.xml_validator.validate_file(temp_file_path)

            # If NoOp backend is used (no schemas available), validation will pass with warnings
            # If proper schemas are available, validation should fail
            if result.backend_used == "NoOp":
                # NoOp backend always returns valid=True but adds warnings
                self.assertTrue(result.is_valid)
                self.assertGreater(len(result.warnings), 0, "NoOp backend should add warnings")
            else:
                # With proper schemas, this invalid XML should fail validation
                self.assertFalse(result.is_valid)
                self.assertGreater(len(result.errors), 0)
        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_validate_xml_content(self):
        """Test validation of XML content (not file)."""
        # Validate direct XML content
        result = self.xml_validator.validate_xml(self.valid_xml)

        # Assuming our XML passes validation against our test schemas
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)


class TestZugferdXmlGeneratorEdgeCases(TestCase):
    """Test suite for edge cases in ZUGFeRD XML generator."""

    def setUp(self):
        """Set up test data for edge case testing."""
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")

    def test_empty_line_items(self):
        """Test XML generation with no line items."""
        invoice_data = {
            "number": "INV-2023-001",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {
                "name": "Test Supplier GmbH",
                "tax_id": "DE123456789",
                "address": "Supplier Street 123, Berlin",
            },
            "customer": {
                "name": "Test Customer AG",
                "tax_id": "DE987654321",
                "address": "Customer Avenue 456, Munich",
            },
            "items": [],  # Empty items list
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Should have no line items
        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 0, "Should have 0 line items")

        # Monetary summation should have zero values
        summation = xml_root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces
        )
        self.assertIsNotNone(summation)

        line_total = summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertEqual(line_total.text, "0.00", "LineTotalAmount should be 0.00 for empty items")

        grand_total = summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertEqual(grand_total.text, "0.00", "GrandTotalAmount should be 0.00 for empty items")

    def test_negative_quantities_credit_note(self):
        """Test XML generation with negative quantities (credit note/Gutschrift)."""
        invoice_data = {
            "number": "CN-2023-001",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {
                "name": "Test Supplier GmbH",
                "tax_id": "DE123456789",
                "address": "Supplier Street 123, Berlin",
            },
            "customer": {
                "name": "Test Customer AG",
                "tax_id": "DE987654321",
                "address": "Customer Avenue 456, Munich",
            },
            "items": [
                {"product_name": "Product A (Return)", "quantity": -2, "price": 100.00, "tax_rate": 19.0},
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Check that negative quantity is properly represented
        delivery = xml_root.find(".//ram:SpecifiedLineTradeDelivery", namespaces)
        billed_qty = delivery.find(".//ram:BilledQuantity", namespaces)
        self.assertEqual(billed_qty.text, "-2.00", "BilledQuantity should be negative")

        # Check that line total is negative
        settlement = xml_root.find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        monetary_sum = settlement.find(".//ram:SpecifiedTradeSettlementLineMonetarySummation", namespaces)
        line_total = monetary_sum.find(".//ram:LineTotalAmount", namespaces)
        self.assertEqual(line_total.text, "-200.00", "LineTotalAmount should be -2 × 100.00 = -200.00")

        # Check that grand total is negative
        header_summation = xml_root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces
        )
        grand_total = header_summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertEqual(grand_total.text, "-238.00", "GrandTotalAmount should be -200.00 - 38.00 = -238.00")

    def test_different_currencies(self):
        """Test XML generation with different currencies."""
        currencies_to_test = ["EUR", "USD", "GBP", "CHF", "JPY"]

        for currency in currencies_to_test:
            with self.subTest(currency=currency):
                invoice_data = {
                    "number": f"INV-{currency}-001",
                    "date": "20230501",
                    "currency": currency,
                    "issuer": {"name": "Test Supplier", "tax_id": "DE123456789", "address": "Test Street 1"},
                    "customer": {"name": "Test Customer", "tax_id": "DE987654321", "address": "Test Avenue 2"},
                    "items": [{"product_name": "Product", "quantity": 1, "price": 100.00, "tax_rate": 19.0}],
                }

                xml_string = self.xml_generator.generate_xml(invoice_data)
                xml_root = etree.fromstring(xml_string.encode("utf-8"))

                namespaces = {
                    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
                    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
                }

                # Check InvoiceCurrencyCode in ApplicableHeaderTradeSettlement (official CII structure)
                settlement = xml_root.find(".//ram:ApplicableHeaderTradeSettlement", namespaces)
                currency_code = settlement.find("ram:InvoiceCurrencyCode", namespaces)
                self.assertEqual(currency_code.text, currency, f"InvoiceCurrencyCode should be {currency}")

    def test_different_tax_rates(self):
        """Test XML generation with different tax rates (0%, 7%, 19%)."""
        invoice_data = {
            "number": "INV-2023-MIXED-TAX",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {"name": "Test Supplier", "tax_id": "DE123456789", "address": "Test Street 1"},
            "customer": {"name": "Test Customer", "tax_id": "DE987654321", "address": "Test Avenue 2"},
            "items": [
                {"product_name": "Product 0% Tax", "quantity": 1, "price": 100.00, "tax_rate": 0.0},
                {"product_name": "Product 7% Tax", "quantity": 1, "price": 100.00, "tax_rate": 7.0},
                {"product_name": "Product 19% Tax", "quantity": 1, "price": 100.00, "tax_rate": 19.0},
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 3, "Should have 3 line items")

        # Test 0% tax rate → CategoryCode should be "Z" (Zero rated)
        first_settlement = line_items[0].find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        first_tax = first_settlement.find(".//ram:ApplicableTradeTax", namespaces)
        first_category = first_tax.find(".//ram:CategoryCode", namespaces)
        self.assertEqual(first_category.text, "Z", "0% tax should map to CategoryCode 'Z' (Zero rated)")
        first_rate = first_tax.find(".//ram:RateApplicablePercent", namespaces)
        self.assertEqual(first_rate.text, "0.00")

        # Test 7% tax rate → CategoryCode should be "S" (Standard)
        second_settlement = line_items[1].find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        second_tax = second_settlement.find(".//ram:ApplicableTradeTax", namespaces)
        second_category = second_tax.find(".//ram:CategoryCode", namespaces)
        self.assertEqual(second_category.text, "S", "7% tax should map to CategoryCode 'S' (Standard)")
        second_rate = second_tax.find(".//ram:RateApplicablePercent", namespaces)
        self.assertEqual(second_rate.text, "7.00")

        # Test 19% tax rate → CategoryCode should be "S" (Standard)
        third_settlement = line_items[2].find(".//ram:SpecifiedLineTradeSettlement", namespaces)
        third_tax = third_settlement.find(".//ram:ApplicableTradeTax", namespaces)
        third_category = third_tax.find(".//ram:CategoryCode", namespaces)
        self.assertEqual(third_category.text, "S", "19% tax should map to CategoryCode 'S' (Standard)")
        third_rate = third_tax.find(".//ram:RateApplicablePercent", namespaces)
        self.assertEqual(third_rate.text, "19.00")

        # Check total calculations (100 + 100 + 100 = 300.00 net, 0 + 7 + 19 = 26.00 tax)
        header_summation = xml_root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces
        )
        line_total = header_summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertEqual(line_total.text, "300.00", "LineTotalAmount should be 300.00")
        tax_total = header_summation.find(".//ram:TaxTotalAmount", namespaces)
        self.assertEqual(tax_total.text, "26.00", "TaxTotalAmount should be 0.00 + 7.00 + 19.00 = 26.00")
        grand_total = header_summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertEqual(grand_total.text, "326.00", "GrandTotalAmount should be 300.00 + 26.00 = 326.00")

    def test_different_unit_codes(self):
        """Test XML generation with different unit codes (UN/ECE Rec. 20)."""
        invoice_data = {
            "number": "INV-2023-UNITS",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {"name": "Test Supplier", "tax_id": "DE123456789", "address": "Test Street 1"},
            "customer": {"name": "Test Customer", "tax_id": "DE987654321", "address": "Test Avenue 2"},
            "items": [
                {
                    "product_name": "Pieces",
                    "quantity": 10,
                    "price": 5.00,
                    "tax_rate": 19.0,
                    "unit_of_measure": "PCE",
                },
                {
                    "product_name": "Meters",
                    "quantity": 5.5,
                    "price": 10.00,
                    "tax_rate": 19.0,
                    "unit_of_measure": "MTR",
                },
                {
                    "product_name": "Hours",
                    "quantity": 8,
                    "price": 50.00,
                    "tax_rate": 19.0,
                    "unit_of_measure": "HUR",
                },
                {
                    "product_name": "Kilograms",
                    "quantity": 2.5,
                    "price": 20.00,
                    "tax_rate": 19.0,
                    "unit_of_measure": "KGM",
                },
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 4, "Should have 4 line items")

        # Expected unit codes mapping
        expected_units = [
            ("C62", "10.00"),  # PCE → C62 (Piece)
            ("MTR", "5.50"),  # MTR → MTR (Meter)
            ("HUR", "8.00"),  # HUR → HUR (Hour)
            ("KGM", "2.50"),  # KGM → KGM (Kilogram)
        ]

        for i, (expected_unit, expected_qty) in enumerate(expected_units):
            with self.subTest(index=i, unit=expected_unit):
                delivery = line_items[i].find(".//ram:SpecifiedLineTradeDelivery", namespaces)
                billed_qty = delivery.find(".//ram:BilledQuantity", namespaces)
                self.assertEqual(
                    billed_qty.get("unitCode"),
                    expected_unit,
                    f"Item {i} should have unitCode '{expected_unit}'",
                )
                self.assertEqual(billed_qty.text, expected_qty, f"Item {i} should have quantity {expected_qty}")

    def test_high_precision_decimals(self):
        """Test XML generation with high precision decimal values."""
        invoice_data = {
            "number": "INV-2023-PRECISION",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {"name": "Test Supplier", "tax_id": "DE123456789", "address": "Test Street 1"},
            "customer": {"name": "Test Customer", "tax_id": "DE987654321", "address": "Test Avenue 2"},
            "items": [
                {
                    "product_name": "High Precision Product",
                    "quantity": 3.333,
                    "price": 99.999,
                    "tax_rate": 19.0,
                },
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Check that values are properly rounded to 2 decimal places
        delivery = xml_root.find(".//ram:SpecifiedLineTradeDelivery", namespaces)
        billed_qty = delivery.find(".//ram:BilledQuantity", namespaces)
        # Quantity should be rounded
        self.assertEqual(billed_qty.text, "3.33", "Quantity should be rounded to 2 decimals")

        # Price should be rounded
        agreement = xml_root.find(".//ram:SpecifiedLineTradeAgreement", namespaces)
        net_price = agreement.find(".//ram:NetPriceProductTradePrice", namespaces)
        charge_amount = net_price.find(".//ram:ChargeAmount", namespaces)
        self.assertEqual(charge_amount.text, "100.00", "Price should be rounded to 2 decimals")

    def test_allowance_tax_basis_consistency_br_co_5(self):
        """EN16931 BR-CO-5: sum(ApplicableTradeTax/BasisAmount) == TaxBasisTotalAmount.

        When an invoice-level allowance or charge is present, BasisAmount per
        tax group must be adjusted proportionally so the constraint holds.
        """
        invoice_data = {
            "number": "INV-BRCO5-001",
            "date": "20260101",
            "currency": "EUR",
            "issuer": {"name": "Seller GmbH", "tax_id": "DE111222333", "address": "Str. 1"},
            "customer": {"name": "Buyer AG", "tax_id": "DE444555666", "address": "Str. 2"},
            # 100 EUR @ 19% + 200 EUR @ 7%  →  LineTotalAmount = 300.00
            "items": [
                {"product_name": "A", "quantity": 1, "price": 100.00, "tax_rate": 19.0},
                {"product_name": "B", "quantity": 2, "price": 100.00, "tax_rate": 7.0},
            ],
            "allowance_total": 30.00,  # 10% invoice-level discount
            "charge_total": 0.00,
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        root = etree.fromstring(xml_string.encode("utf-8"))
        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        # Collect all BasisAmount values (header-level only – line-level tax has no BasisAmount)
        basis_amounts = [
            float(el.text)
            for el in root.findall(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:BasisAmount", ns)
        ]
        tax_basis_total = float(
            root.find(".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:TaxBasisTotalAmount", ns).text
        )

        self.assertAlmostEqual(
            sum(basis_amounts),
            tax_basis_total,
            places=2,
            msg="BR-CO-5: sum(BasisAmount) must equal TaxBasisTotalAmount",
        )
        # LineTotalAmount(300) - AllowanceTotalAmount(30) = 270.00
        self.assertAlmostEqual(tax_basis_total, 270.00, places=2)
        # 19%-group share: 100/300 * 270 = 90.00
        # 7%-group share:  200/300 * 270 = 180.00
        ram_uri = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
        basis_by_group = {
            float(el.find(f"{{{ram_uri}}}RateApplicablePercent").text): float(
                el.find(f"{{{ram_uri}}}BasisAmount").text
            )
            for el in root.findall(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", ns)
        }
        self.assertAlmostEqual(basis_by_group[19.0], 90.00, places=2)
        self.assertAlmostEqual(basis_by_group[7.0], 180.00, places=2)

    def test_allowance_tax_calculated_amount_consistent(self):
        """CalculatedAmount must equal BasisAmount * RateApplicablePercent / 100 after allowance."""
        invoice_data = {
            "number": "INV-CALC-001",
            "date": "20260101",
            "currency": "EUR",
            "issuer": {"name": "Seller GmbH", "tax_id": "DE111222333", "address": "Str. 1"},
            "customer": {"name": "Buyer AG", "tax_id": "DE444555666", "address": "Str. 2"},
            "items": [
                {"product_name": "A", "quantity": 1, "price": 100.00, "tax_rate": 19.0},
            ],
            "allowance_total": 10.00,
            "charge_total": 0.00,
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        root = etree.fromstring(xml_string.encode("utf-8"))
        ns = {"ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"}

        ram_uri = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
        for tax_el in root.findall(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", ns):
            basis = float(tax_el.find(f"{{{ram_uri}}}BasisAmount").text)
            rate = float(tax_el.find(f"{{{ram_uri}}}RateApplicablePercent").text)
            calculated = float(tax_el.find(f"{{{ram_uri}}}CalculatedAmount").text)
            self.assertAlmostEqual(
                calculated,
                basis * rate / 100,
                places=2,
                msg=f"CalculatedAmount mismatch for rate {rate}%",
            )

    def test_multiple_items_same_product(self):
        """Test XML generation with multiple line items for the same product."""
        invoice_data = {
            "number": "INV-2023-DUPLICATE",
            "date": "20230501",
            "currency": "EUR",
            "issuer": {"name": "Test Supplier", "tax_id": "DE123456789", "address": "Test Street 1"},
            "customer": {"name": "Test Customer", "tax_id": "DE987654321", "address": "Test Avenue 2"},
            "items": [
                {"product_name": "Product A", "quantity": 5, "price": 10.00, "tax_rate": 19.0},
                {"product_name": "Product A", "quantity": 3, "price": 10.00, "tax_rate": 19.0},
                {"product_name": "Product A", "quantity": 2, "price": 10.00, "tax_rate": 19.0},
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        xml_root = etree.fromstring(xml_string.encode("utf-8"))

        namespaces = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        }

        # Should have 3 separate line items even for same product
        line_items = xml_root.findall(".//ram:IncludedSupplyChainTradeLineItem", namespaces)
        self.assertEqual(len(line_items), 3, "Should have 3 separate line items")

        # Check total: (5+3+2) × 10.00 × 1.19 = 100.00 net + 19.00 tax = 119.00
        header_summation = xml_root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", namespaces
        )
        line_total = header_summation.find(".//ram:LineTotalAmount", namespaces)
        self.assertEqual(line_total.text, "100.00", "LineTotalAmount should be (5+3+2) × 10.00 = 100.00")
        grand_total = header_summation.find(".//ram:GrandTotalAmount", namespaces)
        self.assertEqual(grand_total.text, "119.00", "GrandTotalAmount should be 100.00 + 19.00 = 119.00")

    def test_mixed_rates_with_header_allowance_br_s_08(self):
        """Zwei Positionen (7% / 19%) + Rechnungsrabatt → EN16931 BR-S-08 compliance.

        Regression test for Mustang error:
          [BR-S-08] BasisAmount must equal sum(line amounts) ± per-rate allowances/charges.

        Invoice:
          - Line 1: 1 × 1 000,00 @ 7%   → net  1 000,00
          - Line 2: 1 × 1 000,00 @ 19%  → net  1 000,00
          - Header allowance: 200,00 (Rechnungsrabatt, input tax_rate irrelevant)

        Expected XML after proportional split (50 % / 50 %):
          SpecifiedTradeAllowanceCharge: 100,00 @ 7%  and  100,00 @ 19%
          ApplicableTradeTax 7%:  BasisAmount = 900,00 · CalculatedAmount = 63,00
          ApplicableTradeTax 19%: BasisAmount = 900,00 · CalculatedAmount = 171,00
          AllowanceTotalAmount    = 200,00
          TaxBasisTotalAmount     = 1 800,00
          TaxTotalAmount          = 234,00
          GrandTotalAmount        = 2 034,00
        """
        invoice_data = {
            "number": "INV-2026-BR-S-08",
            "date": "20260220",
            "due_date": "20260320",
            "currency": "EUR",
            "issuer": {"name": "Verkäufer GmbH", "tax_id": "DE111222333", "address": "Str. 1"},
            "customer": {"name": "Käufer AG", "tax_id": "DE444555666", "address": "Str. 2"},
            "items": [
                {
                    "product_name": "Produkt 7%",
                    "quantity": 1,
                    "price": 1000.00,
                    "tax_rate": 7.0,
                    "line_total": 1000.00,
                },
                {
                    "product_name": "Produkt 19%",
                    "quantity": 1,
                    "price": 1000.00,
                    "tax_rate": 19.0,
                    "line_total": 1000.00,
                },
            ],
            # The single header-level allowance as the service layer would supply it.
            # The generator is expected to split it proportionally (100 @ 7%, 100 @ 19%).
            "allowances_charges": [
                {
                    "is_charge": False,
                    "actual_amount": 200.00,
                    "tax_rate": 19.0,  # original rate on the DB record – will be split
                    "reason": "Rechnungsrabatt",
                    "reason_code": "",
                    "calculation_percent": None,
                    "basis_amount": None,
                }
            ],
            "allowance_total": 200.00,
            "charge_total": 0.00,
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
        UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
        ns = {"ram": RAM, "udt": UDT}

        settlement = root.find(".//ram:ApplicableHeaderTradeSettlement", ns)
        self.assertIsNotNone(settlement)

        # ── SpecifiedTradeAllowanceCharge elements ──────────────────────────────
        acs = settlement.findall(f"{{{RAM}}}SpecifiedTradeAllowanceCharge")
        self.assertEqual(len(acs), 2, "Proportional split must produce 2 AllowanceCharge elements (one per rate)")

        ac_amounts = sorted(float(ac.find(f"{{{RAM}}}ActualAmount").text) for ac in acs)
        self.assertAlmostEqual(ac_amounts[0], 100.00, places=2, msg="Split AC amount (first) should be 100.00")
        self.assertAlmostEqual(ac_amounts[1], 100.00, places=2, msg="Split AC amount (second) should be 100.00")

        ac_rates = sorted(
            float(ac.find(f".//{{{RAM}}}CategoryTradeTax/{{{RAM}}}RateApplicablePercent").text) for ac in acs
        )
        self.assertEqual(ac_rates, [7.0, 19.0], "Split ACs must cover both 7% and 19% rates")

        # ── ApplicableTradeTax breakdowns ───────────────────────────────────────
        tax_elements = settlement.findall(f"{{{RAM}}}ApplicableTradeTax")
        self.assertEqual(len(tax_elements), 2, "Must have exactly 2 ApplicableTradeTax elements")

        tax_by_rate = {
            float(el.find(f"{{{RAM}}}RateApplicablePercent").text): {
                "basis": float(el.find(f"{{{RAM}}}BasisAmount").text),
                "calculated": float(el.find(f"{{{RAM}}}CalculatedAmount").text),
            }
            for el in tax_elements
        }

        self.assertAlmostEqual(tax_by_rate[7.0]["basis"], 900.00, places=2, msg="BasisAmount 7% must be 900.00")
        self.assertAlmostEqual(tax_by_rate[19.0]["basis"], 900.00, places=2, msg="BasisAmount 19% must be 900.00")
        self.assertAlmostEqual(
            tax_by_rate[7.0]["calculated"], 63.00, places=2, msg="CalculatedAmount 7% must be 63.00"
        )
        self.assertAlmostEqual(
            tax_by_rate[19.0]["calculated"], 171.00, places=2, msg="CalculatedAmount 19% must be 171.00"
        )

        # ── Monetary summation ──────────────────────────────────────────────────
        summation = settlement.find(f"{{{RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation")
        self.assertIsNotNone(summation)

        def _amt(tag):
            return float(summation.find(f"{{{RAM}}}{tag}").text)

        self.assertAlmostEqual(_amt("LineTotalAmount"), 2000.00, places=2)
        self.assertAlmostEqual(_amt("AllowanceTotalAmount"), 200.00, places=2)
        self.assertAlmostEqual(_amt("ChargeTotalAmount"), 0.00, places=2)
        self.assertAlmostEqual(_amt("TaxBasisTotalAmount"), 1800.00, places=2)
        self.assertAlmostEqual(_amt("TaxTotalAmount"), 234.00, places=2)
        self.assertAlmostEqual(_amt("GrandTotalAmount"), 2034.00, places=2)

        # ── BR-CO-5: sum(BasisAmount) == TaxBasisTotalAmount ──────────────────
        basis_sum = sum(d["basis"] for d in tax_by_rate.values())
        self.assertAlmostEqual(
            basis_sum,
            _amt("TaxBasisTotalAmount"),
            places=2,
            msg="BR-CO-5: sum(BasisAmount) must equal TaxBasisTotalAmount",
        )

        # ── BR-S-08 consistency check ─────────────────────────────────────────
        # For each rate: BasisAmount == sum(line totals at rate) - sum(allowances at rate)
        line_totals_by_rate = {7.0: 1000.00, 19.0: 1000.00}
        allowance_by_rate = {}
        for ac in acs:
            rate = float(ac.find(f".//{{{RAM}}}CategoryTradeTax/{{{RAM}}}RateApplicablePercent").text)
            is_charge = ac.find(f"{{{RAM}}}ChargeIndicator/{{{UDT}}}Indicator").text.lower() == "true"
            amount = float(ac.find(f"{{{RAM}}}ActualAmount").text)
            delta = amount if is_charge else -amount
            allowance_by_rate[rate] = allowance_by_rate.get(rate, 0.0) + delta

        for rate in [7.0, 19.0]:
            expected_basis = line_totals_by_rate[rate] + allowance_by_rate.get(rate, 0.0)
            self.assertAlmostEqual(
                tax_by_rate[rate]["basis"],
                expected_basis,
                places=2,
                msg=f"BR-S-08 violation for rate {rate}%: BasisAmount {tax_by_rate[rate]['basis']} "
                f"!= {expected_basis}",
            )

    def test_br_co_14_tax_total_equals_sum_of_calculated_amounts(self):
        """BR-CO-14: TaxTotalAmount must equal Σ CalculatedAmount (per-rate rounded values).

        Regression test for Mustang error on invoice INV-2026-0004:
          "Invoice total VAT amount (BT-110) = Σ VAT category tax amount (BT-117)"
          Warning: "Payable total in XML is 3418.45, but calculated total is 3418.46"

        Root cause: _add_monetary_summation summed unrounded float products, while
        _add_applicable_trade_tax wrote individually _format_decimal()-rounded values.
        With two tax rates the accumulated rounding can differ by ±0.01.

        Invoice that triggers the bug:
          - Line 1: 3 × 300.00 = 900.00 @ 7%
          - Line 2: 6 × 400.00 = 2400.00 @ 19%
          → Tax 7%:  900.00 × 0.07 =  63.00
          → Tax 19%: 2400.00 × 0.19 = 456.00
          → TaxTotal = 519.00  (both values clean here)

        To specifically trigger floating-point divergence we use non-round bases:
          - Line 1: 1 × 333.33 = 333.33 @ 7%   → tax = 23.33 (rounded from 23.3331)
          - Line 2: 1 × 333.34 = 333.34 @ 19%  → tax = 63.33 (rounded from 63.3346)
          → Σ CalculatedAmount = 23.33 + 63.33 = 86.66
          → TaxTotalAmount must be 86.66, not some independently rounded value.
        """
        invoice_data = {
            "number": "INV-2026-BR-CO-14",
            "date": "20260221",
            "currency": "EUR",
            "issuer": {"name": "Verkäufer GmbH", "tax_id": "DE111222333", "address": "Str. 1"},
            "customer": {"name": "Käufer AG", "tax_id": "DE444555666", "address": "Str. 2"},
            "items": [
                {
                    "product_name": "Pos 1 (7%)",
                    "quantity": 1,
                    "price": 333.33,
                    "tax_rate": 7.0,
                    "line_total": 333.33,
                },
                {
                    "product_name": "Pos 2 (19%)",
                    "quantity": 1,
                    "price": 333.34,
                    "tax_rate": 19.0,
                    "line_total": 333.34,
                },
            ],
        }

        xml_string = self.xml_generator.generate_xml(invoice_data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
        ns = {"ram": RAM}

        settlement = root.find(".//ram:ApplicableHeaderTradeSettlement", ns)

        # Collect individual CalculatedAmount values as written to XML
        tax_elements = settlement.findall(f"{{{RAM}}}ApplicableTradeTax")
        calculated_amounts = [float(el.find(f"{{{RAM}}}CalculatedAmount").text) for el in tax_elements]

        summation = settlement.find(f"{{{RAM}}}SpecifiedTradeSettlementHeaderMonetarySummation")
        tax_total_in_xml = float(summation.find(f"{{{RAM}}}TaxTotalAmount").text)

        # BR-CO-14: TaxTotalAmount must equal sum of individually-rounded CalculatedAmounts
        expected_tax_total = round(sum(calculated_amounts), 2)
        self.assertAlmostEqual(
            tax_total_in_xml,
            expected_tax_total,
            places=2,
            msg=(
                f"BR-CO-14 violation: TaxTotalAmount={tax_total_in_xml} but "
                f"Σ CalculatedAmount={expected_tax_total} "
                f"(individual values: {calculated_amounts})"
            ),
        )
