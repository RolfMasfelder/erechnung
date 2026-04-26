"""
Tests for the invoice API.
"""

from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.models import Invoice
from invoice_app.tests.factories import BusinessPartnerFactory, InvoiceFactory, ProductFactory, UserFactory


class InvoiceAPITest(APITestCase):
    """Test the invoice API."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

        self.business_partner = BusinessPartnerFactory()
        self.product = ProductFactory()
        self.invoice = InvoiceFactory(
            invoice_number="INV-001",
            business_partner=self.business_partner,
            created_by=self.user,
        )

    def test_get_invoice_list(self):
        """Test retrieving the list of invoices."""
        url = reverse("api-invoice-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated: {count, results, next, previous}
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_get_invoice_detail(self):
        """Test retrieving a single invoice."""
        url = reverse("api-invoice-detail", args=[self.invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_number"], "INV-001")

    def test_create_invoice(self):
        """Test creating a new invoice."""
        url = reverse("api-invoice-list")
        data = {
            "invoice_number": "INV-002",
            "invoice_type": "INVOICE",
            "business_partner": self.business_partner.id,
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "currency": "EUR",
            "status": "DRAFT",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Invoice.objects.count(), 2)
