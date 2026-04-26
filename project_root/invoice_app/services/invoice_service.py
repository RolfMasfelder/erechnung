"""
Service for generating and handling electronic invoices.
This module combines XML generation and PDF/A-3 creation.
"""

import logging  # noqa: I001
import os

import pikepdf
from django.conf import settings
from invoice_app.utils.pdf import PdfA3Generator
from invoice_app.utils.xml import ZugferdXmlGenerator, ZugferdXmlValidator

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for handling electronic invoices."""

    def __init__(self):
        """Initialize the invoice service."""
        self.xml_generator = ZugferdXmlGenerator()
        self.xml_validator = ZugferdXmlValidator()
        self.pdf_generator = PdfA3Generator()

    def convert_model_to_dict(self, invoice):
        """
        Convert a Django Invoice model to a dictionary format suitable for XML generation.

        Args:
            invoice (Invoice): The Invoice model instance

        Returns:
            dict: Dictionary with invoice data
        """
        # Get invoice lines
        lines = invoice.lines.all().select_related("invoice")

        # Create items list
        items = []
        for line in lines:
            items.append(
                {
                    "product_name": line.description,
                    "quantity": float(line.quantity),
                    "price": float(line.unit_price),
                    "tax_rate": float(line.tax_rate),
                    "tax_category_code": line.tax_category_code,
                    "tax_exemption_reason": line.tax_exemption_reason or "",
                    "product_code": line.product_code,
                    "unit_of_measure": line.unit_of_measure,
                    "line_total": float(line.line_total),
                    "discount_amount": float(line.discount_amount) if line.discount_amount else 0.0,
                    "discount_reason": line.discount_reason or "",
                }
            )

        # Header-level allowances and charges (EN16931)
        allowances_charges = []
        allowance_total = 0.0
        charge_total = 0.0
        for ac in invoice.allowance_charges.all().order_by("sort_order"):
            allowances_charges.append(
                {
                    "is_charge": ac.is_charge,
                    "actual_amount": float(ac.actual_amount),
                    "calculation_percent": (
                        float(ac.calculation_percent) if ac.calculation_percent is not None else None
                    ),
                    "basis_amount": float(ac.basis_amount) if ac.basis_amount is not None else None,
                    "reason_code": ac.reason_code or "",
                    "reason": ac.reason or "",
                }
            )
            if ac.is_charge:
                charge_total += float(ac.actual_amount)
            else:
                allowance_total += float(ac.actual_amount)

        # UNTDID 1001 TypeCode mapping (EN 16931 / ZUGFeRD)
        type_code_map = {
            "INVOICE": "380",
            "CREDIT_NOTE": "381",
            "DEBIT_NOTE": "384",
            "CORRECTED": "384",
            "PARTIAL": "326",
            "FINAL": "380",
        }

        # Build the invoice data dictionary with complete address data for ZUGFeRD XML
        invoice_data = {
            "number": invoice.invoice_number,
            "type_code": type_code_map.get(invoice.invoice_type, "380"),
            "date": invoice.issue_date.strftime("%Y%m%d"),
            "due_date": invoice.due_date.strftime("%Y%m%d"),
            "delivery_date": invoice.delivery_date.strftime("%Y%m%d") if invoice.delivery_date else None,
            # Business references (B2B)
            "buyer_reference": invoice.buyer_reference or "",
            "seller_reference": invoice.seller_reference or "",
            "currency": invoice.currency,
            "subtotal": float(invoice.subtotal),
            "tax_amount": float(invoice.tax_amount),
            "total_amount": float(invoice.total_amount),
            # Company/Seller data with ZUGFeRD-compatible address fields
            "company": {
                "name": invoice.company.name,
                "legal_name": invoice.company.legal_name,
                "tax_id": invoice.company.tax_id,
                "vat_id": invoice.company.vat_id,
                "commercial_register": invoice.company.commercial_register,
                # Structured address fields for XML generation
                "street_name": invoice.company.street_name,  # Uses property
                "city_name": invoice.company.city_name,  # Uses property
                "postcode_code": invoice.company.postcode_code,  # Uses property
                "country_id": invoice.company.country_id,  # Uses property (ISO code)
                "email": invoice.company.email,
                # Bank details for SpecifiedTradeSettlementPaymentMeans
                "iban": invoice.company.iban,
                "bic": invoice.company.bic,
                "bank_name": invoice.company.bank_name,
            },
            # Backward compatibility: also provide as 'issuer'
            "issuer": {
                "name": invoice.company.name,
                "tax_id": invoice.company.tax_id,
                "vat_id": invoice.company.vat_id,
                "commercial_register": invoice.company.commercial_register,
                "street_name": invoice.company.street_name,
                "city_name": invoice.company.city_name,
                "postcode_code": invoice.company.postcode_code,
                "country_id": invoice.company.country_id,
                "email": invoice.company.email,
                "iban": invoice.company.iban,
                "bic": invoice.company.bic,
                "bank_name": invoice.company.bank_name,
            },
            # BusinessPartner/Buyer data with ZUGFeRD-compatible address fields
            "customer": {
                "name": invoice.business_partner.name,
                "tax_id": invoice.business_partner.tax_id,
                "vat_id": invoice.business_partner.vat_id,
                # Structured address fields for XML generation
                "street_name": invoice.business_partner.street_name,  # Uses property
                "city_name": invoice.business_partner.city_name,  # Uses property
                "postcode_code": invoice.business_partner.postcode_code,  # Uses property
                "country_id": invoice.business_partner.country_id,  # Uses property (ISO code)
                "email": invoice.business_partner.email,
            },
            "items": items,
            "allowances_charges": allowances_charges,
            "allowance_total": allowance_total,
            "charge_total": charge_total,
            "additional_documents": self._build_additional_documents(invoice),
        }

        # BT-25: InvoiceReferencedDocument for credit notes (reference to original invoice)
        if invoice.invoice_type == "CREDIT_NOTE":
            original = invoice.cancels_invoice
            if original:
                invoice_data["invoice_referenced_document"] = {
                    "issuer_assigned_id": original.invoice_number,
                    "issue_date": original.issue_date.strftime("%Y%m%d"),
                }

        return invoice_data

    @staticmethod
    def _build_additional_documents(invoice):
        """Build additional_documents list from invoice attachments for XML generation."""
        # Map AttachmentType to UNTDID 1001 TypeCode
        _type_code_map = {
            "supporting_document": "916",
            "delivery_note": "916",
            "timesheet": "916",
            "other": "916",
        }
        docs = []
        for att in invoice.attachments.all():
            docs.append(
                {
                    "filename": att.original_filename or att.file.name.split("/")[-1],
                    "description": att.description or att.original_filename or "",
                    "type_code": _type_code_map.get(att.attachment_type, "916"),
                }
            )
        return docs

    def generate_invoice_files(self, invoice, zugferd_profile="COMFORT"):
        """
        Generate PDF/A-3 with embedded ZUGFeRD/Factur-X XML for an invoice.

        Args:
            invoice (Invoice): The Invoice model instance
            zugferd_profile (str): ZUGFeRD profile to use (MINIMUM, BASICWL, BASIC, COMFORT, EXTENDED, or XRECHNUNG).
                                   Default is COMFORT (EN16931) – the recommended profile for B2B invoicing.
                                   Automatically switches to XRECHNUNG for GOVERNMENT partners.

        Returns:
            dict: Paths to the generated files
                {
                    'pdf_path': str,
                    'xml_path': str,
                    'is_valid': bool,
                    'validation_errors': list
                }
        """
        try:
            # Auto-select XRechnung profile for government partners
            partner = invoice.business_partner
            if partner and partner.partner_type == "GOVERNMENT" and zugferd_profile != "XRECHNUNG":
                logger.info(
                    f"Auto-selecting XRECHNUNG profile for government partner '{partner.name}' "
                    f"(invoice {invoice.invoice_number})"
                )
                zugferd_profile = "XRECHNUNG"

            # Convert Django model to dictionary
            invoice_data = self.convert_model_to_dict(invoice)

            # BT-10 is mandatory for XRechnung
            if zugferd_profile == "XRECHNUNG" and not invoice_data.get("buyer_reference"):
                raise ValueError(
                    f"BT-10 (buyer_reference) ist für XRechnung-Rechnungen Pflicht. "
                    f"Invoice {invoice.invoice_number} hat keine buyer_reference."
                )

            # Generate XML using the appropriate profile
            xml_generator = ZugferdXmlGenerator(profile=zugferd_profile)
            xml_content = xml_generator.generate_xml(invoice_data)

            # Validate the XML
            validation_result = self.xml_validator.validate_xml(xml_content)

            # Handle both ValidationResult object and legacy tuple format
            if isinstance(validation_result, tuple):
                # Legacy tuple format: (is_valid, errors)
                is_valid, errors = validation_result
                if not is_valid:
                    logger.warning(f"Generated XML for invoice {invoice.invoice_number} failed validation: {errors}")
                # Store for later use
                validation_is_valid = is_valid
                validation_errors = errors
            else:
                # Modern ValidationResult object
                if not validation_result.is_valid:
                    logger.warning(
                        f"Generated XML for invoice {invoice.invoice_number} failed validation: {validation_result.errors}"
                    )
                # Store for later use
                validation_is_valid = validation_result.is_valid
                validation_errors = validation_result.errors

            # Additional XRechnung-specific Schematron validation (BR-DE-* national rules)
            if zugferd_profile == "XRECHNUNG":
                xr_result = self._validate_xrechnung_schematron(xml_content)
                if xr_result is not None:
                    if not xr_result.is_valid:
                        validation_is_valid = False
                        validation_errors = list(validation_errors) + xr_result.errors
                        logger.warning(
                            f"XRechnung Schematron validation failed for {invoice.invoice_number}: {xr_result.errors}"
                        )

            # Generate PDF/A-3 with embedded XML (WeasyPrint uses invoice instance for template rendering)
            pdf_result = self.pdf_generator.generate_invoice_pdf(invoice_data, xml_content, invoice_instance=invoice)

            # Get the file paths relative to MEDIA_ROOT for storing in the model
            pdf_relative_path = os.path.relpath(pdf_result["pdf_path"], start=settings.MEDIA_ROOT)
            xml_relative_path = os.path.relpath(pdf_result["xml_path"], start=settings.MEDIA_ROOT)

            # Update the invoice model
            invoice.pdf_file = pdf_relative_path
            invoice.xml_file = xml_relative_path
            invoice.save()

            # Return result with full paths and validation info
            return {
                "pdf_path": pdf_result["pdf_path"],
                "xml_path": pdf_result["xml_path"],
                "is_valid": validation_is_valid,
                "validation_errors": validation_errors,
            }

        except (OSError, ValueError) as e:
            logger.error(f"Error generating invoice files: {str(e)}")
            raise

    def _validate_xrechnung_schematron(self, xml_content):
        """
        Run XRechnung-specific Schematron validation (BR-DE-* national rules).

        Returns None if the XRechnung schematron is not available.
        """
        from invoice_app.utils.xml.constants import XRECHNUNG_SCHEMATRON_XSLT_PATH

        if not XRECHNUNG_SCHEMATRON_XSLT_PATH.exists():
            logger.warning(f"XRechnung Schematron XSLT not found: {XRECHNUNG_SCHEMATRON_XSLT_PATH}")
            return None

        try:
            from invoice_app.utils.xml.backends import SchematronSaxonBackend

            backend = SchematronSaxonBackend(XRECHNUNG_SCHEMATRON_XSLT_PATH)
            return backend.validate(xml_content)
        except Exception as e:
            logger.warning(f"XRechnung Schematron validation failed to initialize: {e}")
            return None

    def generate_xml_only(self, invoice, zugferd_profile="XRECHNUNG"):
        """
        Generate standalone XML without PDF/A-3 embedding (for B2G XRechnung).

        Args:
            invoice (Invoice): The Invoice model instance
            zugferd_profile (str): Profile to use (default: XRECHNUNG)

        Returns:
            dict: {
                'xml_content': str,
                'xml_path': str,
                'is_valid': bool,
                'validation_errors': list
            }
        """
        # Auto-select XRechnung for GOVERNMENT partners
        partner = invoice.business_partner
        if partner and partner.partner_type == "GOVERNMENT" and zugferd_profile != "XRECHNUNG":
            zugferd_profile = "XRECHNUNG"

        invoice_data = self.convert_model_to_dict(invoice)

        # BT-10 mandatory for XRechnung
        if zugferd_profile == "XRECHNUNG" and not invoice_data.get("buyer_reference"):
            raise ValueError(
                f"BT-10 (buyer_reference) ist für XRechnung-Rechnungen Pflicht. "
                f"Invoice {invoice.invoice_number} hat keine buyer_reference."
            )

        xml_generator = ZugferdXmlGenerator(profile=zugferd_profile)
        xml_content = xml_generator.generate_xml(invoice_data)

        # Validate
        validation_result = self.xml_validator.validate_xml(xml_content)
        if isinstance(validation_result, tuple):
            validation_is_valid, validation_errors = validation_result
        else:
            validation_is_valid = validation_result.is_valid
            validation_errors = validation_result.errors

        # XRechnung-specific validation
        if zugferd_profile == "XRECHNUNG":
            xr_result = self._validate_xrechnung_schematron(xml_content)
            if xr_result is not None and not xr_result.is_valid:
                validation_is_valid = False
                validation_errors = list(validation_errors) + xr_result.errors

        # Save XML file
        xml_dir = os.path.join(settings.MEDIA_ROOT, "invoices", "xml")
        os.makedirs(xml_dir, exist_ok=True)
        xml_filename = f"xrechnung_{invoice.invoice_number}.xml"
        xml_path = os.path.join(xml_dir, xml_filename)

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # Update model
        xml_relative_path = os.path.relpath(xml_path, start=settings.MEDIA_ROOT)
        invoice.xml_file = xml_relative_path
        invoice.save()

        return {
            "xml_content": xml_content,
            "xml_path": xml_path,
            "is_valid": validation_is_valid,
            "validation_errors": validation_errors,
        }

    def extract_xml_from_pdf(self, pdf_path):
        """
        Extract XML from a PDF/A-3 file.

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: XML content as string or None if not found
        """
        try:
            # Use pikepdf to open the PDF
            with pikepdf.open(pdf_path) as pdf:
                # Check if the PDF has embedded files
                if "/EmbeddedFiles" not in pdf.Root:
                    return None

                # Get the names of embedded files
                embedded_files = pdf.Root.EmbeddedFiles.Names

                # Find the XML file
                xml_content = None
                i = 0
                while i < len(embedded_files):
                    if isinstance(embedded_files[i], str) and embedded_files[i].endswith(".xml"):
                        # Get the XML content
                        xml_file = embedded_files[i + 1]
                        xml_stream = xml_file.EF.F
                        xml_content = xml_stream.read().decode("utf-8")
                        break
                    i += 2

                return xml_content

        except (pikepdf.PdfError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
            logger.error(f"Error extracting XML from PDF: {str(e)}")
            return None
            return None
