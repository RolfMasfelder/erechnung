"""
Management command to set the invoice sequence starting value.

Used at deployment time so new invoices continue from the customer's
last invoice number without a numbering gap.

Usage:
    python manage.py set_sequence_start 4711
    → Next invoice will get sequence_number 4712.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from invoice_app.models.invoice_models import Invoice


class Command(BaseCommand):
    help = "Set the invoice sequence starting value (next invoice = N+1)"

    def add_arguments(self, parser):
        parser.add_argument(
            "last_number",
            type=int,
            help="The last used sequence number. Next invoice will be last_number + 1.",
        )

    def handle(self, *args, **options):
        last_number = options["last_number"]
        if last_number < 0:
            raise CommandError("Sequence number must be non-negative.")

        seq_name = Invoice.SEQUENCE_NAME

        # Check for existing invoices with higher sequence numbers
        max_existing = (
            Invoice.objects.filter(sequence_number__isnull=False)
            .order_by("-sequence_number")
            .values_list("sequence_number", flat=True)
            .first()
        )

        if max_existing and max_existing > last_number:
            raise CommandError(
                f"Cannot set sequence to {last_number}: invoice with sequence_number={max_existing} already exists."
            )

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT setval('{seq_name}', %s, true)",
                [last_number],
            )
            # Verify
            cursor.execute(f"SELECT last_value FROM {seq_name}")
            confirmed = cursor.fetchone()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f"Sequence '{seq_name}' set to {confirmed}. Next invoice will get sequence_number {confirmed + 1}."
            )
        )
