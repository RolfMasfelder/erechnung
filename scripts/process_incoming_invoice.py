#!/usr/bin/env python3
"""
Incoming Invoice Processing Script using the new utility architecture.

This script demonstrates how to use the refactored utilities for processing
incoming supplier invoices. It serves as both a command-line tool and an
example of how to integrate the incoming invoice functionality.

Usage Examples:
    # Process a single incoming invoice
    python process_incoming_invoice.py --file /path/to/supplier_invoice.pdf

    # Process all invoices in a directory (e.g., email attachments folder)
    python process_incoming_invoice.py --batch /path/to/invoices_folder

    # Generate compliance report
    python process_incoming_invoice.py --report
"""

import os
import sys
from pathlib import Path


def setup_django():
    """Setup Django environment for standalone script execution."""
    sys.path.insert(0, "project_root")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoice_project.settings")

    import django

    django.setup()


def main():
    """Main function with command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Process incoming invoices using the new utility architecture")
    parser.add_argument("--file", help="Process a single invoice file")
    parser.add_argument("--batch", help="Process all invoices in a directory")
    parser.add_argument("--report", action="store_true", help="Generate processing report")

    args = parser.parse_args()

    # Setup Django
    setup_django()

    # Import services after Django setup
    from invoice_app.services import IncomingInvoiceService  # noqa: E402

    # Initialize the service
    service = IncomingInvoiceService()

    if args.file:
        # Process single file
        result = service.process_single_invoice(args.file)
        print(f"\nResult: {result.message}")

        if result.success:
            print(f"Invoice ID: {result.invoice_id}")
        else:
            print("Processing failed.")

    elif args.batch:
        # Process batch
        results = service.process_batch(args.batch)

        print(results.get_summary())

        if results.details:
            print("\nDetailed Results:")
            for detail in results.details:
                print(f"  {detail['status']}: {detail['file']}")
                if detail.get("invoice_id"):
                    print(f"    Invoice ID: {detail['invoice_id']}")

    elif args.report:
        # Generate report
        from datetime import datetime  # noqa: E402

        from invoice_app.models import Invoice  # noqa: E402

        # Find incoming invoices by checking notes field for "INCOMING INVOICE"
        incoming_invoices = Invoice.objects.filter(notes__contains="INCOMING INVOICE").order_by("-created_at")

        report_lines = [
            "INCOMING INVOICE PROCESSING REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total incoming invoices: {incoming_invoices.count()}",
            "",
        ]

        if incoming_invoices.exists():
            report_lines.extend(["Recent incoming invoices:", "-" * 30])

            for invoice in incoming_invoices[:20]:  # Show last 20
                report_lines.extend(
                    [
                        f"ID: {invoice.id}",
                        f"  Number: {invoice.invoice_number}",
                        f"  Supplier: {invoice.company.name}",
                        f"  Amount: {invoice.total_amount} {invoice.currency}",
                        f"  Date: {invoice.issue_date}",
                        f"  Status: {invoice.status}",
                        f"  Processed: {invoice.created_at.strftime('%Y-%m-%d %H:%M')}",
                        "",
                    ]
                )

        report = "\n".join(report_lines)
        print(report)

        # Also save to file
        report_path = Path("incoming_invoice_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")

    else:
        print("Please specify --file, --batch, or --report")
        print("Use --help for more information")
        print("\nThis script uses the new utility architecture:")
        print("  - invoice_app.utils.incoming_xml: XML parsing")
        print("  - invoice_app.utils.validation: Validation")
        print("  - invoice_app.services.incoming_invoice_service: Orchestration")


if __name__ == "__main__":
    main()
