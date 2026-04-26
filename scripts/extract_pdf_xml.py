#!/usr/bin/env python3
"""
PDF XML Extraction utility to extract and verify embedded XML from PDF/A-3 files.
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


def extract_xml_from_pdf(pdf_path):
    """
    Extract embedded XML from PDF/A-3 file using PyPDF4.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted XML content or None if extraction failed
    """
    try:
        from PyPDF4 import PdfFileReader

        print(f"\n=== Extracting XML from: {pdf_path} ===")

        with open(pdf_path, "rb") as file:
            reader = PdfFileReader(file, strict=False)

            # Navigate to embedded files
            if hasattr(reader, "trailer") and reader.trailer:
                trailer = reader.trailer

                if "/Root" in trailer:
                    root = trailer["/Root"].getObject()

                    if "/Names" in root:
                        names = root["/Names"].getObject()

                        if "/EmbeddedFiles" in names:
                            embedded_files = names["/EmbeddedFiles"].getObject()
                            print(f"Found embedded files structure: {embedded_files}")

                            # Extract the embedded file names and file specs
                            if "/Names" in embedded_files:
                                names_array = embedded_files["/Names"]
                                print(f"Names array length: {len(names_array)}")

                                # Names array contains alternating filename/filespec pairs
                                for i in range(0, len(names_array), 2):
                                    if i + 1 < len(names_array):
                                        filename = names_array[i]
                                        filespec = names_array[i + 1].getObject()

                                        print(f"Processing embedded file: {filename}")
                                        print(f"Filespec: {filespec}")

                                        # Get the actual embedded file data
                                        if "/EF" in filespec and "/F" in filespec["/EF"]:
                                            file_stream = filespec["/EF"]["/F"].getObject()
                                            print(f"File stream object: {file_stream}")

                                            if hasattr(file_stream, "getData"):
                                                # Try to get the raw data
                                                xml_data = file_stream.getData()
                                                xml_content = xml_data.decode("utf-8")

                                                print(f"Successfully extracted XML ({len(xml_content)} characters)")
                                                return xml_content

                                            elif "/Length" in file_stream:
                                                # Alternative method to access stream data
                                                print(f"Stream length: {file_stream['/Length']}")

                                                # Some PyPDF versions store data differently
                                                if hasattr(file_stream, "_data"):
                                                    xml_data = file_stream._data
                                                    xml_content = xml_data.decode("utf-8")
                                                    print(f"Extracted XML via _data ({len(xml_content)} characters)")
                                                    return xml_content

        print("Could not extract XML content from PDF")
        return None

    except Exception as e:
        print(f"Error extracting XML from PDF: {e}")
        import traceback

        traceback.print_exc()
        return None


def validate_extracted_xml(xml_content):
    """
    Validate the extracted XML content against our schemas.

    Args:
        xml_content (str): XML content to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not xml_content:
        return False

    try:
        setup_django()
        from invoice_app.utils.xml import ZugferdXmlValidator  # noqa: E402

        print("\n=== Validating Extracted XML ===")

        # Create validator and validate
        validator = ZugferdXmlValidator()
        is_valid, errors = validator.validate_xml(xml_content)

        if is_valid:
            print("✅ Extracted XML is valid according to ZUGFeRD schema!")
        else:
            print("❌ Extracted XML validation failed:")
            for error in errors:
                print(f"  - {error}")

        return is_valid

    except Exception as e:
        print(f"Error validating extracted XML: {e}")
        return False


def compare_xml_files(extracted_xml, original_xml_path):
    """
    Compare extracted XML with the original XML file.

    Args:
        extracted_xml (str): XML content extracted from PDF
        original_xml_path (str): Path to original XML file

    Returns:
        bool: True if they match, False otherwise
    """
    try:
        if not extracted_xml or not os.path.exists(original_xml_path):
            return False

        print(f"\n=== Comparing with original XML: {original_xml_path} ===")

        with open(original_xml_path, encoding="utf-8") as f:
            original_xml = f.read()

        # Normalize whitespace for comparison
        def normalize_xml(xml_str):
            import re

            # Remove extra whitespace and newlines
            normalized = re.sub(r">\s+<", "><", xml_str.strip())
            return normalized

        extracted_normalized = normalize_xml(extracted_xml)
        original_normalized = normalize_xml(original_xml)

        if extracted_normalized == original_normalized:
            print("✅ Extracted XML matches original XML file exactly!")
            return True
        else:
            print("❌ Extracted XML differs from original XML file")
            print(f"Original length: {len(original_xml)} characters")
            print(f"Extracted length: {len(extracted_xml)} characters")

            # Show first difference
            for i, (orig_char, extr_char) in enumerate(zip(original_xml, extracted_xml, strict=False)):
                if orig_char != extr_char:
                    print(f"First difference at position {i}:")
                    print(f"  Original: '{orig_char}' (ord {ord(orig_char)})")
                    print(f"  Extracted: '{extr_char}' (ord {ord(extr_char)})")
                    break

            return False

    except Exception as e:
        print(f"Error comparing XML files: {e}")
        return False


def main():
    """Main extraction and verification function."""
    print("=== PDF XML Extraction and Verification ===")

    # Find latest generated files
    setup_django()
    from django.conf import settings  # noqa: E402

    pdf_dir = Path(settings.PDF_OUTPUT_DIR)
    xml_dir = Path(settings.XML_OUTPUT_DIR)

    # Find most recent PDF file
    pdf_files = list(pdf_dir.glob("invoice_DEMO-*.pdf"))

    if not pdf_files:
        print("No generated PDF files found. Run generate_real_invoice.py first.")
        return

    # Sort by modification time and get the latest
    latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)

    # Find corresponding XML file
    pdf_name = latest_pdf.stem  # Get filename without extension
    xml_path = xml_dir / f"{pdf_name}.xml"

    print(f"Analyzing PDF: {latest_pdf}")
    print(f"File size: {latest_pdf.stat().st_size / 1024:.1f} KB")

    if xml_path.exists():
        print(f"Original XML: {xml_path}")
        print(f"XML size: {xml_path.stat().st_size / 1024:.1f} KB")

    # Extract XML from PDF
    extracted_xml = extract_xml_from_pdf(str(latest_pdf))

    if extracted_xml:
        print("\n=== Extracted XML Preview (first 500 characters) ===")
        print(extracted_xml[:500])
        if len(extracted_xml) > 500:
            print("...")

        # Validate extracted XML
        validate_extracted_xml(extracted_xml)

        # Compare with original if available
        if xml_path.exists():
            compare_xml_files(extracted_xml, str(xml_path))

        # Save extracted XML for inspection
        extracted_xml_path = pdf_dir / f"{pdf_name}_extracted.xml"
        with open(extracted_xml_path, "w", encoding="utf-8") as f:
            f.write(extracted_xml)
        print(f"\n💾 Extracted XML saved to: {extracted_xml_path}")

    else:
        print("❌ Failed to extract XML from PDF")

    print("\n=== Extraction Complete ===")


if __name__ == "__main__":
    main()
