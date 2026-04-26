"""Tests for Celery tasks (async PDF generation)."""

from unittest import mock

from django.test import TestCase

from invoice_app.tasks import generate_invoice_pdf_task


class TestGenerateInvoicePdfTask(TestCase):
    """Tests for the async PDF generation Celery task (Issue #4)."""

    @mock.patch("invoice_app.services.invoice_service.InvoiceService.generate_invoice_files")
    @mock.patch("invoice_app.models.Invoice.objects")
    def test_task_success(self, mock_objects, mock_generate):
        """Test successful async PDF generation."""
        mock_invoice = mock.MagicMock()
        mock_invoice.invoice_number = "INV-001"
        mock_objects.get.return_value = mock_invoice

        mock_generate.return_value = {
            "pdf_path": "/tmp/test.pdf",
            "is_valid": True,
            "validation_errors": [],
        }

        result = generate_invoice_pdf_task(42, "COMFORT")

        mock_objects.get.assert_called_once_with(pk=42)
        mock_generate.assert_called_once_with(mock_invoice, "COMFORT")
        self.assertEqual(result["invoice_id"], 42)
        self.assertTrue(result["is_valid"])

    @mock.patch("invoice_app.models.Invoice.objects")
    def test_task_invoice_not_found(self, mock_objects):
        """Test task raises when invoice does not exist."""
        from invoice_app.models import Invoice

        mock_objects.get.side_effect = Invoice.DoesNotExist

        with self.assertRaises(Invoice.DoesNotExist):
            generate_invoice_pdf_task(999)
