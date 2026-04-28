"""Tests for the dashboard statistics endpoint."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from invoice_app.models import BusinessPartner, Company, Country, Invoice, Product
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


def _germany() -> Country:
    return Country.objects.get_or_create(
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


def _make_partner(name: str, email: str, country: Country) -> BusinessPartner:
    return BusinessPartner.objects.create(
        company_name=name,
        email=email,
        address_line1="Street 1",
        postal_code="12345",
        city="City",
        country=country,
    )


def _make_invoice(number: str, partner, company, status_value: str, net: Decimal, tax: Decimal) -> Invoice:
    return Invoice.objects.create(
        invoice_number=number,
        business_partner=partner,
        company=company,
        status=status_value,
        subtotal=net,
        tax_amount=tax,
        total_amount=net + tax,
    )


class DashboardStatsViewTest(TestCase):
    """Test cases for dashboard statistics API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.country = _germany()
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="123456789",
            vat_id="DE123456789",
            email="company@example.com",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Test City",
            country="Germany",
        )
        self.url = reverse("api-stats")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_stats(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoices"]["total"], 0)
        self.assertEqual(response.data["business_partners"]["total"], 0)
        self.assertEqual(response.data["products"]["total"], 0)
        self.assertEqual(response.data["companies"]["total"], 1)

    def test_invoice_statistics(self):
        self.client.force_authenticate(user=self.user)

        partner1 = _make_partner("Customer 1", "c1@example.com", self.country)
        partner2 = _make_partner("Customer 2", "c2@example.com", self.country)

        _make_invoice("INV-001", partner1, self.company, "DRAFT", Decimal("84.03"), Decimal("15.97"))
        _make_invoice("INV-002", partner1, self.company, "SENT", Decimal("168.07"), Decimal("31.93"))
        _make_invoice("INV-003", partner2, self.company, "PAID", Decimal("252.10"), Decimal("47.90"))
        _make_invoice("INV-004", partner2, self.company, "CANCELLED", Decimal("42.02"), Decimal("7.98"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice_stats = response.data["invoices"]

        self.assertEqual(invoice_stats["total"], 4)
        self.assertEqual(invoice_stats["by_status"]["draft"], 1)
        self.assertEqual(invoice_stats["by_status"]["sent"], 1)
        self.assertEqual(invoice_stats["by_status"]["paid"], 1)
        self.assertEqual(invoice_stats["by_status"]["cancelled"], 1)
        self.assertEqual(invoice_stats["by_status"]["overdue"], 0)

    def test_invoice_amounts(self):
        self.client.force_authenticate(user=self.user)

        partner = _make_partner("Customer", "customer@example.com", self.country)

        _make_invoice("INV-001", partner, self.company, "PAID", Decimal("420.17"), Decimal("79.83"))
        _make_invoice("INV-002", partner, self.company, "SENT", Decimal("252.10"), Decimal("47.90"))
        _make_invoice("INV-003", partner, self.company, "OVERDUE", Decimal("168.07"), Decimal("31.93"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice_stats = response.data["invoices"]

        self.assertEqual(float(invoice_stats["total_amount"]), 1000.00)
        self.assertEqual(float(invoice_stats["paid_amount"]), 500.00)
        self.assertEqual(float(invoice_stats["outstanding_amount"]), 500.00)

    def test_business_partner_and_product_count(self):
        self.client.force_authenticate(user=self.user)

        _make_partner("Customer 1", "c1@example.com", self.country)
        _make_partner("Customer 2", "c2@example.com", self.country)

        Product.objects.create(product_code="PROD-001", name="Product 1", base_price=Decimal("10.00"))
        Product.objects.create(product_code="PROD-002", name="Product 2", base_price=Decimal("20.00"))
        Product.objects.create(product_code="PROD-003", name="Product 3", base_price=Decimal("30.00"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["business_partners"]["total"], 2)
        self.assertEqual(response.data["products"]["total"], 3)
