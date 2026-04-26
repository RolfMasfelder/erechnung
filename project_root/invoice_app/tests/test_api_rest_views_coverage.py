"""
Tests for improving coverage of api/rest_views.py.

Focused on testing error paths, edge cases, and previously untested code paths.
"""

import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, OperationalError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.models import AuditLog, BusinessPartner, Company, Country, Invoice, InvoiceLine, Product


class InvoiceGeneratePDFTests(APITestCase):
    """Test suite for Invoice ViewSet PDF generation."""

    def setUp(self):
        """Set up test data and authenticate."""
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
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Berlin",
            country=self.germany,
            email="test@company.com",
        )

        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Partner",
            tax_id="DE987654321",
            address_line1="Partner Street 1",
            postal_code="54321",
            city="Munich",
            country=self.germany,
            email="info@partner.com",
        )

        # Create test invoice
        today = timezone.now().date()
        self.invoice = Invoice.objects.create(
            invoice_number="INV-TEST-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.partner,
            issue_date=today,
            due_date=today + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )

        InvoiceLine.objects.create(
            invoice=self.invoice,
            description="Test Product",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            line_total=Decimal("100.00"),
            product_code="TEST-001",
            unit_of_measure=1,
        )

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    def test_generate_pdf_with_invalid_profile(self, mock_service):
        """Test generate_pdf with invalid ZUGFeRD profile falls back to COMFORT."""
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.return_value = {
            "pdf_path": "/tmp/test.pdf",
            "xml_path": "/tmp/test.xml",
            "is_valid": True,
            "validation_errors": [],
        }

        url = reverse("api-invoice-generate-pdf", args=[self.invoice.id])
        # Use invalid profile
        response = self.client.post(url + "?profile=INVALID_PROFILE")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify it fell back to COMFORT profile
        mock_service_instance.generate_invoice_files.assert_called_once_with(self.invoice, "COMFORT")

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    def test_generate_pdf_exception(self, mock_service):
        """Test generate_pdf with generation exception."""
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.side_effect = OSError("Generation failed")

        url = reverse("api-invoice-generate-pdf", args=[self.invoice.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "PDF_GENERATION_FAILED")


class InvoiceDownloadErrorHandlingTests(APITestCase):
    """Test error handling in PDF/XML download endpoints."""

    def setUp(self):
        """Set up test data and authenticate."""
        self._temp_media = tempfile.mkdtemp()
        self._media_override = override_settings(MEDIA_ROOT=self._temp_media)
        self._media_override.enable()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

        self.germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "name": "Germany",
                "currency_code": "EUR",
                "is_eu_member": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            address_line1="Test Street 1",
            postal_code="12345",
            city="Berlin",
            country=self.germany,
        )

        self.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Partner",
            tax_id="DE987654321",
            address_line1="Partner Street 1",
            postal_code="54321",
            city="Munich",
            country=self.germany,
        )

        today = timezone.now().date()
        self.invoice = Invoice.objects.create(
            invoice_number="INV-DOWNLOAD-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=self.company,
            business_partner=self.partner,
            issue_date=today,
            due_date=today + timezone.timedelta(days=30),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            status=Invoice.InvoiceStatus.DRAFT,
            created_by=self.user,
        )

    def tearDown(self):
        self._media_override.disable()
        shutil.rmtree(self._temp_media, ignore_errors=True)
        super().tearDown()

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    def test_download_pdf_generation_failure(self, mock_service):
        """Test download_pdf when auto-generation fails."""
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.side_effect = OSError("Generation failed")

        url = reverse("api-invoice-download-pdf", args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "PDF_GENERATION_FAILED")

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    @mock.patch("builtins.open")
    def test_download_pdf_file_read_error(self, mock_open, mock_service):
        """Test download_pdf when file cannot be read."""
        # Mock successful generation
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.return_value = {
            "pdf_path": "/tmp/test.pdf",
            "xml_path": "/tmp/test.xml",
            "is_valid": True,
            "validation_errors": [],
        }

        # Create a fake PDF file field
        pdf_content = b"%PDF-1.4 fake pdf content"
        self.invoice.pdf_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        self.invoice.save()

        # Mock file open to raise an error
        mock_open.side_effect = OSError("Cannot read file")

        url = reverse("api-invoice-download-pdf", args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "FILE_SERVING_FAILED")

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    def test_download_xml_generation_failure(self, mock_service):
        """Test download_xml when auto-generation fails."""
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.side_effect = ValueError("XML generation failed")

        url = reverse("api-invoice-download-xml", args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "XML_GENERATION_FAILED")

    @mock.patch("invoice_app.services.invoice_service.InvoiceService")
    @mock.patch("builtins.open")
    def test_download_xml_file_read_error(self, mock_open, mock_service):
        """Test download_xml when file cannot be read."""
        # Mock successful generation
        mock_service_instance = mock_service.return_value
        mock_service_instance.generate_invoice_files.return_value = {
            "pdf_path": "/tmp/test.pdf",
            "xml_path": "/tmp/test.xml",
            "is_valid": True,
            "validation_errors": [],
        }

        # Create a fake XML file field
        xml_content = b"<?xml version='1.0'?><root></root>"
        self.invoice.xml_file = SimpleUploadedFile("test.xml", xml_content, content_type="application/xml")
        self.invoice.save()

        # Mock file open to raise an error
        mock_open.side_effect = OSError("Cannot read file")

        url = reverse("api-invoice-download-xml", args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"]["code"], "FILE_SERVING_FAILED")


class ProductViewSetEdgeCasesTests(APITestCase):
    """Test edge cases for Product ViewSet update_stock action."""

    def setUp(self):
        """Set up test data and authenticate."""
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

        self.product = Product.objects.create(
            product_code="PROD-001",
            name="Test Product",
            base_price=Decimal("50.00"),
            track_inventory=True,
            stock_quantity=Decimal("100"),
            minimum_stock=Decimal("10"),
        )

        self.product_no_tracking = Product.objects.create(
            product_code="PROD-002",
            name="No Tracking Product",
            base_price=Decimal("30.00"),
            track_inventory=False,
        )

    def test_update_stock_inventory_tracking_disabled(self):
        """Test update_stock for product with inventory tracking disabled."""
        url = reverse("api-product-update-stock", args=[self.product_no_tracking.id])
        response = self.client.post(url, {"quantity": 50, "operation": "add"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVENTORY_TRACKING_DISABLED")

    def test_update_stock_missing_quantity(self):
        """Test update_stock without quantity parameter."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        response = self.client.post(url, {"operation": "add"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_QUANTITY")

    def test_update_stock_invalid_quantity(self):
        """Test update_stock with invalid quantity value."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        response = self.client.post(url, {"quantity": "invalid", "operation": "add"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_QUANTITY")

    def test_update_stock_invalid_operation(self):
        """Test update_stock with invalid operation."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        response = self.client.post(url, {"quantity": 10, "operation": "invalid_op"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_OPERATION")

    def test_update_stock_subtract_below_zero(self):
        """Test update_stock subtract operation doesn't go below zero."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        # Try to subtract more than available
        response = self.client.post(url, {"quantity": 150, "operation": "subtract"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("0"))

    def test_update_stock_add_operation(self):
        """Test update_stock add operation."""
        url = reverse("api-product-update-stock", args=[self.product.id])
        response = self.client.post(url, {"quantity": 25, "operation": "add"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("125"))


class AuditLogViewSetTests(APITestCase):
    """Test AuditLog ViewSet including permission-protected actions."""

    def setUp(self):
        """Set up test data and authenticate."""
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.admin_user = User.objects.create_superuser(username="admin", password="admin123")

    def test_cleanup_expired_permission_denied(self):
        """Test cleanup_expired action without delete permission."""
        self.client.force_authenticate(user=self.user)

        url = reverse("api-audit-log-cleanup-expired")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], "PERMISSION_DENIED")

    def test_cleanup_expired_success(self):
        """Test cleanup_expired action with proper permissions."""
        self.client.force_authenticate(user=self.admin_user)

        # Create some old audit logs
        old_date = timezone.now() - timezone.timedelta(days=400)
        for i in range(5):
            AuditLog.objects.create(
                user=self.user,
                action="TEST_ACTION",
                object_type="test",
                object_repr=f"test_{i}",
                description=f"Test log {i}",
                timestamp=old_date,
            )

        url = reverse("api-audit-log-cleanup-expired")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("deleted_count", response.data)

    def test_get_queryset_without_permission(self):
        """Test that audit logs are not visible without proper permission."""
        self.client.force_authenticate(user=self.user)

        # Create an audit log
        AuditLog.objects.create(
            user=self.user,
            action="TEST",
            object_type="test",
            object_repr="test",
            description="Test",
        )

        url = reverse("api-audit-log-list")
        response = self.client.get(url)

        # Should return empty list (no permission)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)


class BusinessPartnerImportViewTests(APITestCase):
    """Test BusinessPartner import functionality."""

    def setUp(self):
        """Set up test data and authenticate."""
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

        # Create Germany country
        self.germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "name": "Germany",
                "currency_code": "EUR",
                "standard_vat_rate": 19.00,
            },
        )[0]

    def test_import_business_partners_success(self):
        """Test successful import of business partners."""
        url = reverse("api-business-partner-import")

        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Import Test Corp",
                    "country_code": "DE",
                    "address_line1": "Test Street 1",
                    "postal_code": "12345",
                    "city": "Berlin",
                    "email": "import@test.com",
                    "is_customer": True,
                    "is_supplier": False,
                },
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Another Corp",
                    "country_code": "DE",
                    "address_line1": "Another Street 2",
                    "postal_code": "54321",
                    "city": "Munich",
                    "email": "another@test.com",
                    "is_customer": True,
                    "is_supplier": False,
                },
            ],
            "skip_duplicates": True,
            "update_existing": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 2)
        self.assertEqual(response.data["error_count"], 0)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["imported_ids"]), 2)

    def test_import_business_partners_with_duplicates_skip(self):
        """Test import with duplicates and skip_duplicates=True."""
        # Create existing partner
        BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Existing Corp",
            country=self.germany,
            address_line1="Existing Street",
            postal_code="11111",
            city="Berlin",
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Existing Corp",
                    "country_code": "DE",
                    "address_line1": "Existing Street",
                    "postal_code": "11111",
                    "city": "Berlin",
                },
                {
                    "partner_type": "BUSINESS",
                    "company_name": "New Corp",
                    "country_code": "DE",
                    "address_line1": "New Street",
                    "postal_code": "22222",
                    "city": "Munich",
                },
            ],
            "skip_duplicates": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(response.data["skipped_count"], 1)
        self.assertEqual(response.data["error_count"], 0)

    def test_import_business_partners_with_duplicates_error(self):
        """Test import with duplicates and skip_duplicates=False."""
        # Create existing partner
        BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Existing Corp",
            country=self.germany,
            address_line1="Existing Street",
            postal_code="11111",
            city="Berlin",
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Existing Corp",
                    "country_code": "DE",
                    "address_line1": "Existing Street",
                    "postal_code": "11111",
                    "city": "Berlin",
                }
            ],
            "skip_duplicates": False,
            "update_existing": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(response.data["error_count"], 1)
        self.assertIn("existiert bereits", response.data["errors"][0]["message"])

    def test_import_business_partners_update_existing(self):
        """Test import with update_existing=True."""
        # Create existing partner
        existing = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Update Corp",
            country=self.germany,
            address_line1="Old Street",
            postal_code="33333",
            city="Berlin",
            email="old@test.com",
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Update Corp",
                    "country_code": "DE",
                    "address_line1": "New Street",
                    "postal_code": "33333",
                    "city": "Berlin",
                    "email": "new@test.com",
                }
            ],
            "skip_duplicates": False,
            "update_existing": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)
        existing.refresh_from_db()
        self.assertEqual(existing.email, "new@test.com")
        self.assertEqual(existing.address_line1, "New Street")

    def test_import_business_partners_invalid_data(self):
        """Test import with invalid data."""
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Test Corp",
                    # Missing required fields
                }
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_business_partners_exception_handling(self):
        """Test import with row causing exception."""
        url = reverse("api-business-partner-import")

        # Trigger exception by using invalid data that passes serializer but fails at save
        data = {
            "rows": [
                {
                    "partner_type": "BUSINESS",
                    "company_name": "Test Corp",
                    "country_code": "DE",
                    "address_line1": "Test",
                    "postal_code": "12345",
                    "city": "Test",
                }
            ]
        }

        with mock.patch.object(BusinessPartner.objects, "create", side_effect=IntegrityError("Database error")):
            response = self.client.post(url, data, format="json")

        # Should handle gracefully and report error
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(response.data["error_count"], 1)


class ProductImportViewTests(APITestCase):
    """Test Product import functionality."""

    def setUp(self):
        """Set up test data and authenticate."""
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

    def test_import_products_success(self):
        """Test successful import of products."""
        url = reverse("api-product-import")

        data = {
            "rows": [
                {
                    "product_code": "IMPORT-001",
                    "name": "Import Product 1",
                    "base_price": "100.00",
                    "tax_category": "STANDARD",
                },
                {
                    "product_code": "IMPORT-002",
                    "name": "Import Product 2",
                    "base_price": "50.00",
                    "tax_category": "STANDARD",
                },
            ],
            "skip_duplicates": True,
            "update_existing": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 2)
        self.assertEqual(response.data["error_count"], 0)
        self.assertTrue(response.data["success"])

    def test_import_products_auto_generate_code(self):
        """Test import with auto-generated product codes."""
        url = reverse("api-product-import")

        data = {
            "rows": [
                {
                    # No product_code provided
                    "name": "Auto Code Product",
                    "base_price": "75.00",
                    "tax_category": "STANDARD",
                }
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)

        # Verify product was created with auto-generated code
        product = Product.objects.get(name="Auto Code Product")
        self.assertTrue(product.product_code.startswith("P"))

    def test_import_products_duplicate_by_code_skip(self):
        """Test import with duplicate product code and skip_duplicates=True."""
        # Create existing product
        Product.objects.create(
            product_code="EXISTING-001",
            name="Existing Product",
            base_price=Decimal("100.00"),
        )

        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "product_code": "EXISTING-001",
                    "name": "Duplicate Try",
                    "base_price": "200.00",
                },
                {
                    "product_code": "NEW-001",
                    "name": "New Product",
                    "base_price": "50.00",
                },
            ],
            "skip_duplicates": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(response.data["skipped_count"], 1)

    def test_import_products_duplicate_by_name_skip(self):
        """Test import with duplicate product name and skip_duplicates=True."""
        # Create existing product
        Product.objects.create(
            product_code="PROD-001",
            name="Unique Product Name",
            base_price=Decimal("100.00"),
        )

        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "product_code": "DIFFERENT-001",
                    "name": "Unique Product Name",
                    "base_price": "200.00",
                }
            ],
            "skip_duplicates": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["skipped_count"], 1)

    def test_import_products_duplicate_error(self):
        """Test import with duplicate and skip_duplicates=False."""
        # Create existing product
        Product.objects.create(
            product_code="DUP-001",
            name="Duplicate Product",
            base_price=Decimal("100.00"),
        )

        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "product_code": "DUP-001",
                    "name": "Duplicate Product",
                    "base_price": "200.00",
                }
            ],
            "skip_duplicates": False,
            "update_existing": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(response.data["error_count"], 1)
        self.assertIn("existiert bereits", response.data["errors"][0]["message"])

    def test_import_products_update_existing(self):
        """Test import with update_existing=True."""
        # Create existing product
        existing = Product.objects.create(
            product_code="UPDATE-001",
            name="Update Product",
            base_price=Decimal("100.00"),
            description="Old description",
        )

        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "product_code": "UPDATE-001",
                    "name": "Update Product",
                    "base_price": "150.00",
                    "description": "New description",
                }
            ],
            "update_existing": True,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["imported_count"], 1)
        existing.refresh_from_db()
        self.assertEqual(existing.base_price, Decimal("150.00"))
        self.assertEqual(existing.description, "New description")

    def test_import_products_invalid_data(self):
        """Test import with invalid data."""
        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    # Missing required 'name' field
                    "base_price": "100.00"
                }
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_products_exception_handling(self):
        """Test import with row causing exception."""
        url = reverse("api-product-import")

        # Create a product to test duplicate logic
        Product.objects.create(
            product_code="TEST-001",
            name="Test",
            base_price=Decimal("100.00"),
        )

        # Force an exception by mocking
        with mock.patch.object(Product.objects, "create", side_effect=IntegrityError("Database error")):
            data = {
                "rows": [
                    {
                        "product_code": "FORCE-ERROR",
                        "name": "Will Fail",
                        "base_price": "100.00",
                    }
                ]
            }

            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
            self.assertEqual(response.data["error_count"], 1)
            self.assertGreater(len(response.data["errors"]), 0)


class DashboardStatsViewTests(APITestCase):
    """Test DashboardStatsView error handling."""

    def setUp(self):
        """Set up test data and authenticate."""
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.client.force_authenticate(user=self.user)

    def test_dashboard_stats_success(self):
        """Test successful retrieval of dashboard stats."""
        url = reverse("api-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("invoices", response.data)
        self.assertIn("business_partners", response.data)
        self.assertIn("products", response.data)
        self.assertIn("companies", response.data)

    @mock.patch("invoice_app.api.rest_views.Invoice.objects.aggregate")
    def test_dashboard_stats_exception_handling(self, mock_aggregate):
        """Test dashboard stats with database exception."""
        mock_aggregate.side_effect = OperationalError("Database connection error")

        url = reverse("api-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"]["code"], "SERVICE_UNAVAILABLE")
