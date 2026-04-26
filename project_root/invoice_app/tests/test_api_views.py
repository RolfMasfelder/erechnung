"""
Tests for the REST API views.
"""

from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine


class InvoiceViewSetTests(APITestCase):
    """Test suite for the Invoice API endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

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

        # Create test company and business partner
        self.supplier = Company.objects.create(
            name="Test Supplier GmbH",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Supplier Street 123",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
            email="contact@supplier.com",
        )

        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
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

    def test_get_invoices_list(self):
        """Test retrieving the list of invoices."""
        url = reverse("api-invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated: {count, results, next, previous}
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["invoice_number"], "INV-2023-001")

    def test_get_invoice_detail(self):
        """Test retrieving a single invoice."""
        url = reverse("api-invoice-detail", args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_number"], "INV-2023-001")
        self.assertEqual(response.data["business_partner"], self.business_partner.id)
        self.assertEqual(response.data["company"], self.supplier.id)
        self.assertEqual(response.data["currency"], "EUR")
        self.assertEqual(float(response.data["total_amount"]), 297.5)

        # Check that related data is included
        self.assertEqual(response.data["business_partner_details"]["company_name"], "Test Customer AG")
        self.assertEqual(response.data["company_details"]["name"], "Test Supplier GmbH")
        self.assertEqual(len(response.data["lines"]), 2)
        self.assertEqual(response.data["lines"][0]["description"], "Product A")

    def test_create_invoice(self):
        """Test creating a new invoice."""
        url = reverse("api-invoice-list")
        today_str = timezone.now().date().isoformat()
        due_date_str = (timezone.now().date() + timezone.timedelta(days=30)).isoformat()

        data = {
            "invoice_type": Invoice.InvoiceType.INVOICE,
            "company": self.supplier.id,
            "business_partner": self.business_partner.id,
            "issue_date": today_str,
            "due_date": due_date_str,
            "currency": "EUR",
            "subtotal": "150.00",
            "tax_amount": "28.50",
            "total_amount": "178.50",
            "status": Invoice.InvoiceStatus.DRAFT,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Invoice.objects.count(), 2)
        # invoice_number is auto-generated (read_only field)
        new_invoice = Invoice.objects.get(id=response.data["id"])
        self.assertEqual(new_invoice.total_amount, Decimal("178.50"))

    def test_update_invoice(self):
        """Test updating an invoice."""
        url = reverse("api-invoice-detail", args=[self.invoice.id])

        data = {
            "invoice_type": Invoice.InvoiceType.INVOICE,
            "company": self.supplier.id,
            "business_partner": self.business_partner.id,
            "issue_date": self.invoice.issue_date.isoformat(),
            "due_date": self.invoice.due_date.isoformat(),
            "currency": "USD",  # Changed from EUR to USD
            "subtotal": "250.00",
            "tax_amount": "47.50",
            "total_amount": "297.50",
            "status": Invoice.InvoiceStatus.DRAFT,
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invoice.refresh_from_db()
        # invoice_number is read_only and cannot be changed via API
        self.assertEqual(self.invoice.invoice_number, "INV-2023-001")
        self.assertEqual(self.invoice.currency, "USD")

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    def test_generate_pdf(self, mock_invoice_service):
        """Test generating a PDF for an invoice."""
        # Set up mock
        mock_service_instance = mock_invoice_service.return_value
        mock_service_instance.generate_invoice_files.return_value = {
            "pdf_path": "/tmp/invoice.pdf",
            "xml_path": "/tmp/invoice.xml",
            "is_valid": True,
            "validation_errors": [],
        }

        # Call API endpoint
        url = reverse("api-invoice-generate-pdf", args=[self.invoice.id])
        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pdf_url", response.data)
        self.assertEqual(response.data["xml_valid"], True)

        # Verify service was called with default COMFORT profile
        mock_service_instance.generate_invoice_files.assert_called_once_with(self.invoice, "COMFORT")

    def test_mark_as_paid(self):
        """Test marking an invoice as paid."""
        url = reverse("api-invoice-mark-as-paid", args=[self.invoice.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.InvoiceStatus.PAID)

    def test_invoice_list_ordering_supported_fields(self):
        """Test ordering by invoice_number, status and customer relation field."""
        partner_alpha = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Alpha GmbH",
            tax_id="DE111111111",
            address_line1="Alpha Straße 1",
            postal_code="50667",
            city="Köln",
            country=self.germany,
            email="alpha@example.com",
        )

        Invoice.objects.create(
            invoice_number="INV-2023-002",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.supplier,
            business_partner=partner_alpha,
            issue_date=self.invoice.issue_date,
            due_date=self.invoice.due_date,
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.SENT,
            created_by=self.user,
        )

        url = reverse("api-invoice-list")

        response = self.client.get(url, {"ordering": "invoice_number"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["invoice_number"], "INV-2023-001")

        response = self.client.get(url, {"ordering": "status"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["status"], Invoice.InvoiceStatus.DRAFT)

        response = self.client.get(url, {"ordering": "business_partner__company_name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # customer_name ist veraltet – verwende business_partner_details.company_name
        self.assertEqual(response.data["results"][0]["business_partner_details"]["company_name"], "Alpha GmbH")


class CompanyViewSetTests(APITestCase):
    """Test suite for the Company API endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

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

        # Create test company
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 123",
            postal_code="12345",
            city="Test City",
            country=self.germany,
            email="test@example.com",
        )

    def test_get_companies_list(self):
        """Test retrieving the list of companies."""
        url = reverse("api-company-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated: {count, results, next, previous}
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test Company")

    def test_get_company_detail(self):
        """Test retrieving a single company."""
        url = reverse("api-company-detail", args=[self.company.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Company")
        self.assertEqual(response.data["tax_id"], "DE123456789")

    def test_create_company(self):
        """Test creating a new company."""
        url = reverse("api-company-list")

        data = {
            "name": "New Company",
            "tax_id": "DE987654321",
            "vat_id": "DE987654321",
            "address_line1": "New Street 456",
            "postal_code": "54321",
            "city": "New City",
            "country": self.germany.code,
            "email": "new@example.com",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 2)
        new_company = Company.objects.get(name="New Company")
        self.assertEqual(new_company.tax_id, "DE987654321")

    def test_update_company(self):
        """Test updating a company."""
        url = reverse("api-company-detail", args=[self.company.id])

        data = {
            "name": "Updated Company",
            "tax_id": "DE123456789",
            "vat_id": "DE123456789",
            "address_line1": "Test Street 123",
            "postal_code": "12345",
            "city": "Test City",
            "country": self.germany.code,
            "email": "updated@example.com",
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Updated Company")
        self.assertEqual(self.company.email, "updated@example.com")

    def test_delete_company(self):
        """Test deleting a company."""
        # First create a new company to delete
        new_company = Company.objects.create(
            name="To Be Deleted",
            tax_id="DELETE001",
            vat_id="DE000000000",
            address_line1="Delete Street",
            postal_code="00000",
            city="Delete City",
            country=self.germany,
        )

        url = reverse("api-company-detail", args=[new_company.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Company.objects.count(), 1)  # Only the original one remains
        with self.assertRaises(Company.DoesNotExist):
            Company.objects.get(pk=new_company.id)


class BusinessPartnerViewSetTests(APITestCase):
    """Test suite for the BusinessPartner API endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

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

        # Create test business partner
        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Customer",
            tax_id="DE123456789",
            address_line1="Test Street 123",
            postal_code="12345",
            city="Test City",
            country=self.germany,
            email="test@example.com",
        )

    def test_get_business_partners_list(self):
        """Test retrieving the list of business partners."""
        url = reverse("api-business-partner-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated: {count, results, next, previous}
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["company_name"], "Test Customer")

    def test_get_business_partner_detail(self):
        """Test retrieving a single business partner."""
        url = reverse("api-business-partner-detail", args=[self.business_partner.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["company_name"], "Test Customer")
        self.assertEqual(response.data["tax_id"], "DE123456789")

    def test_create_business_partner(self):
        """Test creating a new business partner."""
        url = reverse("api-business-partner-list")

        data = {
            "partner_type": "BUSINESS",
            "company_name": "New Customer",
            "tax_id": "DE987654321",
            "address_line1": "New Street 456",
            "postal_code": "54321",
            "city": "New City",
            "country": self.germany.pk,
            "email": "new@example.com",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BusinessPartner.objects.count(), 2)
        new_partner = BusinessPartner.objects.get(company_name="New Customer")
        self.assertEqual(new_partner.tax_id, "DE987654321")

    def test_business_partner_ordering_by_business_partner_name(self):
        """Test ordering by computed business_partner_name field."""
        BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Alpha Partner",
            address_line1="Alpha Straße 1",
            postal_code="50667",
            city="Köln",
            country=self.germany,
            email="alpha@example.com",
        )

        url = reverse("api-business-partner-list")
        response = self.client.get(url, {"ordering": "business_partner_name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["company_name"], "Alpha Partner")

    def test_update_business_partner(self):
        """Test updating a business partner."""
        url = reverse("api-business-partner-detail", args=[self.business_partner.id])

        data = {
            "partner_type": "BUSINESS",
            "company_name": "Updated Customer",
            "tax_id": "DE123456789",
            "address_line1": "Test Street 123",
            "postal_code": "12345",
            "city": "Test City",
            "country": self.germany.pk,
            "email": "updated@example.com",
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.business_partner.refresh_from_db()
        self.assertEqual(self.business_partner.company_name, "Updated Customer")
        self.assertEqual(self.business_partner.email, "updated@example.com")

    def test_delete_customer(self):
        """Test deleting a business partner."""
        # First create a new business partner to delete
        new_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="To Be Deleted",
            address_line1="Delete Street",
            postal_code="00000",
            city="Delete City",
            country=self.germany,
        )

        url = reverse("api-business-partner-detail", args=[new_partner.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BusinessPartner.objects.count(), 1)  # Only the original one remains
        with self.assertRaises(BusinessPartner.DoesNotExist):
            BusinessPartner.objects.get(pk=new_partner.id)
