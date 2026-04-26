#!/usr/bin/env python3
"""
Script to generate a real PDF invoice with embedded XML for manual inspection.
This bypasses all test mocking to create actual files you can examine.
"""

import os
import sys
from datetime import datetime, timedelta

import django


def setup_django():
    """Set up Django environment."""
    sys.path.insert(0, "project_root")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoice_project.settings")
    django.setup()


def main():
    """Generate a real invoice PDF with embedded XML."""
    setup_django()

    # Import after Django setup
    from decimal import Decimal

    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from invoice_app.models import Company, Customer, Invoice, InvoiceLine
    from invoice_app.services.invoice_service import InvoiceService

    User = get_user_model()

    print("🔧 Setting up test data...")

    # Create or get test user
    user, created = User.objects.get_or_create(username="demo_user", defaults={"password": "demo123"})

    # Create or get test company (supplier)
    supplier, created = Company.objects.get_or_create(
        name="Demo Supplier GmbH",
        defaults={
            "tax_id": "DE123456789",
            "vat_id": "DE987654321",
            "address_line1": "Musterstraße 123",
            "postal_code": "10115",
            "city": "Berlin",
            "country": "Germany",
            "email": "contact@demo-supplier.com",
        },
    )

    # Create or get test customer
    customer, created = Customer.objects.get_or_create(
        company_name="Demo Customer AG",
        defaults={
            "tax_id": "DE987654321",
            "address_line1": "Kundenstraße 456",
            "postal_code": "80333",
            "city": "München",
            "country": "Germany",
            "email": "info@demo-customer.com",
        },
    )

    # Create test invoice
    today = timezone.now().date()
    due_date = today + timedelta(days=30)

    invoice_number = f"DEMO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Delete any existing invoice with this number
    Invoice.objects.filter(invoice_number=invoice_number).delete()

    invoice = Invoice.objects.create(
        invoice_number=invoice_number,
        invoice_type=Invoice.InvoiceType.INVOICE,
        company=supplier,
        customer=customer,
        issue_date=today,
        due_date=due_date,
        currency="EUR",
        subtotal=Decimal("450.00"),
        tax_amount=Decimal("85.50"),
        total_amount=Decimal("535.50"),
        status=Invoice.InvoiceStatus.DRAFT,
        created_by=user,
    )

    # Create invoice lines
    InvoiceLine.objects.create(
        invoice=invoice,
        description="Premium Software License",
        quantity=Decimal("1"),
        unit_price=Decimal("300.00"),
        tax_rate=Decimal("19.00"),
        line_total=Decimal("300.00"),
        product_code="SW-PREM-001",
        unit_of_measure=1,  # PCE – Stück
    )

    InvoiceLine.objects.create(
        invoice=invoice,
        description="Professional Consulting (8 hours)",
        quantity=Decimal("8"),
        unit_price=Decimal("150.00"),
        tax_rate=Decimal("19.00"),
        line_total=Decimal("1200.00"),
        product_code="CONS-PRO",
        unit_of_measure=2,  # HUR – Stunde
    )

    InvoiceLine.objects.create(
        invoice=invoice,
        description="Hardware Support Package",
        quantity=Decimal("1"),
        unit_price=Decimal("250.00"),
        tax_rate=Decimal("19.00"),
        line_total=Decimal("250.00"),
        product_code="HW-SUPP-001",
        unit_of_measure=1,  # PCE – Stück
    )

    print(f"📄 Created invoice: {invoice_number}")
    print(f"   Supplier: {supplier.name}")
    print(f"   Customer: {customer.company_name}")
    print(f"   Total: {invoice.total_amount} {invoice.currency}")
    print(f"   Lines: {invoice.lines.count()}")

    # Generate the PDF with embedded XML
    print("\n🚀 Generating PDF with embedded XML...")

    try:
        service = InvoiceService()
        result = service.generate_invoice_files(invoice, "COMFORT")

        if result["is_valid"]:
            print("✅ PDF generation successful!")
            print(f"📄 PDF file: {result.get('pdf_path', 'Not available')}")
            print(f"📋 XML file: {result.get('xml_path', 'Not available')}")

            # Check file sizes
            pdf_path = result.get("pdf_path")
            xml_path = result.get("xml_path")

            if pdf_path and os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path)
                print(f"   PDF size: {pdf_size:,} bytes")
                if pdf_size < 1000:
                    print("   ⚠️  Warning: PDF file seems very small!")

            if xml_path and os.path.exists(xml_path):
                xml_size = os.path.getsize(xml_path)
                print(f"   XML size: {xml_size:,} bytes")

                # Show first few lines of XML
                print("\n📋 XML content preview:")
                with open(xml_path, encoding="utf-8") as f:
                    lines = f.readlines()[:10]
                    for i, line in enumerate(lines, 1):
                        print(f"   {i:2d}: {line.rstrip()}")
                    if len(lines) >= 10:
                        print("   ... (truncated)")

            # Print validation results
            if result.get("validation_errors"):
                print(f"\n⚠️  Validation warnings: {len(result['validation_errors'])}")
                for error in result["validation_errors"][:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(result["validation_errors"]) > 5:
                    print(f"   ... and {len(result['validation_errors']) - 5} more")
            else:
                print("\n✅ No validation errors!")

        else:
            print("❌ PDF generation failed!")
            print(f"Errors: {result.get('validation_errors', [])}")

    except Exception as e:
        print(f"❌ Error during PDF generation: {e}")
        import traceback

        traceback.print_exc()

    print("\n💡 You can find the generated files in:")
    print("   PDF: project_root/media/invoices/")
    print("   XML: project_root/media/xml/")
    print(f"\n📝 Invoice saved in database with ID: {invoice.id}")


if __name__ == "__main__":
    main()
