"""
Tests for InvoiceAttachment model and API (Phase A: Rechnungsbegründende Dokumente).

Covers:
- Model fields: attachment_type, mime_type, original_filename
- Upload path generation (invoices/attachments/invoice_{number}/)
- File size validation (max 10 MB)
- File extension validation (PDF, PNG, JPEG, CSV, XLSX)
- Auto-detection of original_filename and mime_type on save
- API CRUD with new fields
"""

import shutil
import tempfile
from decimal import Decimal
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.models import AttachmentType, BusinessPartner, Company, Country, Invoice, InvoiceAttachment
from invoice_app.models.invoice_models import attachment_upload_path


class AttachmentUploadPathTests(TestCase):
    """Test the upload path generation function."""

    def test_path_contains_invoice_number(self):
        invoice = MagicMock()
        invoice.invoice_number = "INV-2026-001"
        instance = MagicMock()
        instance.invoice = invoice
        instance.invoice_id = 1

        result = attachment_upload_path(instance, "Lieferschein.pdf")
        self.assertEqual(result, "invoices/attachments/invoice_INV-2026-001/Lieferschein.pdf")

    def test_path_sanitizes_filename(self):
        invoice = MagicMock()
        invoice.invoice_number = "INV-001"
        instance = MagicMock()
        instance.invoice = invoice
        instance.invoice_id = 1

        result = attachment_upload_path(instance, "Rechnung (Kopie).pdf")
        self.assertIn("invoice_INV-001", result)
        # Django's get_valid_filename sanitizes spaces/parens
        self.assertNotIn("(", result)

    def test_path_with_unknown_invoice(self):
        instance = MagicMock()
        instance.invoice_id = None

        result = attachment_upload_path(instance, "test.pdf")
        self.assertIn("invoice_unknown", result)


class AttachmentModelTests(TestCase):
    """Test InvoiceAttachment model fields and behaviour."""

    @classmethod
    def setUpClass(cls):
        cls._temp_media_dir = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_dir, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.germany = Country.objects.get_or_create(
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

        cls.company = Company.objects.create(
            name="Test GmbH",
            tax_id="DE111111111",
            vat_id="DE111111111",
            address_line1="Teststr. 1",
            postal_code="10115",
            city="Berlin",
            country=cls.germany,
            email="test@example.com",
        )

        cls.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Kunde AG",
            tax_id="DE222222222",
            address_line1="Kundenstr. 2",
            postal_code="80333",
            city="München",
            country=cls.germany,
            email="kunde@example.com",
        )

        from django.contrib.auth import get_user_model

        cls.user = get_user_model().objects.create_user("testuser", password="pass")

        cls.invoice = Invoice.objects.create(
            invoice_number="INV-ATT-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=cls.company,
            business_partner=cls.partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            currency="EUR",
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
            total_amount=Decimal("119.00"),
            created_by=cls.user,
        )

    def test_default_attachment_type(self):
        f = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        att = InvoiceAttachment.objects.create(
            invoice=self.invoice,
            file=f,
            description="Beleg",
        )
        self.assertEqual(att.attachment_type, AttachmentType.SUPPORTING_DOCUMENT)

    def test_auto_detect_original_filename(self):
        f = SimpleUploadedFile("Lieferschein_2026.pdf", b"%PDF-1.4", content_type="application/pdf")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Lieferschein")
        att.save()
        self.assertEqual(att.original_filename, "Lieferschein_2026.pdf")

    def test_auto_detect_mime_type_pdf(self):
        f = SimpleUploadedFile("test.pdf", b"%PDF-1.4", content_type="application/pdf")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="PDF")
        att.save()
        self.assertEqual(att.mime_type, "application/pdf")

    def test_auto_detect_mime_type_png(self):
        f = SimpleUploadedFile("scan.png", b"\x89PNG", content_type="image/png")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Scan")
        att.save()
        self.assertEqual(att.mime_type, "image/png")

    def test_auto_detect_mime_type_jpeg(self):
        f = SimpleUploadedFile("photo.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Foto")
        att.save()
        self.assertEqual(att.mime_type, "image/jpeg")

    def test_auto_detect_mime_type_csv(self):
        f = SimpleUploadedFile("data.csv", b"a,b,c\n1,2,3", content_type="text/csv")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Daten")
        att.save()
        self.assertEqual(att.mime_type, "text/csv")

    def test_auto_detect_mime_type_xlsx(self):
        f = SimpleUploadedFile("sheet.xlsx", b"PK\x03\x04", content_type="application/octet-stream")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Tabelle")
        att.save()
        self.assertEqual(att.mime_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_attachment_type_choices(self):
        f = SimpleUploadedFile("note.pdf", b"%PDF", content_type="application/pdf")
        att = InvoiceAttachment.objects.create(
            invoice=self.invoice,
            file=f,
            description="Notiz",
            attachment_type=AttachmentType.TIMESHEET,
        )
        self.assertEqual(att.attachment_type, "timesheet")

    def test_str_uses_original_filename(self):
        f = SimpleUploadedFile("Zeitaufstellung.pdf", b"%PDF", content_type="application/pdf")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Zeiten")
        att.save()
        self.assertIn("Zeitaufstellung.pdf", str(att))
        self.assertIn("INV-ATT-001", str(att))

    def test_file_extension_validation_rejects_exe(self):
        f = SimpleUploadedFile("malware.exe", b"\x4d\x5a", content_type="application/octet-stream")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Bad file")
        with self.assertRaises(ValidationError):
            att.full_clean()

    def test_file_extension_validation_rejects_js(self):
        f = SimpleUploadedFile("script.js", b"alert(1)", content_type="application/javascript")
        att = InvoiceAttachment(invoice=self.invoice, file=f, description="Bad file")
        with self.assertRaises(ValidationError):
            att.full_clean()


class AttachmentAPITests(APITestCase):
    """Test InvoiceAttachment API endpoints with new fields."""

    @classmethod
    def setUpClass(cls):
        cls._temp_media_dir = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media_dir, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.germany = Country.objects.get_or_create(
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

        cls.company = Company.objects.create(
            name="API Test GmbH",
            tax_id="DE333333333",
            vat_id="DE333333333",
            address_line1="APIstr. 1",
            postal_code="10115",
            city="Berlin",
            country=cls.germany,
            email="api@example.com",
        )

        cls.partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="API Kunde AG",
            tax_id="DE444444444",
            address_line1="Kundenstr. 4",
            postal_code="80333",
            city="München",
            country=cls.germany,
            email="apikunde@example.com",
        )

        from django.contrib.auth import get_user_model

        cls.user = get_user_model().objects.create_user("apiuser", password="pass")

        cls.invoice = Invoice.objects.create(
            invoice_number="INV-API-ATT-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=cls.company,
            business_partner=cls.partner,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            currency="EUR",
            subtotal=Decimal("200.00"),
            tax_amount=Decimal("38.00"),
            total_amount=Decimal("238.00"),
            created_by=cls.user,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_create_attachment_with_type(self):
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("Lieferschein.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Lieferschein März 2026",
            "attachment_type": "delivery_note",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["attachment_type"], "delivery_note")
        self.assertEqual(response.data["original_filename"], "Lieferschein.pdf")
        self.assertEqual(response.data["mime_type"], "application/pdf")

    def test_create_attachment_default_type(self):
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("beleg.pdf", b"%PDF-1.4", content_type="application/pdf")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Allgemeiner Beleg",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["attachment_type"], "supporting_document")

    def test_create_attachment_png(self):
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, content_type="image/png")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Scan eines Belegs",
            "attachment_type": "other",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mime_type"], "image/png")

    def test_reject_disallowed_extension(self):
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("script.html", b"<script>alert(1)</script>", content_type="text/html")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Should be rejected",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_oversized_file(self):
        url = reverse("api-invoice-attachment-list")
        # Create a file >10 MB
        f = SimpleUploadedFile("large.pdf", b"x" * (10 * 1024 * 1024 + 1), content_type="application/pdf")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Too large",
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_new_fields(self):
        """Verify list response includes original_filename, attachment_type, mime_type."""
        f = SimpleUploadedFile("zeitaufstellung.csv", b"date,hours\n2026-03-01,8", content_type="text/csv")
        InvoiceAttachment.objects.create(
            invoice=self.invoice,
            file=f,
            description="Zeiten",
            attachment_type="timesheet",
        )
        url = reverse("api-invoice-attachment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"] if "results" in response.data else response.data
        att = results[0]
        self.assertIn("original_filename", att)
        self.assertIn("attachment_type", att)
        self.assertIn("mime_type", att)

    def test_original_filename_is_readonly(self):
        """original_filename should be auto-set, not writable via API."""
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("real_name.pdf", b"%PDF-1.4", content_type="application/pdf")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Test",
            "original_filename": "fake_name.pdf",  # Should be ignored
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["original_filename"], "real_name.pdf")

    def test_mime_type_is_readonly(self):
        """mime_type should be auto-detected, not writable via API."""
        url = reverse("api-invoice-attachment-list")
        f = SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf")
        data = {
            "invoice": self.invoice.id,
            "file": f,
            "description": "Test",
            "mime_type": "text/plain",  # Should be ignored
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mime_type"], "application/pdf")
