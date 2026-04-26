"""
Tests for incoming XML utilities.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from django.test import TestCase
from lxml import etree

from invoice_app.utils.incoming_xml import (
    DEFAULT_COUNTRY,
    DEFAULT_POSTAL_CODE,
    PLACEHOLDER_TEXT,
    IncomingXmlParser,
    SupplierDataExtractor,
)


class IncomingXmlParserTestCase(TestCase):
    """Test IncomingXmlParser class."""

    def setUp(self):
        """Set up test data."""
        self.parser = IncomingXmlParser()

        # Sample minimal XML structure
        self.minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <CrossIndustryInvoice xmlns="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                             xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                             xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
            <ExchangedDocumentContext/>
            <ExchangedDocument>
                <ID>INV-001</ID>
                <TypeCode>380</TypeCode>
                <IssueDateTime>
                    <udt:DateTimeString>20240101</udt:DateTimeString>
                </IssueDateTime>
            </ExchangedDocument>
            <SupplyChainTradeTransaction>
                <ApplicableHeaderTradeAgreement>
                    <SellerTradeParty>
                        <ram:Name>Test Supplier</ram:Name>
                        <ram:ID>SUP001</ram:ID>
                    </SellerTradeParty>
                    <BuyerTradeParty>
                        <ram:Name>Test Buyer</ram:Name>
                    </BuyerTradeParty>
                </ApplicableHeaderTradeAgreement>
                <ApplicableHeaderTradeSettlement>
                    <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
                    <SpecifiedTradeSettlementHeaderMonetarySummation>
                        <GrandTotalAmount>100.00</GrandTotalAmount>
                        <TaxTotalAmount>19.00</TaxTotalAmount>
                    </SpecifiedTradeSettlementHeaderMonetarySummation>
                </ApplicableHeaderTradeSettlement>
            </SupplyChainTradeTransaction>
        </CrossIndustryInvoice>"""

    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = IncomingXmlParser()
        self.assertIsInstance(parser.NAMESPACES, dict)
        self.assertIn("inv", parser.NAMESPACES)
        self.assertIn("ram", parser.NAMESPACES)
        self.assertIn("udt", parser.NAMESPACES)

    def test_extract_invoice_data_minimal(self):
        """Test extracting invoice data from minimal XML."""
        # Create a simpler XML structure that matches the XPath patterns
        simple_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
            <inv:Header>
                <inv:ID>INV-001</inv:ID>
                <inv:TypeCode>380</inv:TypeCode>
                <inv:IssueDateTime>
                    <udt:DateTimeString>20240101</udt:DateTimeString>
                </inv:IssueDateTime>
            </inv:Header>
        </invoice>"""

        result = self.parser.extract_invoice_data(simple_xml)

        # Test basic structure
        self.assertIsInstance(result, dict)
        self.assertIn("invoice_number", result)
        self.assertIn("issue_date", result)
        self.assertIn("type_code", result)
        self.assertIn("currency", result)
        self.assertIn("line_items", result)

    def test_extract_text_method(self):
        """Test _extract_text helper method."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <inv:element>Test Value</inv:element>
        </root>"""

        root = etree.fromstring(xml.encode("utf-8"))

        # Test with existing element
        result = self.parser._extract_text(root, ".//inv:element", default="default")
        self.assertEqual(result, "Test Value")

        # Test with non-existing element
        result = self.parser._extract_text(root, ".//inv:missing", default="default")
        self.assertEqual(result, "default")

    def test_extract_amount_method(self):
        """Test _extract_amount helper method."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <inv:amount>123.45</inv:amount>
            <inv:invalid>not_a_number</inv:invalid>
        </root>"""

        root = etree.fromstring(xml.encode("utf-8"))

        # Test with valid amount
        result = self.parser._extract_amount(root, ".//inv:amount", default=0.0)
        self.assertEqual(result, 123.45)

        # Test with invalid amount
        result = self.parser._extract_amount(root, ".//inv:invalid", default=10.0)
        self.assertEqual(result, 10.0)

        # Test with missing element
        result = self.parser._extract_amount(root, ".//inv:missing", default=5.0)
        self.assertEqual(result, 5.0)

    def test_parse_date_method(self):
        """Test _parse_date helper method."""
        # Test with None element
        result = self.parser._parse_date(None)
        today = datetime.now().date().isoformat()
        self.assertEqual(result, today)

        # Test with YYYYMMDD format
        mock_elem = Mock()
        mock_elem.text = "20240315"
        result = self.parser._parse_date(mock_elem)
        self.assertEqual(result, "2024-03-15")

        # Test with already formatted date
        mock_elem.text = "2024-03-15"
        result = self.parser._parse_date(mock_elem)
        self.assertEqual(result, "2024-03-15")

        # Test with DD.MM.YYYY format
        mock_elem.text = "15.03.2024"
        result = self.parser._parse_date(mock_elem)
        self.assertEqual(result, "2024-03-15")

        # Test with invalid date format
        mock_elem.text = "invalid_date"
        result = self.parser._parse_date(mock_elem)
        today = datetime.now().date().isoformat()
        self.assertEqual(result, today)

    def test_extract_line_items_method(self):
        """Test _extract_line_items helper method."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <inv:LineItem>
                <inv:Description>Test Item 1</inv:Description>
                <inv:Quantity>2.0</inv:Quantity>
                <inv:UnitPrice>10.00</inv:UnitPrice>
                <inv:LineTotal>20.00</inv:LineTotal>
            </inv:LineItem>
            <inv:LineItem>
                <inv:Description>Test Item 2</inv:Description>
                <inv:Quantity>1.0</inv:Quantity>
                <inv:UnitPrice>15.00</inv:UnitPrice>
            </inv:LineItem>
        </root>"""

        root = etree.fromstring(xml.encode("utf-8"))
        result = self.parser._extract_line_items(root)

        self.assertEqual(len(result), 2)

        # Test first item
        item1 = result[0]
        self.assertEqual(item1["description"], "Test Item 1")
        self.assertEqual(item1["quantity"], 2.0)
        self.assertEqual(item1["unit_price"], 10.00)
        self.assertEqual(item1["line_total"], 20.00)

        # Test second item (without line total)
        item2 = result[1]
        self.assertEqual(item2["description"], "Test Item 2")
        self.assertEqual(item2["quantity"], 1.0)
        self.assertEqual(item2["unit_price"], 15.00)
        self.assertEqual(item2["line_total"], 15.0)  # quantity * unit_price

    def test_extract_invoice_data_malformed_xml(self):
        """Test handling of malformed XML."""
        malformed_xml = "This is not XML"

        with self.assertRaises(ValueError) as context:
            self.parser.extract_invoice_data(malformed_xml)

        self.assertIn("Error extracting invoice data from XML", str(context.exception))

    def test_extract_invoice_data_empty_xml(self):
        """Test handling of empty XML."""
        empty_xml = "<?xml version='1.0'?><root></root>"

        result = self.parser.extract_invoice_data(empty_xml)

        # Should return default values
        self.assertEqual(result["invoice_number"], "")
        self.assertEqual(result["type_code"], "380")
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["total_amount"], 0.0)
        self.assertEqual(result["line_items"], [])

    @patch("invoice_app.utils.incoming_xml.datetime")
    def test_parse_date_with_exception(self, mock_datetime):
        """Test _parse_date when datetime operations fail."""
        mock_datetime.now.return_value.date.return_value.isoformat.return_value = "2024-01-01"
        mock_datetime.strptime.side_effect = Exception("Test exception")

        mock_elem = Mock()
        mock_elem.text = "2024-01-01"

        result = self.parser._parse_date(mock_elem)
        self.assertEqual(result, "2024-01-01")

    def test_extract_invoice_data_with_unicode(self):
        """Test handling of XML with unicode characters."""
        unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <inv:Header>
                <inv:ID>INV-äöü-001</inv:ID>
            </inv:Header>
        </root>"""

        result = self.parser.extract_invoice_data(unicode_xml)
        self.assertEqual(result["invoice_number"], "INV-äöü-001")


class SupplierDataExtractorTestCase(TestCase):
    """Test SupplierDataExtractor class."""

    def setUp(self):
        """Set up test data."""
        self.extractor = SupplierDataExtractor()

        # Sample supplier XML
        self.supplier_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
            <inv:SellerTradeParty>
                <ram:Name>Test Supplier GmbH</ram:Name>
                <ram:SpecifiedTaxRegistration>
                    <ram:ID>DE123456789</ram:ID>
                </ram:SpecifiedTaxRegistration>
                <ram:PostalTradeAddress>
                    <ram:LineOne>Musterstraße 123</ram:LineOne>
                    <ram:CityName>Berlin</ram:CityName>
                    <ram:PostcodeCode>10115</ram:PostcodeCode>
                    <ram:CountryID>DE</ram:CountryID>
                </ram:PostalTradeAddress>
                <ram:DefinedTradeContact>
                    <ram:EmailURIUniversalCommunication>
                        <ram:URIID>contact@supplier.com</ram:URIID>
                    </ram:EmailURIUniversalCommunication>
                    <ram:TelephoneUniversalCommunication>
                        <ram:CompleteNumber>+49 30 12345678</ram:CompleteNumber>
                    </ram:TelephoneUniversalCommunication>
                </ram:DefinedTradeContact>
            </inv:SellerTradeParty>
        </invoice>"""

    def test_extractor_initialization(self):
        """Test extractor initialization."""
        extractor = SupplierDataExtractor()
        self.assertIsInstance(extractor, SupplierDataExtractor)

    def test_extract_supplier_info_complete(self):
        """Test extracting complete supplier information."""
        result = self.extractor.extract_supplier_info(self.supplier_xml)

        # Test all fields
        self.assertEqual(result["name"], "Test Supplier GmbH")
        self.assertEqual(result["tax_id"], "DE123456789")
        self.assertEqual(result["address_line1"], "Musterstraße 123")
        self.assertEqual(result["city"], "Berlin")
        self.assertEqual(result["postal_code"], "10115")
        self.assertEqual(result["country"], "DE")
        self.assertEqual(result["email"], "contact@supplier.com")
        self.assertEqual(result["phone"], "+49 30 12345678")

    def test_extract_supplier_info_minimal(self):
        """Test extracting supplier info with minimal data."""
        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
            <inv:SellerTradeParty>
                <ram:Name>Minimal Supplier</ram:Name>
            </inv:SellerTradeParty>
        </invoice>"""

        result = self.extractor.extract_supplier_info(minimal_xml)

        # Test that defaults are set
        self.assertEqual(result["name"], "Minimal Supplier")
        self.assertEqual(result["tax_id"], "")
        self.assertEqual(result["address_line1"], PLACEHOLDER_TEXT)
        self.assertEqual(result["city"], PLACEHOLDER_TEXT)
        self.assertEqual(result["postal_code"], DEFAULT_POSTAL_CODE)
        self.assertEqual(result["country"], DEFAULT_COUNTRY)
        self.assertEqual(result["email"], "")
        self.assertEqual(result["phone"], "")

    def test_extract_supplier_info_partial_address(self):
        """Test extracting supplier info with partial address."""
        partial_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
            <inv:SellerTradeParty>
                <ram:Name>Partial Supplier</ram:Name>
                <ram:PostalTradeAddress>
                    <ram:CityName>Munich</ram:CityName>
                    <ram:CountryID>DE</ram:CountryID>
                </ram:PostalTradeAddress>
            </inv:SellerTradeParty>
        </invoice>"""

        result = self.extractor.extract_supplier_info(partial_xml)

        self.assertEqual(result["name"], "Partial Supplier")
        self.assertEqual(result["address_line1"], PLACEHOLDER_TEXT)  # Missing
        self.assertEqual(result["city"], "Munich")  # Present
        self.assertEqual(result["postal_code"], DEFAULT_POSTAL_CODE)  # Missing
        self.assertEqual(result["country"], "DE")  # Present

    def test_extract_supplier_info_partial_contact(self):
        """Test extracting supplier info with partial contact."""
        partial_contact_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
            <inv:SellerTradeParty>
                <ram:Name>Contact Supplier</ram:Name>
                <ram:DefinedTradeContact>
                    <ram:EmailURIUniversalCommunication>
                        <ram:URIID>only@email.com</ram:URIID>
                    </ram:EmailURIUniversalCommunication>
                </ram:DefinedTradeContact>
            </inv:SellerTradeParty>
        </invoice>"""

        result = self.extractor.extract_supplier_info(partial_contact_xml)

        self.assertEqual(result["email"], "only@email.com")
        self.assertEqual(result["phone"], "")  # Missing

    def test_extract_supplier_info_malformed_xml(self):
        """Test handling of malformed XML."""
        malformed_xml = "This is not XML"

        with self.assertRaises(ValueError) as context:
            self.extractor.extract_supplier_info(malformed_xml)

        self.assertIn("Error extracting supplier data from XML", str(context.exception))

    def test_extract_supplier_info_empty_xml(self):
        """Test handling of empty XML."""
        empty_xml = "<?xml version='1.0'?><root></root>"

        result = self.extractor.extract_supplier_info(empty_xml)

        # Should return defaults
        self.assertEqual(result["name"], "")
        self.assertEqual(result["tax_id"], "")
        self.assertEqual(result["address_line1"], PLACEHOLDER_TEXT)
        self.assertEqual(result["city"], PLACEHOLDER_TEXT)
        self.assertEqual(result["postal_code"], DEFAULT_POSTAL_CODE)
        self.assertEqual(result["country"], DEFAULT_COUNTRY)
        self.assertEqual(result["email"], "")
        self.assertEqual(result["phone"], "")

    def test_extract_text_helper_method(self):
        """Test _extract_text helper method."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
            <inv:element>Helper Test</inv:element>
        </root>"""

        root = etree.fromstring(xml.encode("utf-8"))

        # Test with existing element
        result = self.extractor._extract_text(root, ".//inv:element", default="default")
        self.assertEqual(result, "Helper Test")

        # Test with non-existing element
        result = self.extractor._extract_text(root, ".//inv:missing", default="fallback")
        self.assertEqual(result, "fallback")

    def test_extract_supplier_with_unicode_characters(self):
        """Test handling of unicode characters in supplier data."""
        unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
            <inv:SellerTradeParty>
                <ram:Name>Müller &amp; Söhne GmbH</ram:Name>
                <ram:PostalTradeAddress>
                    <ram:LineOne>Königstraße 42</ram:LineOne>
                    <ram:CityName>Düsseldorf</ram:CityName>
                </ram:PostalTradeAddress>
            </inv:SellerTradeParty>
        </invoice>"""

        result = self.extractor.extract_supplier_info(unicode_xml)

        self.assertEqual(result["name"], "Müller & Söhne GmbH")
        self.assertEqual(result["address_line1"], "Königstraße 42")
        self.assertEqual(result["city"], "Düsseldorf")


class ConstantsTestCase(TestCase):
    """Test module constants."""

    def test_constants_values(self):
        """Test that constants have expected values."""
        self.assertEqual(PLACEHOLDER_TEXT, "[To be updated]")
        self.assertEqual(DEFAULT_POSTAL_CODE, "00000")
        self.assertEqual(DEFAULT_COUNTRY, "DE")

    def test_constants_types(self):
        """Test that constants have expected types."""
        self.assertIsInstance(PLACEHOLDER_TEXT, str)
        self.assertIsInstance(DEFAULT_POSTAL_CODE, str)
        self.assertIsInstance(DEFAULT_COUNTRY, str)


class IntegrationTestCase(TestCase):
    """Integration tests for both parser and extractor."""

    def test_combined_parsing_workflow(self):
        """Test using both parser and extractor on the same XML."""
        complex_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <invoice xmlns:inv="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                 xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                 xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
            <inv:Header>
                <inv:ID>COMPLEX-001</inv:ID>
                <inv:TypeCode>380</inv:TypeCode>
                <inv:IssueDateTime>
                    <udt:DateTimeString>20240301</udt:DateTimeString>
                </inv:IssueDateTime>
            </inv:Header>
            <inv:SellerTradeParty>
                <ram:Name>Complex Supplier Ltd</ram:Name>
                <ram:ID>COMP001</ram:ID>
                <ram:PostalTradeAddress>
                    <ram:LineOne>Business Park 1</ram:LineOne>
                    <ram:CityName>Hamburg</ram:CityName>
                    <ram:PostcodeCode>20095</ram:PostcodeCode>
                    <ram:CountryID>DE</ram:CountryID>
                </ram:PostalTradeAddress>
            </inv:SellerTradeParty>
            <inv:DocumentTotals>
                <inv:GrandTotal>500.00</inv:GrandTotal>
                <inv:TaxTotal>95.00</inv:TaxTotal>
                <inv:InvoiceCurrencyCode>EUR</inv:InvoiceCurrencyCode>
            </inv:DocumentTotals>
        </invoice>"""

        parser = IncomingXmlParser()
        extractor = SupplierDataExtractor()

        # Extract both types of data
        invoice_data = parser.extract_invoice_data(complex_xml)
        supplier_data = extractor.extract_supplier_info(complex_xml)

        # Verify invoice data
        self.assertEqual(invoice_data["invoice_number"], "COMPLEX-001")
        self.assertEqual(invoice_data["issue_date"], "2024-03-01")
        self.assertEqual(invoice_data["total_amount"], 500.0)

        # Verify supplier data
        self.assertEqual(supplier_data["name"], "Complex Supplier Ltd")
        self.assertEqual(supplier_data["city"], "Hamburg")
        self.assertEqual(supplier_data["postal_code"], "20095")

        # Both should handle the same XML without errors
        self.assertIsInstance(invoice_data, dict)
        self.assertIsInstance(supplier_data, dict)
