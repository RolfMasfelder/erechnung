"""
Tests for BusinessPartner Tax Logic (Task 1.2).

Covers three tax scenarios:
1. Domestic (Inland): Company & customer in same country → normal VAT
2. EU Reverse Charge: Different EU country + valid VAT ID → 0%, category AE
3. Export (Drittland): Non-EU country → 0%, category G

Also tests:
- VAT ID format validation
- Product.get_tax_rate_for_partner() with TaxService integration
- InvoiceLine.tax_category_code property
- TaxService.determine_tax_scenario()
- TaxService.get_tax_determination()
"""

from decimal import Decimal

from django.test import TestCase

from invoice_app.models.business_partner import BusinessPartner
from invoice_app.models.company import Company
from invoice_app.models.country import Country, CountryTaxRate
from invoice_app.models.invoice_models import Invoice, InvoiceLine
from invoice_app.models.product import Product
from invoice_app.services.tax_service import EXEMPTION_REASONS, TaxDetermination, TaxScenario, TaxService


class TaxScenarioTestMixin:
    """
    Common test data setup for tax scenario tests.
    Creates Germany (domestic), France (EU), and Switzerland (non-EU) countries,
    plus an active company in Germany.
    """

    @classmethod
    def setUpTestData(cls):
        # Countries (use get_or_create since PK is the code and tests share DB)
        cls.germany, _ = Country.objects.get_or_create(
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
                "reduced_vat_rate": Decimal("7.00"),
            },
        )
        cls.france, _ = Country.objects.get_or_create(
            code="FR",
            defaults={
                "code_alpha3": "FRA",
                "numeric_code": "250",
                "name": "France",
                "name_local": "France",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "fr",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": Decimal("20.00"),
                "reduced_vat_rate": Decimal("5.50"),
            },
        )
        cls.austria, _ = Country.objects.get_or_create(
            code="AT",
            defaults={
                "code_alpha3": "AUT",
                "numeric_code": "040",
                "name": "Austria",
                "name_local": "Österreich",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": Decimal("20.00"),
                "reduced_vat_rate": Decimal("10.00"),
            },
        )
        cls.switzerland, _ = Country.objects.get_or_create(
            code="CH",
            defaults={
                "code_alpha3": "CHE",
                "numeric_code": "756",
                "name": "Switzerland",
                "name_local": "Schweiz",
                "currency_code": "CHF",
                "currency_name": "Swiss Franc",
                "currency_symbol": "CHF",
                "default_language": "de",
                "is_eu_member": False,
                "is_eurozone": False,
                "standard_vat_rate": Decimal("8.10"),
                "reduced_vat_rate": Decimal("2.60"),
            },
        )
        cls.usa, _ = Country.objects.get_or_create(
            code="US",
            defaults={
                "code_alpha3": "USA",
                "numeric_code": "840",
                "name": "United States",
                "name_local": "United States",
                "currency_code": "USD",
                "currency_name": "US Dollar",
                "currency_symbol": "$",
                "default_language": "en",
                "is_eu_member": False,
                "is_eurozone": False,
                "standard_vat_rate": Decimal("0.00"),
            },
        )

        # CountryTaxRate for Germany
        from django.utils import timezone

        today = timezone.now().date()
        CountryTaxRate.objects.create(
            country=cls.germany,
            rate_type=CountryTaxRate.RateType.STANDARD,
            rate=Decimal("19.00"),
            valid_from=today,
            is_active=True,
        )
        CountryTaxRate.objects.create(
            country=cls.germany,
            rate_type=CountryTaxRate.RateType.REDUCED,
            rate=Decimal("7.00"),
            valid_from=today,
            is_active=True,
        )

        # Company (German)
        cls.company = Company.objects.create(
            name="Test GmbH",
            tax_id="12/345/67890",
            vat_id="DE123456789",
            address_line1="Musterstraße 1",
            postal_code="12345",
            city="Berlin",
            country="Deutschland",
        )

        # Product with standard rate
        cls.product_standard = Product.objects.create(
            product_code="PROD-STD-001",
            name="Standard Product",
            base_price=Decimal("100.00"),
            default_tax_rate=Decimal("19.00"),
            tax_category=Product.TaxCategory.STANDARD,
        )

        # Product with reduced rate
        cls.product_reduced = Product.objects.create(
            product_code="PROD-RED-001",
            name="Reduced Product",
            base_price=Decimal("50.00"),
            default_tax_rate=Decimal("7.00"),
            tax_category=Product.TaxCategory.REDUCED,
        )

        # Product with zero rate
        cls.product_zero = Product.objects.create(
            product_code="PROD-ZERO-001",
            name="Zero Rate Product",
            base_price=Decimal("25.00"),
            default_tax_rate=Decimal("0.00"),
            tax_category=Product.TaxCategory.ZERO,
        )


# ==============================================================================
# TaxService.determine_tax_scenario Tests
# ==============================================================================
class TaxServiceScenarioTests(TaxScenarioTestMixin, TestCase):
    """Tests for TaxService.determine_tax_scenario()."""

    def test_domestic_same_country(self):
        """German customer → DOMESTIC."""
        partner = BusinessPartner.objects.create(
            company_name="Inlandskunde GmbH",
            address_line1="Teststr. 1",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
            vat_id="DE987654321",
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.DOMESTIC)

    def test_eu_reverse_charge_with_valid_vat_id(self):
        """French customer with valid VAT ID → EU_REVERSE_CHARGE."""
        partner = BusinessPartner.objects.create(
            company_name="Société Française SARL",
            address_line1="1 Rue de Test",
            postal_code="75001",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.EU_REVERSE_CHARGE)

    def test_eu_without_vat_id_stays_domestic(self):
        """French customer without VAT ID → DOMESTIC (B2C case)."""
        partner = BusinessPartner.objects.create(
            company_name="Particulier",
            address_line1="2 Rue de Test",
            postal_code="75002",
            city="Paris",
            country=self.france,
            vat_id="",
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.DOMESTIC)

    def test_eu_with_invalid_vat_id_stays_domestic(self):
        """French customer with invalid VAT ID → DOMESTIC."""
        partner = BusinessPartner.objects.create(
            company_name="Bad VAT SARL",
            address_line1="3 Rue de Test",
            postal_code="75003",
            city="Paris",
            country=self.france,
            vat_id="FR1",  # Too short for French format
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.DOMESTIC)

    def test_export_non_eu_country(self):
        """Swiss customer → EXPORT."""
        partner = BusinessPartner.objects.create(
            company_name="Schweizer AG",
            address_line1="Bahnhofstrasse 1",
            postal_code="8001",
            city="Zürich",
            country=self.switzerland,
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.EXPORT)

    def test_export_usa_customer(self):
        """US customer → EXPORT."""
        partner = BusinessPartner.objects.create(
            company_name="American Corp",
            address_line1="123 Main St",
            postal_code="10001",
            city="New York",
            country=self.usa,
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.EXPORT)

    def test_no_partner_defaults_to_domestic(self):
        """No partner → DOMESTIC."""
        result = TaxService.determine_tax_scenario("DE", None)
        self.assertEqual(result, TaxScenario.DOMESTIC)

    def test_partner_without_country_defaults_to_domestic(self):
        """Partner without country → DOMESTIC."""
        partner = BusinessPartner.objects.create(
            company_name="No Country GmbH",
            address_line1="Teststr. 1",
            postal_code="10115",
            city="Berlin",
            country=None,
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.DOMESTIC)

    def test_austrian_customer_with_valid_vat_id(self):
        """Austrian customer with valid VAT ID → EU_REVERSE_CHARGE."""
        partner = BusinessPartner.objects.create(
            company_name="Wiener GmbH",
            address_line1="Kärntner Straße 1",
            postal_code="1010",
            city="Wien",
            country=self.austria,
            vat_id="ATU12345678",
        )
        result = TaxService.determine_tax_scenario("DE", partner)
        self.assertEqual(result, TaxScenario.EU_REVERSE_CHARGE)


# ==============================================================================
# TaxService.get_tax_determination Tests
# ==============================================================================
class TaxDeterminationTests(TaxScenarioTestMixin, TestCase):
    """Tests for TaxService.get_tax_determination()."""

    def test_domestic_standard_rate(self):
        """Domestic customer → standard 19% rate, category S."""
        partner = BusinessPartner.objects.create(
            company_name="Inland GmbH",
            address_line1="Teststr. 1",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("19.00"),
            product_tax_category="STANDARD",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.scenario, TaxScenario.DOMESTIC)
        self.assertEqual(result.tax_rate, Decimal("19.00"))
        self.assertEqual(result.tax_category_code, "S")
        self.assertEqual(result.exemption_reason, "")

    def test_domestic_reduced_rate(self):
        """Domestic customer → reduced 7% rate, category S."""
        partner = BusinessPartner.objects.create(
            company_name="Inland Reduced GmbH",
            address_line1="Teststr. 2",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("7.00"),
            product_tax_category="REDUCED",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.tax_rate, Decimal("7.00"))
        self.assertEqual(result.tax_category_code, "S")

    def test_domestic_zero_rate(self):
        """Domestic with zero rate product → category Z."""
        partner = BusinessPartner.objects.create(
            company_name="Inland Zero GmbH",
            address_line1="Teststr. 3",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("0.00"),
            product_tax_category="ZERO",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.tax_rate, Decimal("0.00"))
        self.assertEqual(result.tax_category_code, "Z")

    def test_domestic_exempt(self):
        """Domestic with exempt product → category E."""
        partner = BusinessPartner.objects.create(
            company_name="Inland Exempt GmbH",
            address_line1="Teststr. 4",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("0.00"),
            product_tax_category="EXEMPT",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.tax_category_code, "E")

    def test_eu_reverse_charge(self):
        """EU customer with VAT ID → 0%, AE, with exemption reason."""
        partner = BusinessPartner.objects.create(
            company_name="FR Company SARL",
            address_line1="4 Rue de Test",
            postal_code="75004",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("19.00"),
            product_tax_category="STANDARD",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.scenario, TaxScenario.EU_REVERSE_CHARGE)
        self.assertEqual(result.tax_rate, Decimal("0.00"))
        self.assertEqual(result.tax_category_code, "AE")
        self.assertIn("Reverse Charge", result.exemption_reason)

    def test_export_third_country(self):
        """Non-EU customer → 0%, G, with export exemption reason."""
        partner = BusinessPartner.objects.create(
            company_name="Swiss AG",
            address_line1="Bahnhofstr. 2",
            postal_code="8002",
            city="Zürich",
            country=self.switzerland,
        )
        result = TaxService.get_tax_determination(
            product_tax_rate=Decimal("19.00"),
            product_tax_category="STANDARD",
            company_country_code="DE",
            partner=partner,
        )
        self.assertEqual(result.scenario, TaxScenario.EXPORT)
        self.assertEqual(result.tax_rate, Decimal("0.00"))
        self.assertEqual(result.tax_category_code, "G")
        self.assertIn("Ausfuhrlieferung", result.exemption_reason)


# ==============================================================================
# VAT ID Format Validation Tests
# ==============================================================================
class VatIdValidationTests(TestCase):
    """Tests for TaxService.validate_vat_id_format()."""

    def test_valid_german_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("DE123456789"))

    def test_valid_french_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("FR12345678901"))

    def test_valid_austrian_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("ATU12345678"))

    def test_valid_dutch_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("NL123456789B01"))

    def test_valid_italian_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("IT12345678901"))

    def test_valid_spanish_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("ESA12345678"))

    def test_valid_polish_vat_id(self):
        self.assertTrue(TaxService.validate_vat_id_format("PL1234567890"))

    def test_invalid_german_vat_id_too_short(self):
        self.assertFalse(TaxService.validate_vat_id_format("DE12345"))

    def test_invalid_german_vat_id_too_long(self):
        self.assertFalse(TaxService.validate_vat_id_format("DE1234567890"))

    def test_invalid_empty_string(self):
        self.assertFalse(TaxService.validate_vat_id_format(""))

    def test_invalid_none(self):
        self.assertFalse(TaxService.validate_vat_id_format(None))

    def test_invalid_too_short(self):
        self.assertFalse(TaxService.validate_vat_id_format("DE"))

    def test_case_insensitive(self):
        self.assertTrue(TaxService.validate_vat_id_format("de123456789"))

    def test_strips_whitespace(self):
        self.assertTrue(TaxService.validate_vat_id_format("  DE123456789  "))

    def test_unknown_country_prefix_allows_reasonable_length(self):
        """Unknown country prefix should still pass if long enough."""
        self.assertTrue(TaxService.validate_vat_id_format("XX123456789"))

    def test_unknown_country_prefix_rejects_short(self):
        """Unknown country prefix too short → reject."""
        self.assertFalse(TaxService.validate_vat_id_format("XX1"))


# ==============================================================================
# Product.get_tax_rate_for_partner Integration Tests
# ==============================================================================
class ProductTaxRateForPartnerTests(TaxScenarioTestMixin, TestCase):
    """Tests for Product.get_tax_rate_for_partner() with TaxService integration."""

    def test_domestic_partner_gets_standard_rate(self):
        partner = BusinessPartner.objects.create(
            company_name="Inland Test GmbH",
            address_line1="Teststr. 5",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        rate = self.product_standard.get_tax_rate_for_partner(partner)
        self.assertEqual(rate, Decimal("19.00"))

    def test_eu_partner_with_vat_id_gets_zero(self):
        partner = BusinessPartner.objects.create(
            company_name="FR Test SARL",
            address_line1="5 Rue de Test",
            postal_code="75005",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        rate = self.product_standard.get_tax_rate_for_partner(partner)
        self.assertEqual(rate, Decimal("0.00"))

    def test_export_partner_gets_zero(self):
        partner = BusinessPartner.objects.create(
            company_name="US Test Corp",
            address_line1="456 Main St",
            postal_code="10002",
            city="New York",
            country=self.usa,
        )
        rate = self.product_standard.get_tax_rate_for_partner(partner)
        self.assertEqual(rate, Decimal("0.00"))

    def test_no_partner_gets_default_rate(self):
        rate = self.product_standard.get_tax_rate_for_partner(None)
        self.assertEqual(rate, Decimal("19.00"))

    def test_reduced_product_domestic_gets_reduced_rate(self):
        partner = BusinessPartner.objects.create(
            company_name="Inland Reduced Test",
            address_line1="Teststr. 6",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        rate = self.product_reduced.get_tax_rate_for_partner(partner)
        self.assertEqual(rate, Decimal("7.00"))

    def test_reduced_product_eu_reverse_charge_gets_zero(self):
        """Even reduced-rate products get 0% for Reverse Charge."""
        partner = BusinessPartner.objects.create(
            company_name="AT Test GmbH",
            address_line1="Kärntner Str. 2",
            postal_code="1010",
            city="Wien",
            country=self.austria,
            vat_id="ATU12345678",
        )
        rate = self.product_reduced.get_tax_rate_for_partner(partner)
        self.assertEqual(rate, Decimal("0.00"))


# ==============================================================================
# Product.get_tax_determination_for_partner Tests
# ==============================================================================
class ProductTaxDeterminationTests(TaxScenarioTestMixin, TestCase):
    """Tests for Product.get_tax_determination_for_partner()."""

    def test_domestic_determination(self):
        partner = BusinessPartner.objects.create(
            company_name="Determ Inland GmbH",
            address_line1="Teststr. 7",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        det = self.product_standard.get_tax_determination_for_partner(partner)
        self.assertIsInstance(det, TaxDetermination)
        self.assertEqual(det.scenario, TaxScenario.DOMESTIC)
        self.assertEqual(det.tax_rate, Decimal("19.00"))
        self.assertEqual(det.tax_category_code, "S")
        self.assertEqual(det.exemption_reason, "")

    def test_eu_reverse_charge_determination(self):
        partner = BusinessPartner.objects.create(
            company_name="Determ FR SARL",
            address_line1="6 Rue de Test",
            postal_code="75006",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        det = self.product_standard.get_tax_determination_for_partner(partner)
        self.assertEqual(det.scenario, TaxScenario.EU_REVERSE_CHARGE)
        self.assertEqual(det.tax_rate, Decimal("0.00"))
        self.assertEqual(det.tax_category_code, "AE")
        self.assertEqual(det.exemption_reason, EXEMPTION_REASONS[TaxScenario.EU_REVERSE_CHARGE])

    def test_export_determination(self):
        partner = BusinessPartner.objects.create(
            company_name="Determ Swiss AG",
            address_line1="Bahnhofstr. 3",
            postal_code="8003",
            city="Zürich",
            country=self.switzerland,
        )
        det = self.product_standard.get_tax_determination_for_partner(partner)
        self.assertEqual(det.scenario, TaxScenario.EXPORT)
        self.assertEqual(det.tax_rate, Decimal("0.00"))
        self.assertEqual(det.tax_category_code, "G")
        self.assertEqual(det.exemption_reason, EXEMPTION_REASONS[TaxScenario.EXPORT])

    def test_no_partner_determination(self):
        det = self.product_standard.get_tax_determination_for_partner(None)
        self.assertEqual(det.scenario, TaxScenario.DOMESTIC)
        self.assertEqual(det.tax_rate, Decimal("19.00"))
        self.assertEqual(det.tax_category_code, "S")

    def test_zero_rate_product_no_partner(self):
        det = self.product_zero.get_tax_determination_for_partner(None)
        self.assertEqual(det.tax_category_code, "Z")
        self.assertEqual(det.tax_rate, Decimal("0.00"))


# ==============================================================================
# InvoiceLine Tax Category Integration Tests
# ==============================================================================
class InvoiceLineTaxCategoryTests(TaxScenarioTestMixin, TestCase):
    """Tests for InvoiceLine tax_category_code and tax_exemption_reason persistence."""

    def _create_invoice(self, partner):
        """Helper to create an invoice with the given partner."""
        return Invoice.objects.create(
            company=self.company,
            business_partner=partner,
            currency="EUR",
        )

    def test_domestic_invoice_line_has_standard_category(self):
        """Domestic invoice line → tax_category_code = S, normal rate."""
        partner = BusinessPartner.objects.create(
            company_name="Line Inland GmbH",
            address_line1="Teststr. 8",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        invoice = self._create_invoice(partner)
        line = InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product_standard,
            quantity=Decimal("2"),
        )
        self.assertEqual(line.tax_rate, Decimal("19.00"))
        self.assertEqual(line.tax_category_code, "S")
        self.assertEqual(line.tax_exemption_reason, "")

    def test_eu_reverse_charge_invoice_line(self):
        """EU Reverse Charge invoice line → 0%, AE, with exemption reason."""
        partner = BusinessPartner.objects.create(
            company_name="Line FR SARL",
            address_line1="7 Rue de Test",
            postal_code="75007",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        invoice = self._create_invoice(partner)
        line = InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product_standard,
            quantity=Decimal("1"),
        )
        self.assertEqual(line.tax_rate, Decimal("0.00"))
        self.assertEqual(line.tax_category_code, "AE")
        self.assertIn("Reverse Charge", line.tax_exemption_reason)
        # Tax amount should be 0
        self.assertEqual(line.tax_amount, Decimal("0.00"))

    def test_export_invoice_line(self):
        """Export invoice line → 0%, G, with export exemption reason."""
        partner = BusinessPartner.objects.create(
            company_name="Line Swiss AG",
            address_line1="Bahnhofstr. 4",
            postal_code="8004",
            city="Zürich",
            country=self.switzerland,
        )
        invoice = self._create_invoice(partner)
        line = InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product_standard,
            quantity=Decimal("3"),
        )
        self.assertEqual(line.tax_rate, Decimal("0.00"))
        self.assertEqual(line.tax_category_code, "G")
        self.assertIn("Ausfuhrlieferung", line.tax_exemption_reason)
        self.assertEqual(line.tax_amount, Decimal("0.00"))

    def test_reverse_charge_invoice_total_no_tax(self):
        """Full invoice for EU Reverse Charge → total = subtotal (no tax)."""
        partner = BusinessPartner.objects.create(
            company_name="Total FR SARL",
            address_line1="8 Rue de Test",
            postal_code="75008",
            city="Paris",
            country=self.france,
            vat_id="FR12345678901",
        )
        invoice = self._create_invoice(partner)
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product_standard,
            quantity=Decimal("2"),
        )
        invoice.refresh_from_db()
        # 2 × 100.00 = 200.00 subtotal, 0 tax
        self.assertEqual(invoice.subtotal, Decimal("200.00"))
        self.assertEqual(invoice.tax_amount, Decimal("0.00"))
        self.assertEqual(invoice.total_amount, Decimal("200.00"))

    def test_domestic_invoice_total_with_tax(self):
        """Domestic invoice → total includes correct tax."""
        partner = BusinessPartner.objects.create(
            company_name="Total Inland GmbH",
            address_line1="Teststr. 9",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
        )
        invoice = self._create_invoice(partner)
        InvoiceLine.objects.create(
            invoice=invoice,
            product=self.product_standard,
            quantity=Decimal("1"),
        )
        invoice.refresh_from_db()
        # 1 × 100.00 = 100.00 subtotal, 19.00 tax, 119.00 total
        self.assertEqual(invoice.subtotal, Decimal("100.00"))
        self.assertEqual(invoice.tax_amount, Decimal("19.00"))
        self.assertEqual(invoice.total_amount, Decimal("119.00"))


# ==============================================================================
# TaxService.get_company_country_code Tests
# ==============================================================================
class CompanyCountryCodeTests(TaxScenarioTestMixin, TestCase):
    """Tests for TaxService.get_company_country_code()."""

    def test_german_company(self):
        code = TaxService.get_company_country_code(self.company)
        self.assertEqual(code, "DE")

    def test_none_company_defaults_to_de(self):
        code = TaxService.get_company_country_code(None)
        self.assertEqual(code, "DE")


# ==============================================================================
# InvoiceLine.tax_category_code Property Tests (edge cases)
# ==============================================================================
class TaxCategoryCodePropertyTests(TestCase):
    """Tests for InvoiceLine.tax_category_code property edge cases."""

    def test_explicitly_set_ae_is_returned(self):
        """tax_category='AE' is returned even when tax_rate is 0."""
        line = InvoiceLine(tax_rate=Decimal("0"), tax_category="AE")
        self.assertEqual(line.tax_category_code, "AE")

    def test_explicitly_set_g_is_returned(self):
        """tax_category='G' is returned."""
        line = InvoiceLine(tax_rate=Decimal("0"), tax_category="G")
        self.assertEqual(line.tax_category_code, "G")

    def test_default_s_with_positive_rate(self):
        """Default S with positive rate."""
        line = InvoiceLine(tax_rate=Decimal("19"), tax_category="S")
        self.assertEqual(line.tax_category_code, "S")

    def test_zero_rate_without_category_returns_z(self):
        """Zero rate with no explicit category → Z."""
        line = InvoiceLine(tax_rate=Decimal("0"), tax_category="")
        self.assertEqual(line.tax_category_code, "Z")

    def test_zero_rate_with_s_category_returns_z(self):
        """Zero rate with default S → Z (backward compat)."""
        line = InvoiceLine(tax_rate=Decimal("0"), tax_category="S")
        # S with 0% makes no sense → property should return Z
        self.assertEqual(line.tax_category_code, "Z")
