"""
Management command to test PDF/A-3 generation for invoices.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from invoice_app.models import Invoice
from invoice_app.services.invoice_service import InvoiceService


class Command(BaseCommand):
    help = "Generate PDF/A-3 with embedded XML for an invoice"

    def add_arguments(self, parser):
        parser.add_argument(
            "invoice_id",
            nargs="?",
            type=int,
            help="ID of the invoice to generate PDF for (optional, uses first invoice if not specified)",
        )
        parser.add_argument(
            "--profile", type=str, default="BASIC", help="ZUGFeRD profile to use (BASIC, COMFORT, or EXTENDED)"
        )

    def handle(self, *args, **options):
        invoice_id = options.get("invoice_id")
        profile = options.get("profile")

        # Get invoice by ID or first available
        try:
            if invoice_id:
                invoice = Invoice.objects.get(pk=invoice_id)
                self.stdout.write(self.style.SUCCESS(f"Using invoice with ID: {invoice_id}"))
            else:
                invoice = Invoice.objects.first()
                if not invoice:
                    raise CommandError("No invoices found in the database")
                self.stdout.write(self.style.SUCCESS(f"Using first invoice: ID {invoice.id}"))

            # Initialize service and generate files
            service = InvoiceService()
            result = service.generate_invoice_files(invoice, zugferd_profile=profile)

            # Output results
            self.stdout.write(self.style.SUCCESS(f"PDF file generated: {result['pdf_path']}"))
            self.stdout.write(self.style.SUCCESS(f"XML file generated: {result['xml_path']}"))
            self.stdout.write(self.style.SUCCESS(f"PDF exists: {os.path.exists(result['pdf_path'])}"))
            self.stdout.write(self.style.SUCCESS(f"XML exists: {os.path.exists(result['xml_path'])}"))

            # Check XML validation
            if result["is_valid"]:
                self.stdout.write(self.style.SUCCESS("XML validation: PASSED"))
            else:
                self.stdout.write(self.style.WARNING("XML validation: FAILED"))
                for error in result["validation_errors"]:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))

            # Update invoice model
            invoice.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"Invoice PDF file path: {invoice.pdf_file}"))
            self.stdout.write(self.style.SUCCESS(f"Invoice XML file path: {invoice.xml_file}"))

        except Invoice.DoesNotExist as e:
            raise CommandError(f"Invoice with ID {invoice_id} does not exist") from e
        except Exception as e:
            raise CommandError(f"Error generating PDF: {str(e)}") from e
