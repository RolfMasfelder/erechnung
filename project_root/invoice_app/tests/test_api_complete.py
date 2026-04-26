"""
Comprehensive API tests for all entities defined in the API.
This extends test_api_views.py to cover Product, InvoiceLine, InvoiceAttachment, and AuditLog APIs.
"""

import shutil
import tempfile
import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.models import (
    AuditLog,
    BusinessPartner,
    Company,
    Country,
    CountryTaxRate,
    Invoice,
    InvoiceAttachment,
    InvoiceLine,
    Product,
)


class ProductViewSetTests(APITestCase):
    """Test suite for the Product API endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

        # Create test product
        self.product = Product.objects.create(
            product_code="TEST-001",
            name="Test Product",
            description="A test product",
            product_type=Product.ProductType.SERVICE,
            category="Software",
            base_price=Decimal("100.00"),
            cost_price=Decimal("60.00"),
            tax_category=Product.TaxCategory.STANDARD,
            track_inventory=True,
            stock_quantity=Decimal("50"),
            minimum_stock=Decimal("10"),
            created_by=self.user,
        )

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
                "standard_vat_rate": Decimal("19.00"),
            },
        )[0]

        self.company = Company.objects.create(
            name="Issuer GmbH",
            tax_id="DE111222333",
            vat_id="DE111222333",
            address_line1="Musterstraße 1",
            postal_code="10115",
            city="Berlin",
            country="DE",
            email="info@issuer.example",
            is_active=True,
        )

        CountryTaxRate.objects.get_or_create(
            country=self.germany,
            rate_type=CountryTaxRate.RateType.EXEMPT,
            valid_from=date(2020, 1, 1),
            defaults={"rate": Decimal("0.00")},
        )
        CountryTaxRate.objects.get_or_create(
            country=self.germany,
            rate_type=CountryTaxRate.RateType.REDUCED,
            valid_from=date(2020, 1, 1),
            defaults={"rate": Decimal("7.00")},
        )
        CountryTaxRate.objects.get_or_create(
            country=self.germany,
            rate_type=CountryTaxRate.RateType.STANDARD,
            valid_from=date(2020, 1, 1),
            defaults={"rate": Decimal("19.00")},
        )

    def test_get_products_list(self):
        """Test retrieving the list of products."""
        url = reverse("api-product-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated: {count, results, next, previous}
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["product_code"], "TEST-001")

    def test_get_product_detail(self):
        """Test retrieving a single product."""
        url = reverse("api-product-detail", args=[self.product.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["product_code"], "TEST-001")
        self.assertEqual(response.data["name"], "Test Product")
        self.assertEqual(float(response.data["base_price"]), 100.0)

    def test_create_product(self):
        """Test creating a new product."""
        url = reverse("api-product-list")
        data = {
            "product_code": "TEST-002",
            "name": "New Product",
            "description": "A new test product",
            "product_type": "PHYSICAL",
            "category": "Hardware",
            "base_price": "150.00",
            "cost_price": "90.00",
            "tax_category": "STANDARD",
            "track_inventory": True,
            "stock_quantity": "25",
            "minimum_stock": "5",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        new_product = Product.objects.get(product_code="TEST-002")
        self.assertEqual(new_product.name, "New Product")

    def test_update_product(self):
        """Test updating a product."""
        url = reverse("api-product-detail", args=[self.product.id])
        data = {
            "product_code": "TEST-001",
            "name": "Updated Product",
            "description": "An updated test product",
            "product_type": "SERVICE",
            "category": "Software",
            "base_price": "120.00",
            "cost_price": "70.00",
            "tax_category": "STANDARD",
            "track_inventory": True,
            "stock_quantity": "60",
            "minimum_stock": "15",
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Product")
        self.assertEqual(self.product.base_price, Decimal("120.00"))

    def test_delete_product(self):
        """Test deleting a product."""
        # Create a new product to delete
        new_product = Product.objects.create(
            product_code="DELETE-001",
            name="To Be Deleted",
            product_type=Product.ProductType.PHYSICAL,
            base_price=Decimal("50.00"),
            created_by=self.user,
        )

        url = reverse("api-product-detail", args=[new_product.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=new_product.id).exists())

    def test_update_stock_action(self):
        """Test the custom update_stock action."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        data = {"quantity": "20", "operation": "add"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("70.00"))

    def test_low_stock_action(self):
        """Test the custom low_stock action."""
        # Create a product with low stock
        Product.objects.create(
            product_code="LOW-001",
            name="Low Stock Product",
            product_type=Product.ProductType.PHYSICAL,
            base_price=Decimal("25.00"),
            track_inventory=True,
            stock_quantity=Decimal("5"),
            minimum_stock=Decimal("10"),
            created_by=self.user,
        )

        url = reverse("api-product-low-stock")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product_code"], "LOW-001")

    def test_product_tax_options_action(self):
        url = reverse("api-product-tax-options")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["country_code"], "DE")
        self.assertEqual([item["value"] for item in response.data["tax_rates"]], ["0.00", "7.00", "19.00"])

    def test_create_product_rejects_non_legal_vat_rate_for_country(self):
        url = reverse("api-product-list")
        data = {
            "product_code": "TEST-003",
            "name": "Invalid VAT Product",
            "product_type": "PHYSICAL",
            "base_price": "10.00",
            "default_tax_rate": "5.00",
            "unit_of_measure": 1,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("default_tax_rate", response.data["error"]["details"])


class InvoiceLineViewSetTests(APITestCase):
    """Test suite for the InvoiceLine API endpoints."""

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

        # Create test company and customer
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Company Street 123",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
            email="contact@company.com",
        )

        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Customer",
            tax_id="DE987654321",
            address_line1="Customer Avenue 456",
            postal_code="80333",
            city="Munich",
            country=self.germany,
            email="info@customer.com",
        )

        # Create test product
        self.product = Product.objects.create(
            product_code="PROD-001",
            name="Test Product",
            product_type=Product.ProductType.PHYSICAL,
            base_price=Decimal("100.00"),
            tax_category=Product.TaxCategory.STANDARD,
            created_by=self.user,
        )

        # Create test invoice
        self.invoice = Invoice.objects.create(
            invoice_number="INV-TEST-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

        # Create test invoice line
        self.invoice_line = InvoiceLine.objects.create(
            invoice=self.invoice,
            product=self.product,
            description="Test Product Line",
            product_code="PROD-001",
            quantity=Decimal("2"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("19.00"),
            unit_of_measure=1,
        )

    def test_get_invoice_lines_list(self):
        """Test retrieving the list of invoice lines."""
        url = reverse("api-invoice-line-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]["description"], "Test Product Line")
        else:
            self.assertEqual(len(response.data["results"]), 1)
            self.assertEqual(response.data["results"][0]["description"], "Test Product Line")

    def test_get_invoice_line_detail(self):
        """Test retrieving a single invoice line."""
        url = reverse("api-invoice-line-detail", args=[self.invoice_line.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "Test Product Line")
        self.assertEqual(response.data["product_code"], "PROD-001")
        self.assertEqual(float(response.data["quantity"]), 2.0)

    def test_create_invoice_line(self):
        """Test creating a new invoice line."""
        url = reverse("api-invoice-line-list")
        data = {
            "invoice": self.invoice.id,
            "product": self.product.id,
            "description": "New Product Line",
            "product_code": "PROD-002",
            "quantity": "1",
            "unit_price": "75.00",
            "tax_rate": "19.00",
            "unit_of_measure": 1,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InvoiceLine.objects.count(), 2)

    def test_update_invoice_line(self):
        """Test updating an invoice line."""
        url = reverse("api-invoice-line-detail", args=[self.invoice_line.id])
        data = {
            "invoice": self.invoice.id,
            "product": self.product.id,
            "description": "Updated Product Line",
            "product_code": "PROD-001",
            "quantity": "3",
            "unit_price": "60.00",
            "tax_rate": "19.00",
            "unit_of_measure": 1,
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invoice_line.refresh_from_db()
        self.assertEqual(self.invoice_line.description, "Updated Product Line")
        self.assertEqual(self.invoice_line.quantity, Decimal("3"))

    def test_delete_invoice_line(self):
        """Test deleting an invoice line."""
        url = reverse("api-invoice-line-detail", args=[self.invoice_line.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InvoiceLine.objects.filter(id=self.invoice_line.id).exists())


class InvoiceAttachmentViewSetTests(APITestCase):
    """Test suite for the InvoiceAttachment API endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        self._temp_media = tempfile.mkdtemp()
        self._media_override = override_settings(MEDIA_ROOT=self._temp_media)
        self._media_override.enable()
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

        # Create test company and customer
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Company Street 123",
            postal_code="10115",
            city="Berlin",
            country=self.germany,
            email="contact@company.com",
        )

        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Customer",
            tax_id="DE987654321",
            address_line1="Customer Avenue 456",
            postal_code="80333",
            city="Munich",
            country=self.germany,
            email="info@customer.com",
        )

        # Create test invoice
        self.invoice = Invoice.objects.create(
            invoice_number="INV-ATTACH-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.business_partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=self.user,
        )

        # Create test file for uploads
        self.test_file = SimpleUploadedFile("test_document.pdf", b"fake pdf content", content_type="application/pdf")

        # Create test attachment
        self.attachment = InvoiceAttachment.objects.create(
            invoice=self.invoice,
            file=self.test_file,
            description="Test attachment",
        )

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._temp_media, ignore_errors=True)
        super().tearDown()

    def test_get_attachments_list(self):
        """Test retrieving the list of invoice attachments."""
        url = reverse("api-invoice-attachment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]["description"], "Test attachment")
        else:
            self.assertEqual(len(response.data["results"]), 1)
            self.assertEqual(response.data["results"][0]["description"], "Test attachment")

    def test_get_attachment_detail(self):
        """Test retrieving a single invoice attachment."""
        url = reverse("api-invoice-attachment-detail", args=[self.attachment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "Test attachment")

    def test_create_attachment(self):
        """Test creating a new invoice attachment."""
        url = reverse("api-invoice-attachment-list")

        new_file = SimpleUploadedFile("new_document.pdf", b"new fake pdf content", content_type="application/pdf")

        data = {
            "invoice": self.invoice.id,
            "file": new_file,
            "description": "New test attachment",
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InvoiceAttachment.objects.count(), 2)

    def test_update_attachment(self):
        """Test updating an invoice attachment."""
        url = reverse("api-invoice-attachment-detail", args=[self.attachment.id])
        data = {
            "description": "Updated attachment description",
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.attachment.refresh_from_db()
        self.assertEqual(self.attachment.description, "Updated attachment description")

    def test_delete_attachment(self):
        """Test deleting an invoice attachment."""
        url = reverse("api-invoice-attachment-detail", args=[self.attachment.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InvoiceAttachment.objects.filter(id=self.attachment.id).exists())


class AuditLogViewSetTests(APITestCase):
    """Test suite for the AuditLog API endpoints (read-only)."""

    def setUp(self):
        """Set up test data and authenticate."""
        # Create test user with audit log permissions
        self.user = User.objects.create_user(username="testuser", password="12345")

        # Grant permission to view audit logs
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        audit_log_ct = ContentType.objects.get_for_model(AuditLog)
        view_permission = Permission.objects.get(codename="view_auditlog", content_type=audit_log_ct)
        self.user.user_permissions.add(view_permission)

        self.client.force_authenticate(user=self.user)

        # Create test audit log entry
        self.audit_log_uuid = uuid.uuid4()
        self.audit_log = AuditLog.objects.create(
            event_id=self.audit_log_uuid,
            action=AuditLog.ActionType.CREATE,
            severity=AuditLog.Severity.MEDIUM,
            username="testuser",
            object_type="Invoice",
            object_id="123",
            object_repr="Test Invoice",
            description="Created test invoice",
            ip_address="127.0.0.1",
            is_compliance_relevant=True,
        )

    def test_get_audit_logs_list(self):
        """Test retrieving the list of audit logs."""
        url = reverse("api-audit-log-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            # Check that our audit log is in the response
            self.assertGreaterEqual(len(response.data), 1)
            audit_log_uuids = [log["event_id"] for log in response.data]
            self.assertIn(str(self.audit_log_uuid), audit_log_uuids)
        else:
            self.assertGreaterEqual(len(response.data["results"]), 1)
            audit_log_uuids = [log["event_id"] for log in response.data["results"]]
            self.assertIn(str(self.audit_log_uuid), audit_log_uuids)

    def test_get_audit_log_detail(self):
        """Test retrieving a single audit log."""
        url = reverse("api-audit-log-detail", args=[self.audit_log.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["event_id"], str(self.audit_log_uuid))
        self.assertEqual(response.data["action"], "CREATE")
        self.assertEqual(response.data["username"], "testuser")

    def test_audit_log_read_only(self):
        """Test that audit logs are read-only (no create/update/delete)."""
        url = reverse("api-audit-log-list")
        data = {
            "action": "UPDATE",
            "username": "testuser",
            "description": "Should not be created",
        }

        # Try to create - should fail
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Try to update - should fail
        url = reverse("api-audit-log-detail", args=[self.audit_log.id])
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Try to delete - should fail
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_security_events_action(self):
        """Test the custom security_events action."""
        # Create a security event
        security_uuid = uuid.uuid4()
        AuditLog.objects.create(
            event_id=security_uuid,
            action=AuditLog.ActionType.LOGIN,
            severity=AuditLog.Severity.HIGH,
            username="testuser",
            description="Security test event",
            ip_address="192.168.1.1",
            is_security_event=True,
        )

        url = reverse("api-audit-log-security-events")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["event_id"], str(security_uuid))

    def test_compliance_events_action(self):
        """Test the custom compliance_events action."""
        url = reverse("api-audit-log-compliance-events")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include our test audit log which is compliance_relevant=True
        # plus potentially other compliance events from setup
        self.assertGreaterEqual(len(response.data), 1)

        # Check that our audit log is in the response
        audit_log_uuids = [log["event_id"] for log in response.data]
        self.assertIn(str(self.audit_log_uuid), audit_log_uuids)
        self.assertTrue(response.data[0]["is_compliance_relevant"])
