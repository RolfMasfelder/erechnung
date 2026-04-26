"""
Invoice validation utilities for incoming ZUGFeRD/Factur-X invoices.

This module provides validation functionality for incoming supplier invoices
to ensure compliance with ZUGFeRD/Factur-X standards.
"""

import os
import sys
from pathlib import Path


class InvoiceValidator:
    """
    Validator for incoming ZUGFeRD/Factur-X invoices.

    This utility validates PDF/A-3 invoices with embedded XML against
    ZUGFeRD/Factur-X standards and provides detailed validation reports.
    """

    def __init__(self):
        """Initialize the validator with comprehensive validator."""
        self._setup_validator()

    def _setup_validator(self):
        """Setup the comprehensive validator."""
        try:
            # Import the comprehensive validator from the project root
            sys.path.append(os.getcwd())
            from comprehensive_invoice_validator import ComprehensiveInvoiceValidator

            self.validator = ComprehensiveInvoiceValidator()
        except ImportError as e:
            raise ImportError(f"Could not import ComprehensiveInvoiceValidator: {e}") from e

    def validate_invoice_file(self, file_path: str) -> "ValidationResult":
        """
        Validate a single invoice file.

        Args:
            file_path (str): Path to the invoice file

        Returns:
            ValidationResult: Validation result with status and details
        """
        if not os.path.exists(file_path):
            return ValidationResult(
                is_valid=False, errors=[f"File not found: {file_path}"], warnings=[], extracted_xml=None
            )

        # Use the comprehensive validator
        result = self.validator.validate_pdf_file(file_path)

        # Extract embedded attachments (non-XML files) from PDF/A-3
        extracted_attachments = self._extract_embedded_attachments(file_path)

        return ValidationResult(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
            extracted_xml=result.extracted_xml,
            extracted_attachments=extracted_attachments,
        )

    def _extract_embedded_attachments(self, file_path: str) -> list[dict]:
        """
        Extract non-XML embedded files from a PDF/A-3 using pikepdf.

        Returns a list of dicts, each with:
          - filename (str)
          - content (bytes)
          - mime_type (str)
          - af_relationship (str): e.g. '/Data', '/Supplement', '/Source', or ''
        """
        try:
            import pikepdf
        except ImportError:
            return []

        attachments = []
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx"}

        try:
            with pikepdf.open(file_path) as pdf:
                root = pdf.Root
                if "/Names" not in root:
                    return []
                names = root["/Names"]
                if "/EmbeddedFiles" not in names:
                    return []
                embedded = names["/EmbeddedFiles"]
                if "/Names" not in embedded:
                    return []

                names_array = list(embedded["/Names"])

                for i in range(0, len(names_array), 2):
                    if i + 1 >= len(names_array):
                        break
                    filename = str(names_array[i])
                    filespec = names_array[i + 1]

                    # Skip XML files (already handled by extracted_xml)
                    if filename.lower().endswith(".xml"):
                        continue

                    # Only extract allowed file types
                    ext = os.path.splitext(filename.lower())[1]
                    if ext not in allowed_extensions:
                        continue

                    # Get AFRelationship
                    af_rel = ""
                    if "/AFRelationship" in filespec:
                        af_rel = str(filespec["/AFRelationship"])

                    # Get file content
                    try:
                        if "/EF" in filespec and "/F" in filespec["/EF"]:
                            stream = filespec["/EF"]["/F"]
                            content = bytes(stream.read_bytes())
                        else:
                            continue
                    except Exception:
                        continue

                    # Detect MIME type from extension
                    mime_map = {
                        ".pdf": "application/pdf",
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".csv": "text/csv",
                        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    }
                    mime_type = mime_map.get(ext, "application/octet-stream")

                    attachments.append(
                        {
                            "filename": filename,
                            "content": content,
                            "mime_type": mime_type,
                            "af_relationship": af_rel,
                        }
                    )
        except Exception:
            # If PDF cannot be read for attachments, don't fail the whole validation
            pass

        return attachments

    def validate_xml_content(self, xml_content: str) -> "ValidationResult":
        """
        Validate XML content directly.

        Args:
            xml_content (str): ZUGFeRD/Factur-X XML content

        Returns:
            ValidationResult: Validation result
        """
        if not xml_content.strip():
            return ValidationResult(is_valid=False, errors=["Empty XML content"], warnings=[], extracted_xml=None)

        # Use the comprehensive validator's XML validation
        result = self.validator.validate_xml_content(xml_content)

        return ValidationResult(
            is_valid=result.is_valid, errors=result.errors, warnings=result.warnings, extracted_xml=xml_content
        )

    def check_duplicate_invoice(self, invoice_number: str, total_amount: float) -> bool:
        """
        Check if an invoice already exists in the database.

        Args:
            invoice_number (str): Invoice number to check
            total_amount (float): Total amount to check

        Returns:
            bool: True if duplicate found, False otherwise
        """
        try:
            # Import Django models after setup
            from invoice_app.models import Invoice

            existing = Invoice.objects.filter(invoice_number=invoice_number, total_amount=total_amount).exists()

            return existing

        except Exception:
            # If there's an error checking the database, assume no duplicate
            return False


class ValidationResult:
    """
    Container for validation results.
    """

    def __init__(
        self,
        is_valid: bool,
        errors: list,
        warnings: list,
        extracted_xml: str = None,
        extracted_attachments: list = None,
    ):
        """
        Initialize validation result.

        Args:
            is_valid (bool): Whether the validation passed
            errors (list): List of error messages
            warnings (list): List of warning messages
            extracted_xml (str): Extracted XML content if available
            extracted_attachments (list): List of dicts with extracted embedded files.
                Each dict: {filename, content (bytes), mime_type, af_relationship}
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.extracted_xml = extracted_xml
        self.extracted_attachments = extracted_attachments or []

    def __str__(self) -> str:
        """String representation of validation result."""
        status = "VALID" if self.is_valid else "INVALID"
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        return f"ValidationResult(status={status}, errors={error_count}, warnings={warning_count})"

    def get_summary(self) -> str:
        """Get a human-readable summary of the validation result."""
        lines = []

        if self.is_valid:
            lines.append("✅ VALIDATION PASSED")
        else:
            lines.append("❌ VALIDATION FAILED")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. {warning}")

        return "\n".join(lines)


class InvoiceFileManager:
    """
    Manager for organizing processed and rejected invoice files.
    """

    def __init__(self, base_directory: str = None):
        """
        Initialize file manager.

        Args:
            base_directory (str): Base directory for invoice processing
        """
        if base_directory:
            self.base_dir = Path(base_directory)
        else:
            # Default to project root/incoming_invoices
            self.base_dir = Path.cwd() / "incoming_invoices"

        self.base_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.processed_dir = self.base_dir / "processed"
        self.rejected_dir = self.base_dir / "rejected"

        self.processed_dir.mkdir(exist_ok=True)
        self.rejected_dir.mkdir(exist_ok=True)

    def move_to_processed(self, file_path: str, invoice_id: int = None) -> Path:
        """
        Move a successfully processed invoice to the processed directory.

        Args:
            file_path (str): Original file path
            invoice_id (int): Database ID of the created invoice

        Returns:
            Path: New file path in processed directory
        """
        import shutil
        from datetime import datetime

        file_name = Path(file_path).name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if invoice_id:
            new_name = f"{timestamp}_id{invoice_id}_{file_name}"
        else:
            new_name = f"{timestamp}_{file_name}"

        new_path = self.processed_dir / new_name
        shutil.copy2(file_path, new_path)

        return new_path

    def move_to_rejected(self, file_path: str, validation_result: ValidationResult) -> tuple[Path, Path]:
        """
        Move a rejected invoice to the rejected directory with report.

        Args:
            file_path (str): Original file path
            validation_result (ValidationResult): Validation result

        Returns:
            tuple[Path, Path]: (file_path, report_path) in rejected directory
        """
        import shutil
        from datetime import datetime

        file_name = Path(file_path).name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Copy file
        rejected_file = self.rejected_dir / f"{timestamp}_{file_name}"
        shutil.copy2(file_path, rejected_file)

        # Create rejection report
        report_path = rejected_file.with_suffix(".txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("INVOICE REJECTION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"File: {file_name}\n")
            f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Status: REJECTED\n\n")
            f.write(validation_result.get_summary())

        return rejected_file, report_path

    def create_processing_report(self, file_path: str, invoice_id: int, invoice_data: dict) -> Path:
        """
        Create a processing report for a successfully processed invoice.

        Args:
            file_path (str): Processed file path
            invoice_id (int): Database ID of the created invoice
            invoice_data (dict): Extracted invoice data

        Returns:
            Path: Path to the created report
        """
        from datetime import datetime

        report_path = Path(file_path).with_suffix(".txt")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("INVOICE PROCESSING REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"File: {Path(file_path).name}\n")
            f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Status: PROCESSED\n")
            f.write(f"Database ID: {invoice_id}\n")
            f.write(f"Invoice Number: {invoice_data.get('invoice_number', 'N/A')}\n")
            f.write(f"Supplier: {invoice_data.get('seller_name', 'N/A')}\n")
            f.write(f"Amount: {invoice_data.get('total_amount', 0)} {invoice_data.get('currency', 'EUR')}\n")
            f.write(f"Date: {invoice_data.get('issue_date', 'N/A')}\n")

        return report_path
