#!/usr/bin/env python3
"""
Comprehensive Invoice Validation Utility for ZUGFeRD/Factur-X invoices.

This utility can validate:
1. PDF/A-3 files with embedded XML (incoming invoices)
2. Standalone XML files (extracted or received separately)
3. Generated invoices (outgoing validation)

Supports both XSD schema validation and business rule validation.
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


class InvoiceValidationResult:
    """Container for invoice validation results."""

    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.info = []
        self.extracted_xml = None
        self.validation_type = None
        self.file_path = None
        self.xml_size = 0
        self.pdf_size = 0

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add validation information."""
        self.info.append(message)

    def print_summary(self):
        """Print a comprehensive validation summary."""
        print(f"\n{'=' * 60}")
        print(f"VALIDATION SUMMARY: {self.validation_type}")
        print(f"{'=' * 60}")

        if self.file_path:
            print(f"File: {self.file_path}")
            if self.pdf_size > 0:
                print(f"PDF Size: {self.pdf_size / 1024:.1f} KB")
            if self.xml_size > 0:
                print(f"XML Size: {self.xml_size / 1024:.1f} KB")

        status_icon = "✅" if self.is_valid else "❌"
        print(f"\nOverall Status: {status_icon} {'VALID' if self.is_valid else 'INVALID'}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        if self.info:
            print(f"\n📋 INFORMATION ({len(self.info)}):")
            for i, info in enumerate(self.info, 1):
                print(f"  {i}. {info}")

        print(f"{'=' * 60}")


class ComprehensiveInvoiceValidator:
    """
    Comprehensive validator for ZUGFeRD/Factur-X invoices.

    Can validate:
    - PDF/A-3 files with embedded XML
    - Standalone XML files
    - Business rules and data consistency
    """

    def __init__(self):
        """Initialize the validator."""
        setup_django()
        self._load_django_components()

    def _load_django_components(self):
        """Load Django components after setup."""
        from django.conf import settings  # noqa: E402
        from invoice_app.utils.xml import ZugferdXmlValidator  # noqa: E402

        self.xml_validator = ZugferdXmlValidator()
        self.settings = settings

    def extract_xml_from_pdf(self, pdf_path: str) -> str | None:
        """
        Extract embedded XML from PDF/A-3 file.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: Extracted XML content or None if extraction failed
        """
        try:
            from PyPDF4 import PdfFileReader

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

                                # Extract the embedded file names and file specs
                                if "/Names" in embedded_files:
                                    names_array = embedded_files["/Names"]

                                    # Names array contains alternating filename/filespec pairs
                                    for i in range(0, len(names_array), 2):
                                        if i + 1 < len(names_array):
                                            filename = names_array[i]
                                            filespec = names_array[i + 1].getObject()

                                            # Look for XML files
                                            if filename.lower().endswith(".xml"):
                                                # Get the actual embedded file data
                                                if "/EF" in filespec and "/F" in filespec["/EF"]:
                                                    file_stream = filespec["/EF"]["/F"].getObject()

                                                    if hasattr(file_stream, "getData"):
                                                        xml_data = file_stream.getData()
                                                        xml_content = xml_data.decode("utf-8")
                                                        return xml_content

                                                    elif "/Length" in file_stream and hasattr(file_stream, "_data"):
                                                        xml_data = file_stream._data
                                                        xml_content = xml_data.decode("utf-8")
                                                        return xml_content

            return None

        except Exception as e:
            print(f"Error extracting XML from PDF: {e}")
            return None

    def validate_xml_schema(self, xml_content: str) -> tuple[bool, list[str]]:
        """
        Validate XML content against ZUGFeRD/Factur-X schemas.

        Args:
            xml_content (str): XML content to validate

        Returns:
            tuple: (is_valid, error_list)
        """
        try:
            return self.xml_validator.validate_xml(xml_content)
        except Exception as e:
            return False, [f"Schema validation error: {e}"]

    def validate_business_rules(self, xml_content: str) -> tuple[bool, list[str], list[str]]:
        """
        Validate business rules for invoice data.

        Args:
            xml_content (str): XML content to validate

        Returns:
            tuple: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        try:
            from lxml import etree

            # Parse XML
            root = etree.fromstring(xml_content.encode("utf-8"))

            # Define namespace
            ns = {
                "inv": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
                "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
                "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
            }

            # Business Rule 1: Invoice must have a valid ID
            invoice_id = root.find(".//inv:Header/inv:ID", ns)
            if invoice_id is None or not invoice_id.text or not invoice_id.text.strip():
                errors.append("Invoice ID is missing or empty")

            # Business Rule 2: Invoice must have a valid issue date
            issue_date = root.find(".//inv:Header/inv:IssueDateTime/udt:DateTimeString", ns)
            if issue_date is None or not issue_date.text:
                errors.append("Invoice issue date is missing")
            else:
                # Check date format (should be YYYYMMDD for format="102")
                date_format = issue_date.get("format")
                if date_format == "102" and len(issue_date.text) != 8:
                    errors.append(f"Invalid date format: {issue_date.text} (expected YYYYMMDD)")

            # Business Rule 3: Invoice must have seller information
            seller_name = root.find(".//inv:SellerTradeParty/ram:Name", ns)
            if seller_name is None or not seller_name.text:
                errors.append("Seller name is missing")

            # Business Rule 4: Invoice must have buyer information
            buyer_name = root.find(".//inv:BuyerTradeParty/ram:Name", ns)
            if buyer_name is None or not buyer_name.text:
                errors.append("Buyer name is missing")

            # Business Rule 5: Check for line items
            line_items = root.findall(".//inv:LineItem", ns)
            if not line_items:
                warnings.append("No line items found in invoice")

            # Business Rule 6: Validate totals if present
            grand_total = root.find(".//inv:DocumentTotals/inv:GrandTotal", ns)
            if grand_total is not None:
                try:
                    total_value = float(grand_total.text)
                    if total_value < 0:
                        warnings.append("Invoice total is negative")
                    elif total_value == 0:
                        warnings.append("Invoice total is zero")
                except ValueError:
                    errors.append(f"Invalid grand total format: {grand_total.text}")

            # Business Rule 7: Check currency code
            currency = root.find(".//inv:DocumentTotals/inv:InvoiceCurrencyCode", ns)
            if currency is not None:
                valid_currencies = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD"]
                if currency.text not in valid_currencies:
                    warnings.append(f"Unusual currency code: {currency.text}")

            is_valid = len(errors) == 0
            return is_valid, errors, warnings

        except Exception as e:
            errors.append(f"Business rule validation error: {e}")
            return False, errors, warnings

    def validate_pdf_file(self, pdf_path: str) -> InvoiceValidationResult:
        """
        Validate a PDF/A-3 invoice file with embedded XML.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            InvoiceValidationResult: Comprehensive validation results
        """
        result = InvoiceValidationResult()
        result.validation_type = "PDF/A-3 Invoice with Embedded XML"
        result.file_path = pdf_path

        # Check if file exists
        if not os.path.exists(pdf_path):
            result.add_error(f"PDF file not found: {pdf_path}")
            return result

        # Get file size
        result.pdf_size = os.path.getsize(pdf_path)
        result.add_info(f"PDF file size: {result.pdf_size / 1024:.1f} KB")

        # Extract XML from PDF
        result.add_info("Extracting XML from PDF...")
        xml_content = self.extract_xml_from_pdf(pdf_path)

        if not xml_content:
            result.add_error("Could not extract XML from PDF - file may not be a valid PDF/A-3 with embedded XML")
            return result

        result.extracted_xml = xml_content
        result.xml_size = len(xml_content.encode("utf-8"))
        result.add_info(f"Successfully extracted XML ({result.xml_size} bytes)")

        # Validate XML schema
        result.add_info("Validating XML schema...")
        schema_valid, schema_errors = self.validate_xml_schema(xml_content)

        if schema_valid:
            result.add_info("✅ XML schema validation passed")
        else:
            for error in schema_errors:
                result.add_error(f"Schema validation: {error}")

        # Validate business rules
        result.add_info("Validating business rules...")
        rules_valid, rule_errors, rule_warnings = self.validate_business_rules(xml_content)

        for error in rule_errors:
            result.add_error(f"Business rule: {error}")

        for warning in rule_warnings:
            result.add_warning(f"Business rule: {warning}")

        if rules_valid:
            result.add_info("✅ Business rule validation passed")

        return result

    def validate_xml_file(self, xml_path: str) -> InvoiceValidationResult:
        """
        Validate a standalone XML invoice file.

        Args:
            xml_path (str): Path to the XML file

        Returns:
            InvoiceValidationResult: Comprehensive validation results
        """
        result = InvoiceValidationResult()
        result.validation_type = "Standalone XML Invoice"
        result.file_path = xml_path

        # Check if file exists
        if not os.path.exists(xml_path):
            result.add_error(f"XML file not found: {xml_path}")
            return result

        # Read XML content
        try:
            with open(xml_path, encoding="utf-8") as f:
                xml_content = f.read()
        except Exception as e:
            result.add_error(f"Could not read XML file: {e}")
            return result

        result.extracted_xml = xml_content
        result.xml_size = len(xml_content.encode("utf-8"))
        result.add_info(f"XML file size: {result.xml_size / 1024:.1f} KB")

        # Validate XML schema
        result.add_info("Validating XML schema...")
        schema_valid, schema_errors = self.validate_xml_schema(xml_content)

        if schema_valid:
            result.add_info("✅ XML schema validation passed")
        else:
            for error in schema_errors:
                result.add_error(f"Schema validation: {error}")

        # Validate business rules
        result.add_info("Validating business rules...")
        rules_valid, rule_errors, rule_warnings = self.validate_business_rules(xml_content)

        for error in rule_errors:
            result.add_error(f"Business rule: {error}")

        for warning in rule_warnings:
            result.add_warning(f"Business rule: {warning}")

        if rules_valid:
            result.add_info("✅ Business rule validation passed")

        return result

    def validate_invoice_directory(self, directory_path: str) -> dict[str, InvoiceValidationResult]:
        """
        Validate all invoice files in a directory.

        Args:
            directory_path (str): Path to directory containing invoice files

        Returns:
            dict: Mapping of filename to validation results
        """
        results = {}
        directory = Path(directory_path)

        if not directory.exists():
            print(f"Directory not found: {directory_path}")
            return results

        # Find PDF and XML files
        pdf_files = list(directory.glob("*.pdf"))
        xml_files = list(directory.glob("*.xml"))

        print(f"Found {len(pdf_files)} PDF files and {len(xml_files)} XML files")

        # Validate PDF files
        for pdf_file in pdf_files:
            print(f"\nValidating PDF: {pdf_file.name}")
            results[pdf_file.name] = self.validate_pdf_file(str(pdf_file))

        # Validate XML files (that don't have corresponding PDFs)
        for xml_file in xml_files:
            # Skip XML files that are extracted from PDFs
            if "_extracted.xml" in xml_file.name:
                continue

            # Check if there's a corresponding PDF
            pdf_equivalent = xml_file.with_suffix(".pdf")
            if pdf_equivalent not in pdf_files:
                print(f"\nValidating standalone XML: {xml_file.name}")
                results[xml_file.name] = self.validate_xml_file(str(xml_file))

        return results


def main():
    """Main validation function with command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive ZUGFeRD/Factur-X Invoice Validator")
    parser.add_argument("--pdf", help="Validate a specific PDF file")
    parser.add_argument("--xml", help="Validate a specific XML file")
    parser.add_argument("--directory", help="Validate all invoices in a directory")
    parser.add_argument("--latest", action="store_true", help="Validate the latest generated invoice")

    args = parser.parse_args()

    validator = ComprehensiveInvoiceValidator()

    if args.pdf:
        result = validator.validate_pdf_file(args.pdf)
        result.print_summary()

    elif args.xml:
        result = validator.validate_xml_file(args.xml)
        result.print_summary()

    elif args.directory:
        results = validator.validate_invoice_directory(args.directory)

        print(f"\n{'=' * 80}")
        print("BATCH VALIDATION SUMMARY")
        print(f"{'=' * 80}")

        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.is_valid)

        print(f"Total files validated: {total_files}")
        print(f"Valid files: {valid_files}")
        print(f"Invalid files: {total_files - valid_files}")

        for filename, result in results.items():
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            errors = f" ({len(result.errors)} errors)" if result.errors else ""
            warnings = f" ({len(result.warnings)} warnings)" if result.warnings else ""
            print(f"  {filename}: {status}{errors}{warnings}")

    elif args.latest:
        # Find and validate the latest generated invoice
        from django.conf import settings

        pdf_dir = Path(settings.PDF_OUTPUT_DIR)
        pdf_files = list(pdf_dir.glob("invoice_DEMO-*.pdf"))

        if pdf_files:
            latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
            result = validator.validate_pdf_file(str(latest_pdf))
            result.print_summary()
        else:
            print("No generated invoices found. Run generate_real_invoice.py first.")

    else:
        print("Please specify --pdf, --xml, --directory, or --latest")
        print("Use --help for more information")


if __name__ == "__main__":
    main()
