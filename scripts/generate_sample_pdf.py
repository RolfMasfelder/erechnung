#!/usr/bin/env python
"""
Simple script to generate a sample PDF for demonstration.
"""

import logging
import os
import sys
from pathlib import Path

import django


# Configure logging for structured output
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Dynamically resolve project_root (works in container and on host)
REPO_BASE = Path(__file__).resolve().parent.parent  # repo root
PROJECT_ROOT = REPO_BASE / "project_root"

if not PROJECT_ROOT.exists():  # Fail fast with helpful message
    logger.error("project_root not found at: %s", PROJECT_ROOT)
    logger.error("Current __file__: %s", __file__)
    sys.exit(1)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoice_project.settings")
django.setup()

from invoice_app.utils.pdf import PDF_BACKEND, PdfA3Generator  # noqa: E402


def main():
    # Sample invoice data
    invoice_data = {
        "number": "DEMO-2025-001",
        "date": "2025-07-25",
        "due_date": "2025-08-25",
        "currency": "EUR",
        "customer": {
            "name": "Demo Customer GmbH",
            "address": "Demo Street 123, 12345 Demo City",
            "email": "demo@customer.com",
            "tax_id": "DE123456789",
        },
        "items": [
            {"product_name": "Software License", "quantity": 1, "price": 999.00, "tax_rate": 19.0},
            {"product_name": "Support Service", "quantity": 12, "price": 150.00, "tax_rate": 19.0},
            {"product_name": "Training", "quantity": 2, "price": 500.00, "tax_rate": 19.0},
        ],
    }

    # Sample XML content
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
        <ID>DEMO-2025-001</ID>
        <IssueDate>2025-07-25</IssueDate>
        <DueDate>2025-08-25</DueDate>
        <DocumentCurrencyCode>EUR</DocumentCurrencyCode>
        <AccountingSupplierParty>
            <Party>
                <PartyName>
                    <Name>eRechnung Demo Company</Name>
                </PartyName>
            </Party>
        </AccountingSupplierParty>
        <AccountingCustomerParty>
            <Party>
                <PartyName>
                    <Name>Demo Customer GmbH</Name>
                </PartyName>
            </Party>
        </AccountingCustomerParty>
    </Invoice>
    """

    # Create PDF generator
    pdf_generator = PdfA3Generator()

    logger.info("Generating sample PDF...")
    logger.info("PDF backend in use: %s", PDF_BACKEND)
    logger.info("PDF output directory: %s", pdf_generator.output_dir)
    logger.info("XML output directory: %s", pdf_generator.xml_dir)

    try:
        # Generate the PDF
        result = pdf_generator.generate_invoice_pdf(invoice_data, xml_content)

        logger.info("PDF generation successful!")
        logger.info("PDF Path: %s", result["pdf_path"])
        logger.info("XML Path: %s", result["xml_path"])

        # Check file sizes
        if os.path.exists(result["pdf_path"]):
            pdf_size = os.path.getsize(result["pdf_path"])
            logger.info("PDF Size: %.1f KB", pdf_size / 1024)

        if result["xml_path"] and os.path.exists(result["xml_path"]):
            xml_size = os.path.getsize(result["xml_path"])
            logger.info("XML Size: %.1f KB", xml_size / 1024)

    except FileNotFoundError as e:
        logger.error("File not found during PDF generation: %s", e)
        return 1
    except PermissionError as e:
        logger.error("Permission denied during PDF generation: %s", e)
        return 1
    except Exception as e:
        logger.error("Error generating PDF: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
