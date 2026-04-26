import logging

from celery import shared_task


logger = logging.getLogger(__name__)


@shared_task(
    name="invoice_app.generate_invoice_pdf_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def generate_invoice_pdf_task(self, invoice_id, zugferd_profile="COMFORT"):
    """Async PDF/A-3 generation via Celery (Issue #4).

    Enabled via settings.ENABLE_ASYNC_PDF (default: False).
    Generates PDF/A-3 with embedded ZUGFeRD XML for the given invoice.
    """
    from invoice_app.models import Invoice
    from invoice_app.services.invoice_service import InvoiceService

    try:
        invoice = Invoice.objects.get(pk=invoice_id)
        service = InvoiceService()
        result = service.generate_invoice_files(invoice, zugferd_profile)

        logger.info(
            "Async PDF generated for invoice %s (valid=%s)",
            invoice.invoice_number,
            result["is_valid"],
        )
        return {
            "invoice_id": invoice_id,
            "pdf_path": result["pdf_path"],
            "is_valid": result["is_valid"],
            "validation_errors": result["validation_errors"],
        }
    except Invoice.DoesNotExist:
        logger.error("Invoice %s not found for async PDF generation", invoice_id)
        raise
    except Exception as exc:
        logger.error("Async PDF generation failed for invoice %s: %s", invoice_id, exc)
        raise self.retry(exc=exc) from exc
