"""Tests for invoice models."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from invoice_app.models import BusinessPartner, Invoice, InvoiceLine
from invoice_app.tests.factories import (
    BusinessPartnerFactory,
    CompanyFactory,
    IndividualPartnerFactory,
    InvoiceFactory,
    UserFactory,
)


User = get_user_model()


class CompanyModelTests(TestCase):
    """Test suite for the Company model."""

    def test_company_creation(self):
        """Test creating a Company instance."""
        company = CompanyFactory(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE987654321",
            city="Test City",
            email="info@testcompany.com",
        )

        self.assertEqual(company.name, "Test Company")
        self.assertEqual(company.tax_id, "DE123456789")
        self.assertEqual(company.city, "Test City")
        self.assertEqual(company.email, "info@testcompany.com")

        # Test __str__ method
        self.assertEqual(str(company), "Test Company")


class BusinessPartnerModelTests(TestCase):
    """Test suite for the BusinessPartner model."""

    def test_business_partner_creation_business(self):
        """Test creating a business BusinessPartner instance."""
        partner = BusinessPartnerFactory(
            company_name="Customer Corp",
            city="Customer City",
            email="contact@customer.com",
        )

        self.assertEqual(partner.company_name, "Customer Corp")
        self.assertEqual(partner.partner_type, BusinessPartner.PartnerType.BUSINESS)
        self.assertEqual(str(partner), "Customer Corp")

    def test_business_partner_creation_individual(self):
        """Test creating an individual BusinessPartner instance."""
        partner = IndividualPartnerFactory(
            first_name="John",
            last_name="Doe",
            city="Individual City",
            email="john.doe@email.com",
        )

        self.assertEqual(partner.first_name, "John")
        self.assertEqual(partner.last_name, "Doe")
        self.assertEqual(partner.partner_type, BusinessPartner.PartnerType.INDIVIDUAL)
        self.assertEqual(str(partner), "John Doe")


class InvoiceModelTests(TestCase):
    """Test suite for the Invoice model."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.company = CompanyFactory()
        self.business_partner = BusinessPartnerFactory()

    def test_invoice_creation(self):
        """Test creating an Invoice instance."""
        today = timezone.now().date()
        due_date = today + timezone.timedelta(days=30)

        invoice = Invoice.objects.create(
            invoice_number="INV-2023-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
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

        self.assertEqual(invoice.invoice_number, "INV-2023-001")
        self.assertEqual(invoice.issue_date, today)
        self.assertEqual(invoice.currency, "EUR")
        self.assertEqual(invoice.total_amount, Decimal("297.50"))
        self.assertEqual(invoice.company, self.company)
        self.assertEqual(invoice.business_partner, self.business_partner)

        # Test __str__ method
        self.assertEqual(str(invoice), f"INV-2023-001 - {self.business_partner.display_name} (Draft)")

    def test_invoice_save_calculates_total(self):
        """Test that the save method calculates the total_amount correctly."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2023-002",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            # total_amount will be calculated automatically
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )

        self.assertEqual(invoice.total_amount, Decimal("119.00"))

        # Update subtotal and check if total is recalculated
        invoice.subtotal = Decimal("200.00")
        invoice.save()

        self.assertEqual(invoice.total_amount, Decimal("219.00"))

    def test_invoice_status_methods(self):
        """Test the invoice status helper methods."""
        # Create a paid invoice
        paid_invoice = Invoice.objects.create(
            invoice_number="INV-PAID",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.PAID,
            created_by=self.user,
        )

        self.assertTrue(paid_invoice.is_paid())
        self.assertFalse(paid_invoice.is_overdue())

        # Create an overdue invoice
        overdue_invoice = Invoice.objects.create(
            invoice_number="INV-OVERDUE",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date() - timezone.timedelta(days=60),
            due_date=timezone.now().date() - timezone.timedelta(days=30),  # 30 days ago
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.SENT,
            created_by=self.user,
        )

        self.assertFalse(overdue_invoice.is_paid())
        self.assertTrue(overdue_invoice.is_overdue())

    def test_invoice_number_validation(self):
        """Test validation of the invoice_number field."""
        # Valid invoice number
        invoice = Invoice(
            invoice_number="INV-2023-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,  # Add required field
        )

        invoice.full_clean()  # Should not raise ValidationError

        # Invalid invoice number with special characters
        invoice.invoice_number = "INV/2023/001!"

        with self.assertRaises(ValidationError):
            invoice.full_clean()


class InvoiceLineModelTests(TestCase):
    """Test suite for the InvoiceLine model."""

    def setUp(self):
        """Set up test data."""
        self.invoice = InvoiceFactory()

    def test_invoice_line_creation(self):
        """Test creating an InvoiceLine instance."""
        line = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Test Product",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            product_code="PROD-123",
            unit_of_measure=1,
        )

        self.assertEqual(line.description, "Test Product")
        self.assertEqual(line.quantity, Decimal("2"))
        self.assertEqual(line.unit_price, Decimal("100.00"))
        self.assertEqual(line.tax_rate, Decimal("19.00"))

        # Test line_total calculation
        self.assertEqual(line.line_total, Decimal("200.00"))

        # Test __str__ method
        self.assertEqual(str(line), "Test Product - 200.00 EUR")

    def test_line_total_calculation(self):
        """Test that the line_total is calculated correctly on save."""
        line = InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Test Product",
            quantity=Decimal("2"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            product_code="PROD-123",
            unit_of_measure=1,
        )

        self.assertEqual(line.line_total, Decimal("200.00"))

        # Update quantity and check if line_total is recalculated
        line.quantity = Decimal("3")
        line.save()

        self.assertEqual(line.line_total, Decimal("300.00"))
