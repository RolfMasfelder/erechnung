"""
Tests for EN16931 3.17-J/K/L features:
- Payee (BG-10: BT-59/BT-60)
- Seller Tax Representative (BG-7/BG-8: BT-62-BT-69)
- Invoice Line Attributes / Product Characteristics (BG-32: BT-160/BT-161)

Validates the implementation across the entire stack: models, XML generation,
and the InvoiceService dict conversion.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from lxml import etree

from invoice_app.models import (
    BusinessPartner,
    Company,
    Country,
    Invoice,
    InvoiceLine,
    InvoiceLineAttribute,
    Product,
)
from invoice_app.services.invoice_service import InvoiceService
from invoice_app.utils.xml import ZugferdXmlGenerator


User = get_user_model()

_TEST_PW = "testpass123"
RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
NS = {"ram": RAM_NS}


class PayeeModelTests(TestCase):
    """Test suite for Invoice.payee_name / payee_id (BG-10)."""

    def setUp(self):
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
        )
        self.user = User.objects.create_user(username="testuser", password=_TEST_PW)

    def test_invoice_with_payee(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-PAYEE-001",
            company=self.company,
            business_partner=self.partner,
            payee_name="Factoring Bank AG",
            payee_id="FACT-12345",
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        self.assertEqual(invoice.payee_name, "Factoring Bank AG")
        self.assertEqual(invoice.payee_id, "FACT-12345")

    def test_invoice_without_payee_defaults_blank(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-PAYEE-002",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        self.assertEqual(invoice.payee_name, "")
        self.assertEqual(invoice.payee_id, "")


class TaxRepresentativeModelTests(TestCase):
    """Test suite for Company tax representative fields (BG-7/BG-8)."""

    def test_company_with_tax_representative(self):
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
        company = Company.objects.create(
            name="Foreign Seller Ltd",
            tax_id="FR123456789",
            vat_id="FR123456789",
            address_line1="Rue de Paris 1",
            postal_code="75001",
            city="Paris",
            country=country,
            email="test@seller.fr",
            tax_representative_name="Deutscher Steuervertreter GmbH",
            tax_representative_vat_id="DE999999999",
            tax_representative_address_line1="Steuerstrasse 1",
            tax_representative_postal_code="10115",
            tax_representative_city="Berlin",
            tax_representative_country="Deutschland",
        )
        self.assertEqual(company.tax_representative_name, "Deutscher Steuervertreter GmbH")
        self.assertEqual(company.tax_representative_vat_id, "DE999999999")

    def test_company_without_tax_representative_defaults_blank(self):
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
        company = Company.objects.create(
            name="Test GmbH",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Berlin",
            country=country,
            email="test@company.de",
        )
        self.assertEqual(company.tax_representative_name, "")
        self.assertEqual(company.tax_representative_vat_id, "")


class InvoiceLineAttributeModelTests(TestCase):
    """Test suite for the InvoiceLineAttribute model (BG-32)."""

    def setUp(self):
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
        )
        self.user = User.objects.create_user(username="testuser", password=_TEST_PW)
        self.invoice = Invoice.objects.create(
            invoice_number="INV-ATTR-001",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        self.line = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Custom Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )

    def test_create_attribute(self):
        attr = InvoiceLineAttribute.objects.create(invoice_line=self.line, name="Farbe", value="Rot")
        self.assertEqual(attr.name, "Farbe")
        self.assertEqual(attr.value, "Rot")
        self.assertEqual(str(attr), "Farbe: Rot")

    def test_attributes_ordered_by_sort_order(self):
        InvoiceLineAttribute.objects.create(invoice_line=self.line, name="B", value="2", sort_order=2)
        InvoiceLineAttribute.objects.create(invoice_line=self.line, name="A", value="1", sort_order=1)
        names = list(self.line.attributes.values_list("name", flat=True))
        self.assertEqual(names, ["A", "B"])

    def test_cascade_delete_with_invoice_line(self):
        InvoiceLineAttribute.objects.create(invoice_line=self.line, name="Farbe", value="Rot")
        self.line.delete()
        self.assertEqual(InvoiceLineAttribute.objects.count(), 0)


class PayeeXMLTests(TestCase):
    """Test suite for PayeeTradeParty XML generation (BG-10)."""

    def setUp(self):
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.base_data = {
            "number": "TEST-PAYEE-001",
            "date": "20260210",
            "due_date": "20260310",
            "currency": "EUR",
            "company": {"name": "Test GmbH", "tax_id": "DE123456789"},
            "customer": {"name": "Customer AG", "tax_id": "DE987654321"},
            "items": [{"product_name": "Test", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

    def test_xml_contains_payee_trade_party(self):
        data = dict(self.base_data, payee={"name": "Factoring Bank AG", "id": "FACT-12345"})
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        name_el = root.find(".//ram:PayeeTradeParty/ram:Name", NS)
        id_el = root.find(".//ram:PayeeTradeParty/ram:ID", NS)

        self.assertIsNotNone(name_el, "PayeeTradeParty/Name should exist in XML")
        self.assertEqual(name_el.text, "Factoring Bank AG")
        self.assertIsNotNone(id_el)
        self.assertEqual(id_el.text, "FACT-12345")

    def test_xml_omits_payee_trade_party_when_not_set(self):
        xml_string = self.xml_generator.generate_xml(self.base_data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        payee_el = root.find(".//ram:PayeeTradeParty", NS)
        self.assertIsNone(payee_el, "PayeeTradeParty should not exist when payee is not set")

    def test_xml_payee_without_id(self):
        data = dict(self.base_data, payee={"name": "Factoring Bank AG", "id": ""})
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        name_el = root.find(".//ram:PayeeTradeParty/ram:Name", NS)
        id_el = root.find(".//ram:PayeeTradeParty/ram:ID", NS)

        self.assertIsNotNone(name_el)
        self.assertEqual(name_el.text, "Factoring Bank AG")
        self.assertIsNone(id_el)


class TaxRepresentativeXMLTests(TestCase):
    """Test suite for SellerTaxRepresentativeTradeParty XML generation (BG-7/BG-8)."""

    def setUp(self):
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.base_data = {
            "number": "TEST-TAXREP-001",
            "date": "20260210",
            "due_date": "20260310",
            "currency": "EUR",
            "company": {"name": "Foreign Seller Ltd", "tax_id": "FR123456789"},
            "customer": {"name": "Customer AG", "tax_id": "DE987654321"},
            "items": [{"product_name": "Test", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        }

    def test_xml_contains_tax_representative_trade_party(self):
        data = dict(
            self.base_data,
            tax_representative={
                "name": "Deutscher Steuervertreter GmbH",
                "vat_id": "DE999999999",
                "street_name": "Steuerstrasse 1",
                "postcode_code": "10115",
                "city_name": "Berlin",
                "country_id": "DE",
            },
        )
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        name_el = root.find(".//ram:SellerTaxRepresentativeTradeParty/ram:Name", NS)
        vat_el = root.find(
            ".//ram:SellerTaxRepresentativeTradeParty/ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']", NS
        )

        self.assertIsNotNone(name_el, "SellerTaxRepresentativeTradeParty/Name should exist in XML")
        self.assertEqual(name_el.text, "Deutscher Steuervertreter GmbH")
        self.assertIsNotNone(vat_el)
        self.assertEqual(vat_el.text, "DE999999999")

    def test_xml_omits_tax_representative_when_not_set(self):
        xml_string = self.xml_generator.generate_xml(self.base_data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        tax_rep_el = root.find(".//ram:SellerTaxRepresentativeTradeParty", NS)
        self.assertIsNone(tax_rep_el, "SellerTaxRepresentativeTradeParty should not exist when not configured")


class ProductAttributeXMLTests(TestCase):
    """Test suite for ApplicableProductCharacteristic XML generation (BG-32)."""

    def setUp(self):
        self.xml_generator = ZugferdXmlGenerator(profile="COMFORT")
        self.base_data = {
            "number": "TEST-ATTR-001",
            "date": "20260210",
            "due_date": "20260310",
            "currency": "EUR",
            "company": {"name": "Test GmbH", "tax_id": "DE123456789"},
            "customer": {"name": "Customer AG", "tax_id": "DE987654321"},
        }

    def test_xml_contains_product_characteristics(self):
        data = dict(
            self.base_data,
            items=[
                {
                    "product_name": "Test",
                    "quantity": 1,
                    "price": 100.0,
                    "tax_rate": 19.0,
                    "attributes": [
                        {"name": "Farbe", "value": "Rot"},
                        {"name": "Groesse", "value": "L"},
                    ],
                }
            ],
        )
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        characteristics = root.findall(".//ram:SpecifiedTradeProduct/ram:ApplicableProductCharacteristic", NS)
        self.assertEqual(len(characteristics), 2)

        first_desc = characteristics[0].find("ram:Description", NS)
        first_value = characteristics[0].find("ram:Value", NS)
        self.assertEqual(first_desc.text, "Farbe")
        self.assertEqual(first_value.text, "Rot")

    def test_xml_omits_characteristics_when_no_attributes(self):
        data = dict(
            self.base_data,
            items=[{"product_name": "Test", "quantity": 1, "price": 100.0, "tax_rate": 19.0}],
        )
        xml_string = self.xml_generator.generate_xml(data)
        root = etree.fromstring(xml_string.encode("utf-8"))

        characteristics = root.findall(".//ram:ApplicableProductCharacteristic", NS)
        self.assertEqual(len(characteristics), 0)


class InvoiceServiceConversionTests(TestCase):
    """Integration tests for InvoiceService.convert_model_to_dict (BG-10/BG-7/BG-32)."""

    def setUp(self):
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
            tax_representative_name="Steuervertreter GmbH",
            tax_representative_vat_id="DE999999999",
            tax_representative_address_line1="Steuerstrasse 1",
            tax_representative_postal_code="10115",
            tax_representative_city="Berlin",
            tax_representative_country="Deutschland",
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
        )
        self.product = Product.objects.create(
            name="Test Product",
            product_code="PROD-001",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
        )
        self.user = User.objects.create_user(username="testuser", password=_TEST_PW)
        self.invoice_service = InvoiceService()

    def test_convert_model_to_dict_includes_payee(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-CONV-001",
            company=self.company,
            business_partner=self.partner,
            payee_name="Factoring Bank AG",
            payee_id="FACT-12345",
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )

        data = self.invoice_service.convert_model_to_dict(invoice)

        self.assertEqual(data["payee"]["name"], "Factoring Bank AG")
        self.assertEqual(data["payee"]["id"], "FACT-12345")

    def test_convert_model_to_dict_includes_tax_representative(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-CONV-002",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )

        data = self.invoice_service.convert_model_to_dict(invoice)

        self.assertEqual(data["tax_representative"]["name"], "Steuervertreter GmbH")
        self.assertEqual(data["tax_representative"]["vat_id"], "DE999999999")

    def test_convert_model_to_dict_includes_line_attributes(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-CONV-003",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        line = InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )
        InvoiceLineAttribute.objects.create(invoice_line=line, name="Farbe", value="Rot", sort_order=0)
        InvoiceLineAttribute.objects.create(invoice_line=line, name="Groesse", value="L", sort_order=1)

        data = self.invoice_service.convert_model_to_dict(invoice)

        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(
            data["items"][0]["attributes"],
            [{"name": "Farbe", "value": "Rot"}, {"name": "Groesse", "value": "L"}],
        )

    def test_convert_model_to_dict_line_without_attributes_is_empty_list(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-CONV-004",
            company=self.company,
            business_partner=self.partner,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
        )

        data = self.invoice_service.convert_model_to_dict(invoice)

        self.assertEqual(data["items"][0]["attributes"], [])
