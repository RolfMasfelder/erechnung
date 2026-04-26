"""
Tests for Invoice PDF/XML download endpoints.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from invoice_app.models import BusinessPartner, Company, Country, Invoice


User = get_user_model()


class InvoiceDownloadAPITest(TestCase):
    """Test cases for Invoice PDF/XML download endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.force_authenticate(user=self.user)

        # Get or create Germany country
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

        # Create test company
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE987654321",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Test City",
            country=self.germany,
            email="test@testcompany.com",
        )

        # Create test customer (BusinessPartner)
        self.customer = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Customer Inc",
            is_customer=True,
            tax_id="DE987654321",
            vat_id="DE123987654",
            address_line1="Customer Street 1",
            postal_code="54321",
            city="Customer City",
            country=self.germany,
            email="customer@example.com",
        )

        # Create test invoice
        self.invoice = Invoice.objects.create(
            company=self.company,
            business_partner=self.customer,
            invoice_number="INV-2026-001",
            issue_date="2026-02-10",
            due_date="2026-03-10",
            currency="EUR",
            total_amount=Decimal("100.00"),
            status="sent",
            created_by=self.user,
        )

    def test_download_pdf_with_existing_file(self):
        """Test PDF download when file exists."""
        # Generate PDF first
        pdf_url = reverse("api-invoice-generate-pdf", kwargs={"pk": self.invoice.id})
        self.client.post(pdf_url)

        # Refresh invoice from DB
        self.invoice.refresh_from_db()

        # Now download
        download_url = reverse("api-invoice-download-pdf", kwargs={"pk": self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("invoice_INV-2026-001.pdf", response["Content-Disposition"])

    def test_download_pdf_auto_generate_when_missing(self):
        """Test PDF download auto-generates when file doesn't exist."""
        download_url = reverse("api-invoice-download-pdf", kwargs={"pk": self.invoice.id})
        response = self.client.get(download_url)

        # Should auto-generate and return PDF
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Verify file was created in model
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.pdf_file)

    def test_download_xml_with_existing_file(self):
        """Test XML download when file exists."""
        # Generate XML first (via PDF generation)
        pdf_url = reverse("api-invoice-generate-pdf", kwargs={"pk": self.invoice.id})
        self.client.post(pdf_url)

        # Refresh invoice from DB
        self.invoice.refresh_from_db()

        # Now download
        download_url = reverse("api-invoice-download-xml", kwargs={"pk": self.invoice.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("invoice_INV-2026-001.xml", response["Content-Disposition"])

    def test_download_xml_auto_generate_when_missing(self):
        """Test XML download auto-generates when file doesn't exist."""
        download_url = reverse("api-invoice-download-xml", kwargs={"pk": self.invoice.id})
        response = self.client.get(download_url)

        # Should auto-generate and return XML
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/xml")

        # Verify file was created in model
        self.invoice.refresh_from_db()
        self.assertTrue(self.invoice.xml_file)

    def test_download_pdf_unauthenticated(self):
        """Test PDF download requires authentication."""
        # Create new unauthenticated client instead of logout
        unauth_client = APIClient()
        download_url = reverse("api-invoice-download-pdf", kwargs={"pk": self.invoice.id})
        response = unauth_client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_xml_unauthenticated(self):
        """Test XML download requires authentication."""
        # Create new unauthenticated client instead of logout
        unauth_client = APIClient()
        download_url = reverse("api-invoice-download-xml", kwargs={"pk": self.invoice.id})
        response = unauth_client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_pdf_nonexistent_invoice(self):
        """Test PDF download with non-existent invoice returns 404."""
        download_url = reverse("api-invoice-download-pdf", kwargs={"pk": 99999})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_xml_nonexistent_invoice(self):
        """Test XML download with non-existent invoice returns 404."""
        download_url = reverse("api-invoice-download-xml", kwargs={"pk": 99999})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
