"""Tests for the dashboard statistics endpoint."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from invoice_app.models import BusinessPartner, Company, Invoice, Product
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


class DashboardStatsViewTest(TestCase):
    """Test cases for dashboard statistics API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
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
        """Test that endpoint requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_empty_stats(self):
        """Test stats with no data."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoices"]["total"], 0)
        self.assertEqual(response.data["customers"]["total"], 0)
        self.assertEqual(response.data["products"]["total"], 0)
        self.assertEqual(response.data["companies"]["total"], 1)

    def test_invoice_statistics(self):
        """Test invoice statistics with various statuses."""
        self.client.force_authenticate(user=self.user)

        # Create business partners
        partner1 = BusinessPartner.objects.create(
            company_name="Customer 1",
            email="customer1@example.com",
            address_line1="Street 1",
            postal_code="12345",
            city="City",
            country="Germany",
        )
        partner2 = BusinessPartner.objects.create(
            company_name="Customer 2",
            email="customer2@example.com",
            address_line1="Street 2",
            postal_code="12345",
            city="City",
            country="Germany",
        )

        # Create invoices with different statuses
        Invoice.objects.create(
            invoice_number="INV-001",
            business_partner=partner1,
            company=self.company,
            status="draft",
            subtotal=Decimal("84.03"),
            tax_amount=Decimal("15.97"),
        )
        Invoice.objects.create(
            invoice_number="INV-002",
            business_partner=partner1,
            company=self.company,
            status="sent",
            subtotal=Decimal("168.07"),
            tax_amount=Decimal("31.93"),
        )
        Invoice.objects.create(
            invoice_number="INV-003",
            business_partner=partner2,
            company=self.company,
            status="paid",
            subtotal=Decimal("252.10"),
            tax_amount=Decimal("47.90"),
        )
        Invoice.objects.create(
            invoice_number="INV-004",
            business_partner=partner2,
            company=self.company,
            status="cancelled",
            subtotal=Decimal("42.02"),
            tax_amount=Decimal("7.98"),
        )

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
        """Test calculation of total, paid, and outstanding amounts."""
        self.client.force_authenticate(user=self.user)

        partner = BusinessPartner.objects.create(
            company_name="Customer",
            email="customer@example.com",
            address_line1="Street 1",
            postal_code="12345",
            city="City",
            country="Germany",
        )

        Invoice.objects.create(
            invoice_number="INV-001",
            business_partner=partner,
            company=self.company,
            status="paid",
            subtotal=Decimal("420.17"),
            tax_amount=Decimal("79.83"),
        )
        Invoice.objects.create(
            invoice_number="INV-002",
            business_partner=partner,
            company=self.company,
            status="sent",
            subtotal=Decimal("252.10"),
            tax_amount=Decimal("47.90"),
        )
        Invoice.objects.create(
            invoice_number="INV-003",
            business_partner=partner,
            company=self.company,
            status="overdue",
            subtotal=Decimal("168.07"),
            tax_amount=Decimal("31.93"),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice_stats = response.data["invoices"]

        self.assertEqual(float(invoice_stats["total_amount"]), 1000.00)
        self.assertEqual(float(invoice_stats["paid_amount"]), 500.00)
        self.assertEqual(float(invoice_stats["outstanding_amount"]), 500.00)

    def test_customer_and_product_count(self):
        """Test counting of customers and products."""
        self.client.force_authenticate(user=self.user)

        # Create business partners
        BusinessPartner.objects.create(
            company_name="Customer 1",
            email="customer1@example.com",
            address_line1="Street 1",
            postal_code="12345",
            city="City",
            country="Germany",
        )
        BusinessPartner.objects.create(
            company_name="Customer 2",
            email="customer2@example.com",
            address_line1="Street 2",
            postal_code="12345",
            city="City",
            country="Germany",
        )

        # Create products
        Product.objects.create(product_code="PROD-001", name="Product 1", base_price=Decimal("10.00"))
        Product.objects.create(product_code="PROD-002", name="Product 2", base_price=Decimal("20.00"))
        Product.objects.create(product_code="PROD-003", name="Product 3", base_price=Decimal("30.00"))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["customers"]["total"], 2)
        self.assertEqual(response.data["products"]["total"], 3)
        self.assertEqual(response.data["products"]["total"], 3)
