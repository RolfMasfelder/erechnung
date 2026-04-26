#!/usr/bin/env python3
"""
Enhanced PDF inspection script to verify XML embedding in generated invoices.
This script provides multiple methods to inspect PDF files and verify embedded XML content.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path


# Configure logging for structured output
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_django():
    """Setup Django environment for standalone script execution."""
    sys.path.insert(0, "project_root")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoice_project.settings")

    import django

    django.setup()


def inspect_pdf_with_pypdf4(pdf_path):
    """Inspect PDF using PyPDF4 library."""
    try:
        from PyPDF4 import PdfFileReader

        logger.info("=== PyPDF4 Inspection: %s ===", pdf_path)

        with open(pdf_path, "rb") as file:
            reader = PdfFileReader(file, strict=False)

            logger.info("PDF Pages: %d", reader.getNumPages())
            logger.info("PDF Info: %s", reader.getDocumentInfo())

            # Try to access attachments
            if hasattr(reader, "attachments"):
                logger.info("Attachments: %s", reader.attachments)
            else:
                logger.info("PDF reader does not support attachment inspection")

            # Try alternative methods to find embedded files
            if hasattr(reader, "trailer") and reader.trailer:
                trailer = reader.trailer
                logger.debug("Trailer keys: %s", list(trailer.keys()) if trailer else "None")

                # Look for embedded files in the trailer
                if "/Root" in trailer:
                    root = trailer["/Root"]
                    if hasattr(root, "getObject"):
                        root_obj = root.getObject()
                        logger.debug("Root object keys: %s", list(root_obj.keys()) if root_obj else "None")

                        # Check for Names dictionary which might contain embedded files
                        if "/Names" in root_obj:
                            names = root_obj["/Names"].getObject()
                            logger.debug("Names keys: %s", list(names.keys()) if names else "None")

                            if "/EmbeddedFiles" in names:
                                embedded = names["/EmbeddedFiles"].getObject()
                                logger.info("Embedded files found: %s", embedded)

    except ImportError:
        logger.warning("PyPDF4 not available")
    except Exception as e:
        logger.error("PyPDF4 inspection failed: %s", e)


def inspect_pdf_with_pypdf2(pdf_path):
    """Inspect PDF using PyPDF2 library if available."""
    try:
        import PyPDF2

        logger.info("=== PyPDF2 Inspection: %s ===", pdf_path)

        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfFileReader(file, strict=False)

            logger.info("PDF Pages: %d", reader.getNumPages())
            logger.info("PDF Info: %s", reader.getDocumentInfo())

            # Check for attachments
            if hasattr(reader, "attachments"):
                logger.info("Attachments: %s", reader.attachments)
            elif hasattr(reader, "trailer"):
                # Manual search for embedded files
                logger.debug("Searching for embedded files in trailer...")
                trailer = reader.trailer
                if "/Root" in trailer:
                    root = trailer["/Root"].getObject()
                    if "/Names" in root:
                        names = root["/Names"].getObject()
                        if "/EmbeddedFiles" in names:
                            logger.info("Embedded files dictionary found!")
                        else:
                            logger.info("No embedded files found in Names dictionary")
                    else:
                        logger.info("No Names dictionary found in root")

    except ImportError:
        logger.warning("PyPDF2 not available")
    except Exception as e:
        logger.error("PyPDF2 inspection failed: %s", e)


def inspect_pdf_with_pdfplumber(pdf_path):
    """Inspect PDF using pdfplumber library if available."""
    try:
        import pdfplumber

        logger.info("=== pdfplumber Inspection: %s ===", pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            logger.info("PDF Pages: %d", len(pdf.pages))
            logger.info("PDF Metadata: %s", pdf.metadata)

            # pdfplumber doesn't have direct attachment support
            logger.info("pdfplumber: No direct attachment inspection capability")

    except ImportError:
        logger.warning("pdfplumber not available")
    except Exception as e:
        logger.error("pdfplumber inspection failed: %s", e)


def inspect_pdf_with_qpdf(pdf_path):
    """Inspect PDF using qpdf command line tool if available."""
    try:
        logger.info("=== qpdf Command Line Inspection: %s ===", pdf_path)

        # Check if qpdf is available
        result = subprocess.run(["which", "qpdf"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("qpdf not available")
            return

        # Show PDF structure
        result = subprocess.run(["qpdf", "--show-pages", pdf_path], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("PDF Pages info:")
            logger.info(result.stdout)

        # Show all objects
        result = subprocess.run(["qpdf", "--show-all-data", pdf_path], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout
            # Look for embedded files indicators
            if "EmbeddedFile" in output or "/F " in output or "Filespec" in output:
                logger.info("Embedded file indicators found!")
                # Show relevant parts
                lines = output.split("\n")
                for i, line in enumerate(lines):
                    if any(keyword in line for keyword in ["EmbeddedFile", "/F ", "Filespec"]):
                        # Show context around the match
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        logger.info("Context around embedded file:")
                        for j in range(start, end):
                            logger.info("  %s", lines[j])
                        break
            else:
                logger.info("No embedded file indicators found in PDF structure")

    except FileNotFoundError:
        logger.warning("qpdf command not found")
    except subprocess.SubprocessError as e:
        logger.error("qpdf subprocess error: %s", e)
    except Exception as e:
        logger.error("qpdf inspection failed: %s", e)


def inspect_pdf_with_mutool(pdf_path):
    """Inspect PDF using mutool (mupdf) command line tool if available."""
    try:
        logger.info("=== mutool Inspection: %s ===", pdf_path)

        # Check if mutool is available
        result = subprocess.run(["which", "mutool"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("mutool not available")
            return

        # Show PDF info
        result = subprocess.run(["mutool", "info", pdf_path], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("PDF Info:")
            logger.info(result.stdout)

        # Show object structure
        result = subprocess.run(["mutool", "show", pdf_path], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout
            # Look for embedded files
            if "EmbeddedFile" in output or "/Type /Filespec" in output:
                logger.info("Embedded file objects found!")
                lines = output.split("\n")
                for i, line in enumerate(lines):
                    if "EmbeddedFile" in line or "/Type /Filespec" in line:
                        # Show context
                        start = max(0, i - 5)
                        end = min(len(lines), i + 10)
                        logger.info("Embedded file object:")
                        for j in range(start, end):
                            logger.info("  %s", lines[j])
                        logger.info("")
            else:
                logger.info("No embedded file objects found")

    except FileNotFoundError:
        logger.warning("mutool command not found")
    except subprocess.SubprocessError as e:
        logger.error("mutool subprocess error: %s", e)
    except Exception as e:
        logger.error("mutool inspection failed: %s", e)


def find_latest_generated_files():
    """Find the most recently generated PDF and XML files."""
    setup_django()

    from django.conf import settings  # noqa: E402

    pdf_dir = Path(settings.PDF_OUTPUT_DIR)
    xml_dir = Path(settings.XML_OUTPUT_DIR)

    # Find most recent PDF file
    pdf_files = list(pdf_dir.glob("invoice_DEMO-*.pdf"))
    xml_files = list(xml_dir.glob("invoice_DEMO-*.xml"))

    if not pdf_files:
        logger.warning("No generated PDF files found")
        return None, None

    # Sort by modification time and get the latest
    latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
    latest_xml = max(xml_files, key=lambda p: p.stat().st_mtime) if xml_files else None

    return str(latest_pdf), str(latest_xml) if latest_xml else None


def main():
    """Main inspection function."""
    logger.info("=== Enhanced PDF XML Embedding Inspection ===")

    # Find latest generated files
    pdf_path, xml_path = find_latest_generated_files()

    if not pdf_path:
        logger.error("No PDF files to inspect. Run generate_real_invoice.py first.")
        return

    logger.info("Inspecting PDF: %s", pdf_path)
    logger.info("File size: %.1f KB", os.path.getsize(pdf_path) / 1024)

    if xml_path:
        logger.info("Corresponding XML: %s", xml_path)
        logger.info("XML size: %.1f KB", os.path.getsize(xml_path) / 1024)

        # Show first few lines of XML
        with open(xml_path, encoding="utf-8") as f:
            xml_content = f.read()
            lines = xml_content.split("\n")[:10]
            logger.info("XML content preview:")
            for line in lines:
                logger.info("  %s", line)
            if len(xml_content.split("\n")) > 10:
                logger.info("  ...")

    # Run all available inspection methods
    inspect_pdf_with_pypdf4(pdf_path)
    inspect_pdf_with_pypdf2(pdf_path)
    inspect_pdf_with_pdfplumber(pdf_path)
    inspect_pdf_with_qpdf(pdf_path)
    inspect_pdf_with_mutool(pdf_path)

    logger.info("=== Inspection Complete ===")


if __name__ == "__main__":
    main()
