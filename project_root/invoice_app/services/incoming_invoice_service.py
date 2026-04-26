"""
Incoming Invoice Service for processing supplier invoices.

This service orchestrates the complete workflow for processing incoming
ZUGFeRD/Factur-X invoices from suppliers, including validation, data extraction,
and database storage.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Django imports are done after setup
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction

from invoice_app.utils.incoming_xml import IncomingXmlParser, SupplierDataExtractor
from invoice_app.utils.validation import InvoiceFileManager, InvoiceValidator, ValidationResult


if TYPE_CHECKING:
    from invoice_app.models import BusinessPartner, Company

# Constants
PLACEHOLDER_TEXT = "[To be updated]"
DEFAULT_POSTAL_CODE = "00000"
DEFAULT_COUNTRY = "DE"


class IncomingInvoiceService:
    """
    Service for processing incoming supplier invoices.

    This service orchestrates the complete workflow:
    1. Validation of PDF/A-3 with embedded XML
    2. XML data extraction and parsing
    3. Supplier company creation/lookup
    4. Invoice record creation
    5. File management (processed/rejected)
    """

    def __init__(self, base_directory: str = None):
        """
        Initialize the incoming invoice service.

        Args:
            base_directory (str): Base directory for file management
        """
        self.xml_parser = IncomingXmlParser()
        self.supplier_extractor = SupplierDataExtractor()
        self.validator = InvoiceValidator()
        self.file_manager = InvoiceFileManager(base_directory)

        # Load Django models
        self._load_models()

    def _load_models(self):
        """Load Django models."""
        from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceAttachment

        self.Company = Company
        self.Country = Country
        self.BusinessPartner = BusinessPartner
        self.Invoice = Invoice
        self.InvoiceAttachment = InvoiceAttachment
        self.User = get_user_model()

    def process_single_invoice(self, file_path: str) -> ProcessingResult:
        """
        Process a single incoming invoice file.

        Args:
            file_path (str): Path to the invoice file

        Returns:
            ProcessingResult: Result of the processing operation
        """
        print(f"\n{'=' * 60}")
        print(f"PROCESSING INCOMING INVOICE: {Path(file_path).name}")
        print(f"{'=' * 60}")

        # Step 1: Validate the invoice
        validation_result = self.validator.validate_invoice_file(file_path)

        if not validation_result.is_valid:
            # Move to rejected folder
            rejected_file, report_path = self.file_manager.move_to_rejected(file_path, validation_result)

            return ProcessingResult(
                success=False,
                message=f"Invoice rejected due to validation errors. See: {report_path}",
                invoice_id=None,
                validation_result=validation_result,
            )

        # Step 2: Extract invoice data
        if not validation_result.extracted_xml:
            return ProcessingResult(
                success=False,
                message="No XML content extracted from PDF",
                invoice_id=None,
                validation_result=validation_result,
            )

        try:
            invoice_data = self.xml_parser.extract_invoice_data(validation_result.extracted_xml)
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Failed to extract invoice data from XML: {e}",
                invoice_id=None,
                validation_result=validation_result,
            )

        if not invoice_data:
            return ProcessingResult(
                success=False,
                message="No invoice data could be extracted from XML",
                invoice_id=None,
                validation_result=validation_result,
            )

        # Log extracted data
        print("Extracted invoice data:")
        print(f"  Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
        print(f"  Issue Date: {invoice_data.get('issue_date', 'N/A')}")
        print(f"  Supplier: {invoice_data.get('seller_name', 'N/A')}")
        print(f"  Total Amount: {invoice_data.get('total_amount', 0):.2f} {invoice_data.get('currency', 'EUR')}")
        print(f"  Line Items: {len(invoice_data.get('line_items', []))}")

        # Step 3: Check for duplicates
        is_duplicate = self.validator.check_duplicate_invoice(
            invoice_data.get("invoice_number", ""), invoice_data.get("total_amount", 0)
        )

        if is_duplicate:
            return ProcessingResult(
                success=False,
                message=f"Duplicate invoice detected: {invoice_data.get('invoice_number', '')}",
                invoice_id=None,
                validation_result=validation_result,
            )

        # Step 4: Create invoice record
        try:
            with transaction.atomic():
                invoice_id = self._create_invoice_record(invoice_data, file_path)
                # Step 4b: Create attachment records from embedded PDF files
                self._create_attachment_records(invoice_id, validation_result.extracted_attachments, invoice_data)

            # Step 5: Move to processed folder
            processed_file = self.file_manager.move_to_processed(file_path, invoice_id)

            # Create processing report
            self.file_manager.create_processing_report(processed_file, invoice_id, invoice_data)

            print(f"✅ Created invoice record: ID {invoice_id}")

            return ProcessingResult(
                success=True,
                message=f"Invoice successfully processed and saved with ID {invoice_id}",
                invoice_id=invoice_id,
                validation_result=validation_result,
                invoice_data=invoice_data,
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Failed to create invoice record: {e}",
                invoice_id=None,
                validation_result=validation_result,
            )

    def _create_invoice_record(self, invoice_data: dict, file_path: str) -> int:
        """
        Create the invoice record in the database.

        Args:
            invoice_data (dict): Extracted invoice data
            file_path (str): Original file path

        Returns:
            int: Created invoice ID
        """
        # Find or create supplier
        supplier = self._find_or_create_supplier(invoice_data)

        if not supplier:
            raise ValueError("Failed to find or create supplier company")

        # Find or create our company record as business partner
        our_company = self._find_or_create_our_company(invoice_data)

        # Get system user
        system_user = self._get_system_user()

        # Create invoice record
        invoice = self.Invoice.objects.create(
            invoice_number=invoice_data.get("invoice_number", ""),
            invoice_type=self.Invoice.InvoiceType.INVOICE,
            company=supplier,  # Supplier is the issuing company
            business_partner=our_company,  # We are the business partner
            issue_date=invoice_data.get("issue_date", datetime.now().date()),
            currency=invoice_data.get("currency", "EUR"),
            total_amount=invoice_data.get("total_amount", 0),
            tax_amount=invoice_data.get("tax_amount", 0),
            subtotal=invoice_data.get("total_amount", 0) - invoice_data.get("tax_amount", 0),
            status=self.Invoice.InvoiceStatus.SENT,  # Mark as sent (received from supplier)
            created_by=system_user,
            notes=f"INCOMING INVOICE - Automatically processed from PDF/A-3 file: {Path(file_path).name}",
        )

        return invoice.id

    def _create_attachment_records(self, invoice_id: int, extracted_attachments: list, invoice_data: dict) -> list:
        """
        Create InvoiceAttachment records from embedded PDF/A-3 supplement files
        and enrich with XML AdditionalReferencedDocument metadata.

        Also detects XML AdditionalReferencedDocument entries that reference
        files not found as PDF embeddings, and appends warnings to invoice notes.

        Args:
            invoice_id (int): ID of the created invoice
            extracted_attachments (list): Embedded files from PDF extraction
            invoice_data (dict): Parsed invoice data with additional_referenced_documents

        Returns:
            list: Created InvoiceAttachment IDs
        """
        invoice = self.Invoice.objects.get(id=invoice_id)

        # Build lookup of XML AdditionalReferencedDocument by filename
        xml_refs = {}
        for ref in invoice_data.get("additional_referenced_documents", []):
            if ref.get("filename"):
                xml_refs[ref["filename"]] = ref

        # Track which XML refs are matched by embedded files
        embedded_filenames = {att.get("filename", "") for att in (extracted_attachments or [])}

        created_ids = []
        for att in extracted_attachments or []:
            filename = att.get("filename", "unknown")
            content = att.get("content", b"")
            mime_type = att.get("mime_type", "application/octet-stream")
            af_rel = att.get("af_relationship", "")

            # Determine attachment_type from AFRelationship and XML metadata
            attachment_type = self._determine_attachment_type(filename, af_rel, xml_refs.get(filename))

            # Build description from XML metadata if available
            xml_ref = xml_refs.get(filename, {})
            description = (
                xml_ref.get("description")
                or xml_ref.get("issuer_assigned_id")
                or f"Extracted from incoming PDF: {filename}"
            )

            try:
                attachment = self.InvoiceAttachment(
                    invoice=invoice,
                    original_filename=filename,
                    description=description[:255],
                    attachment_type=attachment_type,
                    mime_type=mime_type,
                )
                attachment.file.save(filename, ContentFile(content), save=True)
                created_ids.append(attachment.id)
                print(f"  📎 Extracted attachment: {filename} ({mime_type}, {af_rel})")
            except Exception as e:
                print(f"  ⚠️ Failed to save attachment {filename}: {e}")

        # Detect unmatched XML references (referenced in XML but not embedded in PDF)
        missing_warnings = []
        for ref in invoice_data.get("additional_referenced_documents", []):
            ref_filename = ref.get("filename", "")
            ref_uri = ref.get("external_uri", "")

            # Skip refs that matched an embedded file
            if ref_filename and ref_filename in embedded_filenames:
                continue

            # Skip refs that are purely external URI without filename expectation
            if not ref_filename and ref_uri:
                continue

            # This ref has a filename but no matching embedded file
            ref_id = ref.get("issuer_assigned_id", "")
            ref_desc = ref.get("description", "")
            label = ref_desc or ref_id or ref_filename
            if ref_uri:
                warning = f"⚠️ Referenziertes Dokument nicht im PDF eingebettet: {label} (extern: {ref_uri})"
            else:
                warning = f"⚠️ Referenziertes Dokument nicht im PDF eingebettet: {label}"
            missing_warnings.append(warning)
            print(f"  {warning}")

        # Append warnings to invoice notes so they are visible in the UI
        # Use queryset.update() to bypass GoBD save-lock (this is part of initial import)
        if missing_warnings:
            notes_addition = "\n".join(missing_warnings)
            current_notes = invoice.notes or ""
            new_notes = f"{current_notes}\n{notes_addition}" if current_notes else notes_addition
            self.Invoice.objects.filter(id=invoice_id).update(notes=new_notes)

        return created_ids

    def _determine_attachment_type(self, filename: str, af_relationship: str, xml_ref: dict | None) -> str:
        """
        Determine the InvoiceAttachment type from context.

        Uses XML TypeCode, AFRelationship, and filename heuristics.
        """
        from invoice_app.models.invoice_models import AttachmentType

        # Check XML TypeCode first (most authoritative)
        if xml_ref:
            type_code = xml_ref.get("type_code", "")
            # TypeCode 916 = Rechnungsbegründendes Dokument / Supporting document
            if type_code == "916":
                return AttachmentType.SUPPORTING_DOCUMENT
            # TypeCode 130 = Proforma invoice
            # TypeCode 50 = Delivery note
            if type_code in ("50", "270"):
                return AttachmentType.DELIVERY_NOTE

        # Filename heuristics
        lower_name = filename.lower()
        if any(kw in lower_name for kw in ("lieferschein", "delivery", "liefern")):
            return AttachmentType.DELIVERY_NOTE
        if any(kw in lower_name for kw in ("zeitaufstellung", "timesheet", "stunden")):
            return AttachmentType.TIMESHEET

        return AttachmentType.SUPPORTING_DOCUMENT

    def _find_or_create_supplier(self, invoice_data: dict) -> Company | None:
        """
        Find existing supplier or create a new one.

        Args:
            invoice_data (dict): Extracted invoice data

        Returns:
            Company: Supplier company object
        """
        seller_name = invoice_data.get("seller_name", "")
        seller_id = invoice_data.get("seller_id", "")

        if not seller_name:
            return None

        try:
            # Try to find existing supplier by tax ID (if seller_id looks like a tax ID)
            if seller_id and (seller_id.startswith("DE") or len(seller_id) > 8):
                try:
                    return self.Company.objects.get(tax_id=seller_id)
                except self.Company.DoesNotExist:
                    pass

            # Try by name (primary matching method)
            try:
                return self.Company.objects.get(name=seller_name)
            except self.Company.DoesNotExist:
                pass

            # Create new supplier with extracted supplier data
            try:
                # Extract comprehensive supplier info from XML

                # We need the XML content for supplier extraction
                # This is a simplified version - in practice you'd pass the full XML
                # Get or create Germany country for ForeignKey
                germany = self.Country.objects.get_or_create(
                    code="DE",
                    defaults={
                        "code_alpha3": "DEU",
                        "numeric_code": "276",
                        "name": "Germany",
                        "name_local": "Deutschland",
                        "currency_code": "EUR",
                        "currency_name": "Euro",
                        "currency_symbol": "€",
                        "default_language": "de",
                        "is_eu_member": True,
                        "is_eurozone": True,
                        "standard_vat_rate": 19.00,
                    },
                )[0]

                supplier_data = {
                    "name": seller_name,
                    "tax_id": seller_id if seller_id and (seller_id.startswith("DE") or len(seller_id) > 8) else "",
                    "address_line1": "[To be updated]",
                    "city": "[To be updated]",
                    "postal_code": "00000",
                    "country": germany,
                }

                supplier = self.Company.objects.create(**supplier_data)
                print(f"Created new supplier: {seller_name}")
                return supplier

            except Exception as e:
                print(f"Error creating supplier: {e}")
                return None

        except Exception as e:
            print(f"Error finding/creating supplier: {e}")
            return None

    def _find_or_create_our_company(self, invoice_data: dict) -> BusinessPartner:
        """
        Find or create our company record as a business partner.

        Args:
            invoice_data (dict): Extracted invoice data

        Returns:
            BusinessPartner: Our company as business partner object
        """
        buyer_name = invoice_data.get("buyer_name", "Our Company")

        # Get or create Germany country for ForeignKey
        germany = self.Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "numeric_code": "276",
                "name": "Germany",
                "name_local": "Deutschland",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

        our_company, _ = self.BusinessPartner.objects.get_or_create(
            company_name=buyer_name,  # Use company_name, not name
            defaults={
                "address_line1": "[To be updated]",  # Use address_line1
                "city": "[To be updated]",
                "postal_code": "00000",
                "country": germany,
                "email": "",
                "tax_id": "",
            },
        )

        return our_company

    def _get_system_user(self):
        """
        Get or create a system user for automatic invoice processing.

        Returns:
            User: System user for created_by field
        """
        try:
            # Try to find existing system user
            system_user = self.User.objects.filter(username="incoming_invoice_processor").first()

            if not system_user:
                # Try to find any staff user
                system_user = self.User.objects.filter(is_staff=True).first()

            if not system_user:
                # Create system user
                system_user = self.User.objects.create_user(
                    username="incoming_invoice_processor",
                    email="system@company.com",
                    first_name="System",
                    last_name="Processor",
                    is_staff=True,
                )

            return system_user

        except Exception as e:
            print(f"Warning: Could not create/find system user: {e}")
            return None

    def process_batch(self, directory_path: str) -> BatchProcessingResult:
        """
        Process all PDF invoices in a directory.

        Args:
            directory_path (str): Path to directory containing invoice files

        Returns:
            BatchProcessingResult: Results summary
        """
        directory = Path(directory_path)

        if not directory.exists():
            return BatchProcessingResult(
                total_files=0,
                processed=0,
                rejected=0,
                errors=0,
                details=[],
                error_message=f"Directory not found: {directory_path}",
            )

        pdf_files = list(directory.glob("*.pdf"))

        if not pdf_files:
            return BatchProcessingResult(
                total_files=0,
                processed=0,
                rejected=0,
                errors=0,
                details=[],
                error_message="No PDF files found in directory",
            )

        print(f"\n{'=' * 80}")
        print(f"BATCH PROCESSING: {len(pdf_files)} files in {directory_path}")
        print(f"{'=' * 80}")

        results = BatchProcessingResult(total_files=len(pdf_files), processed=0, rejected=0, errors=0, details=[])

        for pdf_file in pdf_files:
            try:
                result = self.process_single_invoice(str(pdf_file))

                if result.success:
                    results.processed += 1
                    status = "✅ PROCESSED"
                else:
                    results.rejected += 1
                    status = "❌ REJECTED"

                results.details.append(
                    {
                        "file": pdf_file.name,
                        "status": status,
                        "message": result.message,
                        "invoice_id": result.invoice_id,
                    }
                )

                print(f"{status}: {pdf_file.name}")

            except Exception as e:
                results.errors += 1
                error_msg = f"Processing error: {e}"
                results.details.append(
                    {"file": pdf_file.name, "status": "❌ ERROR", "message": error_msg, "invoice_id": None}
                )
                print(f"❌ ERROR: {pdf_file.name} - {error_msg}")

        return results


class ProcessingResult:
    """Result of processing a single invoice."""

    def __init__(
        self,
        success: bool,
        message: str,
        invoice_id: int | None = None,
        validation_result: ValidationResult | None = None,
        invoice_data: dict | None = None,
    ):
        self.success = success
        self.message = message
        self.invoice_id = invoice_id
        self.validation_result = validation_result
        self.invoice_data = invoice_data


class BatchProcessingResult:
    """Result of batch processing multiple invoices."""

    def __init__(
        self, total_files: int, processed: int, rejected: int, errors: int, details: list, error_message: str = None
    ):
        self.total_files = total_files
        self.processed = processed
        self.rejected = rejected
        self.errors = errors
        self.details = details
        self.error_message = error_message

    def get_summary(self) -> str:
        """Get a summary of batch processing results."""
        if self.error_message:
            return f"❌ {self.error_message}"

        lines = [
            "BATCH PROCESSING SUMMARY",
            "=" * 80,
            f"Total files: {self.total_files}",
            f"Processed: {self.processed}",
            f"Rejected: {self.rejected}",
            f"Errors: {self.errors}",
        ]

        return "\n".join(lines)
