"""
Tests for CRUD (Create, Read, Update, Delete) functionality of web views.
This module tests the web interface for Company, Customer, and Invoice management.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine, Product, UserProfile, UserRole


class CRUDTestCase(TestCase):
    """Base test case for CRUD operations with common setup."""

    def setUp(self):
        """Set up test data for CRUD tests."""
        self.client = Client()

        # Create test user with admin role
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")

        # Create admin role and user profile
        if not UserRole.objects.filter(role_type=UserRole.RoleType.ADMIN).exists():
            UserRole.create_system_roles()

        admin_role = UserRole.objects.get(role_type=UserRole.RoleType.ADMIN)
        self.user_profile = UserProfile.objects.create(user=self.user, role=admin_role, employee_id="EMP001")

        # Login user for authenticated requests
        self.client.login(username="testuser", password="testpassword123")

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
            name="Test Company Ltd",
            legal_name="Test Company Limited",
            tax_id="TAX123456",
            vat_id="VAT123456",
            address_line1="123 Test Street",
            city="Test City",
            postal_code="12345",
            country=self.germany,
            email="test@company.com",
            phone="+49123456789",
            default_currency="EUR",
            default_payment_terms=30,
        )

        # Create test business partner
        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            partner_number="CUST001",
            company_name="Test Customer Corp",
            legal_name="Test Customer Corporation",
            tax_id="CUSTTAX123",
            address_line1="456 Customer Ave",
            city="Customer City",
            postal_code="54321",
            country=self.germany,
            email="customer@test.com",
            phone="+49987654321",
        )

        # Create test product
        self.product = Product.objects.create(
            product_code="PROD001",
            name="Test Product",
            description="A test product for testing",
            base_price=Decimal("100.00"),
            currency="EUR",
            default_tax_rate=Decimal("19.00"),
            created_by=self.user,
        )


class CompanyCRUDTests(CRUDTestCase):
    """Test CRUD operations for Company model."""

    def test_company_list_view(self):
        """Test that company list view displays companies correctly."""
        url = reverse("company-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company.name)
        self.assertContains(response, self.company.email)
        self.assertIn("companies", response.context)
        self.assertEqual(list(response.context["companies"]), [self.company])

    def test_company_detail_view(self):
        """Test that company detail view shows correct company information."""
        url = reverse("company-detail", kwargs={"pk": self.company.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company.name)
        self.assertContains(response, self.company.legal_name)
        self.assertContains(response, self.company.tax_id)
        self.assertContains(response, self.company.address_line1)
        self.assertEqual(response.context["company"], self.company)

    def test_company_create_view_get(self):
        """Test GET request to company create view."""
        url = reverse("company-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Company")
        self.assertContains(response, "form")

    def test_company_create_view_post_valid(self):
        """Test POST request to company create view with valid data."""
        url = reverse("company-create")
        data = {
            "name": "New Test Company",
            "legal_name": "New Test Company Ltd",
            "tax_id": "NEWTAX123",
            "vat_id": "DE999888777",
            "address_line1": "789 New Street",
            "city": "New City",
            "postal_code": "98765",
            "country": self.germany.pk,
            "email": "new@company.com",
            "default_currency": "EUR",
            "default_payment_terms": 30,
            "is_active": True,
        }

        # Check initial count
        initial_count = Company.objects.count()

        response = self.client.post(url, data)

        # Should redirect to company list after successful creation
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("company-list"))

        # Check that company was created
        self.assertEqual(Company.objects.count(), initial_count + 1)
        new_company = Company.objects.get(name="New Test Company")
        self.assertEqual(new_company.legal_name, "New Test Company Ltd")
        self.assertEqual(new_company.tax_id, "NEWTAX123")

    def test_company_create_view_post_invalid(self):
        """Test POST request to company create view with invalid data."""
        url = reverse("company-create")
        data = {"name": "", "email": "invalid-email"}  # Required field missing  # Invalid email format

        initial_count = Company.objects.count()
        response = self.client.post(url, data)

        # Should not redirect, should show form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

        # Should not create a new company
        self.assertEqual(Company.objects.count(), initial_count)

    def test_company_update_view_get(self):
        """Test GET request to company update view."""
        url = reverse("company-update", kwargs={"pk": self.company.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update Company")
        self.assertContains(response, self.company.name)

    def test_company_update_view_post_valid(self):
        """Test POST request to company update view with valid data."""
        url = reverse("company-update", kwargs={"pk": self.company.pk})
        data = {
            "name": "Updated Company Name",
            "legal_name": self.company.legal_name,
            "tax_id": self.company.tax_id,
            "vat_id": self.company.vat_id,
            "address_line1": self.company.address_line1,
            "city": self.company.city,
            "postal_code": self.company.postal_code,
            "country": self.company.country.pk,
            "email": "updated@company.com",
            "default_currency": self.company.default_currency,
            "default_payment_terms": self.company.default_payment_terms,
            "is_active": self.company.is_active,
        }

        response = self.client.post(url, data)

        # Should redirect to company list after successful update
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("company-list"))

        # Check that company was updated
        updated_company = Company.objects.get(pk=self.company.pk)
        self.assertEqual(updated_company.name, "Updated Company Name")
        self.assertEqual(updated_company.email, "updated@company.com")

    def test_company_delete_view_get(self):
        """Test GET request to company delete view."""
        url = reverse("company-delete", kwargs={"pk": self.company.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Company")
        self.assertContains(response, self.company.name)

    def test_company_delete_view_post(self):
        """Test POST request to company delete view."""
        url = reverse("company-delete", kwargs={"pk": self.company.pk})
        company_id = self.company.pk

        response = self.client.post(url)

        # Should redirect to company list after successful deletion
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("company-list"))

        # Check that company was deleted
        self.assertFalse(Company.objects.filter(pk=company_id).exists())


class BusinessPartnerCRUDTests(CRUDTestCase):
    """Test CRUD operations for BusinessPartner model."""

    def test_business_partner_list_view(self):
        """Test that business partner list view displays business partners correctly."""
        url = reverse("business-partner-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.business_partner.display_name)
        self.assertContains(response, self.business_partner.email)
        self.assertIn("partners", response.context)
        self.assertEqual(list(response.context["partners"]), [self.business_partner])

    def test_business_partner_detail_view(self):
        """Test that business partner detail view shows correct business partner information."""
        url = reverse("business-partner-detail", kwargs={"pk": self.business_partner.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.business_partner.display_name)
        self.assertContains(response, self.business_partner.company_name)
        self.assertContains(response, self.business_partner.tax_id)
        self.assertEqual(response.context["partner"], self.business_partner)

    def test_business_partner_create_view_business(self):
        """Test creating a business partner."""
        url = reverse("business-partner-create")
        data = {
            "partner_type": BusinessPartner.PartnerType.BUSINESS,
            "partner_number": "CUST002",
            "company_name": "New Business Customer",
            "legal_name": "New Business Customer Ltd",
            "tax_id": "NEWBIZ123",
            "address_line1": "321 Business Ave",
            "city": "Business City",
            "postal_code": "11111",
            "country": self.germany.pk,
            "email": "business@customer.com",
        }

        initial_count = BusinessPartner.objects.count()
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BusinessPartner.objects.count(), initial_count + 1)
        new_partner = BusinessPartner.objects.get(partner_number="CUST002")
        self.assertEqual(new_partner.partner_type, BusinessPartner.PartnerType.BUSINESS)
        self.assertEqual(new_partner.company_name, "New Business Customer")

    def test_business_partner_create_view_individual(self):
        """Test creating an individual business partner."""
        url = reverse("business-partner-create")
        data = {
            "partner_type": BusinessPartner.PartnerType.INDIVIDUAL,
            "partner_number": "CUST003",
            "first_name": "John",
            "last_name": "Doe",
            "address_line1": "456 Individual St",
            "city": "Individual City",
            "postal_code": "22222",
            "country": self.germany.pk,
            "email": "john.doe@email.com",
        }

        initial_count = BusinessPartner.objects.count()
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BusinessPartner.objects.count(), initial_count + 1)
        new_partner = BusinessPartner.objects.get(partner_number="CUST003")
        self.assertEqual(new_partner.partner_type, BusinessPartner.PartnerType.INDIVIDUAL)
        self.assertEqual(new_partner.first_name, "John")
        self.assertEqual(new_partner.last_name, "Doe")


class InvoiceCRUDTests(CRUDTestCase):
    """Test CRUD operations for Invoice model."""

    def setUp(self):
        """Set up additional test data for invoice tests."""
        super().setUp()

        # Create test invoice
        self.invoice = Invoice.objects.create(
            invoice_number="INV-2025-001",
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )

        # Create test invoice line
        self.invoice_line = InvoiceLine.objects.create(
            invoice=self.invoice,
            product=self.product,
            description="Test product line",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("100.00"),
        )

    def test_invoice_list_view(self):
        """Test that invoice list view displays invoices correctly."""
        url = reverse("invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.invoice_number)
        self.assertContains(response, self.business_partner.company_name)  # Business partner name is shown in the list
        self.assertIn("invoices", response.context)

    def test_invoice_detail_view(self):
        """Test that invoice detail view shows correct invoice information."""
        url = reverse("invoice-detail", kwargs={"pk": self.invoice.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.invoice_number)
        self.assertContains(response, self.company.name)
        self.assertContains(response, self.business_partner.display_name)
        self.assertContains(response, str(self.invoice.total_amount))
        self.assertEqual(response.context["invoice"], self.invoice)

    def test_invoice_create_view(self):
        """Test creating a new invoice."""
        url = reverse("invoice-create")
        data = {
            "invoice_number": "INV-2025-002",
            "invoice_type": Invoice.InvoiceType.INVOICE,
            "company": self.company.pk,
            "business_partner": self.business_partner.pk,
            "issue_date": timezone.now().date(),
            "due_date": (timezone.now().date() + timezone.timedelta(days=30)),
            "currency": "EUR",
            "status": Invoice.InvoiceStatus.DRAFT,
            "payment_terms": 30,
        }

        initial_count = Invoice.objects.count()
        response = self.client.post(url, data)

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Invoice.objects.count(), initial_count + 1)
        new_invoice = Invoice.objects.get(invoice_number="INV-2025-002")
        self.assertEqual(new_invoice.company, self.company)
        self.assertEqual(new_invoice.business_partner, self.business_partner)

    def test_invoice_line_create_view(self):
        """Test adding a line item to an invoice."""
        url = reverse("invoice-line-create", kwargs={"invoice_pk": self.invoice.pk})
        data = {
            "product": self.product.pk,
            "description": "New test line item",
            "quantity": Decimal("2.00"),
            "unit_price": Decimal("50.00"),
            "unit_of_measure": 1,
            "tax_rate": Decimal("19.00"),
            "discount_percentage": Decimal("0.00"),
            "discount_amount": Decimal("0.00"),
        }

        initial_count = InvoiceLine.objects.filter(invoice=self.invoice).count()
        response = self.client.post(url, data)

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        new_count = InvoiceLine.objects.filter(invoice=self.invoice).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the new line item
        new_line = InvoiceLine.objects.filter(invoice=self.invoice, description="New test line item").first()
        self.assertIsNotNone(new_line)
        self.assertEqual(new_line.quantity, Decimal("2.00"))
        self.assertEqual(new_line.unit_price, Decimal("50.00"))

    def test_invoice_relationships_maintained(self):
        """Test that relationships between models are maintained properly."""
        # Test company-invoice relationship
        company_invoices = self.company.issued_invoices.all()
        self.assertIn(self.invoice, company_invoices)

        # Test business partner-invoice relationship
        partner_invoices = self.business_partner.received_invoices.all()
        self.assertIn(self.invoice, partner_invoices)

        # Test invoice-line relationship
        invoice_lines = self.invoice.lines.all()
        self.assertIn(self.invoice_line, invoice_lines)

        # Test product-line relationship
        product_lines = self.product.invoice_lines.all()
        self.assertIn(self.invoice_line, product_lines)


class NavigationAndUITests(CRUDTestCase):
    """Test navigation and UI elements."""

    def test_home_page_navigation_links(self):
        """Test that home page contains navigation links to main sections."""
        url = reverse("home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/companies/"')
        self.assertContains(response, 'href="/business-partners/"')

    def test_breadcrumb_navigation(self):
        """Test breadcrumb navigation in detail views."""
        # Test company detail breadcrumb
        url = reverse("company-detail", kwargs={"pk": self.company.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should contain links back to company list
        self.assertContains(response, 'href="/companies/"')

    def test_form_validation_messages(self):
        """Test that form validation displays appropriate error messages."""
        url = reverse("company-create")
        data = {"name": "", "email": "invalid-email-format"}  # Required field

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        # Should show validation errors
        self.assertContains(response, "This field is required")

    def test_success_messages(self):
        """Test that success messages are displayed after operations."""
        url = reverse("company-create")
        data = {
            "name": "Success Test Company",
            "legal_name": "Success Test Company Ltd",
            "tax_id": "TAX-SUCCESS-123",
            "vat_id": "DE999777555",
            "address_line1": "123 Success St",
            "city": "Success City",
            "postal_code": "12345",
            "country": self.germany.pk,
            "email": "success@test.com",
            "default_currency": "EUR",
            "default_payment_terms": 30,
            "is_active": True,
        }

        response = self.client.post(url, data, follow=True)

        # Check for success message in the redirected page
        messages = list(response.context["messages"])
        self.assertTrue(any("successfully" in str(message) for message in messages))


class PermissionTests(CRUDTestCase):
    """Test permission-based access to CRUD operations."""

    def test_unauthenticated_access_redirects(self):
        """Test that unauthenticated users are redirected to login."""
        self.client.logout()

        urls_to_test = [
            reverse("company-list"),
            reverse("company-create"),
            reverse("business-partner-list"),
            reverse("business-partner-create"),
            reverse("invoice-list"),
            reverse("invoice-create"),
        ]

        for url in urls_to_test:
            response = self.client.get(url)
            # Should redirect to login (302) or return forbidden (403)
            self.assertIn(response.status_code, [302, 403])

    def test_role_based_access_permissions(self):
        """Test that different user roles have appropriate access."""
        # Create a read-only user
        readonly_user = User.objects.create_user(username="readonly", password="readonly123")
        readonly_role = UserRole.objects.get(role_type=UserRole.RoleType.READ_ONLY)
        UserProfile.objects.create(user=readonly_user, role=readonly_role, employee_id="EMP002")

        # Test with read-only user
        self.client.logout()
        self.client.login(username="readonly", password="readonly123")

        # Should be able to view lists
        response = self.client.get(reverse("company-list"))
        self.assertEqual(response.status_code, 200)

        # Should be able to view details
        response = self.client.get(reverse("company-detail", kwargs={"pk": self.company.pk}))
        self.assertEqual(response.status_code, 200)
