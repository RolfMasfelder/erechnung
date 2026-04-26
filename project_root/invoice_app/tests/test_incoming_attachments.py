"""
Tests for Phase E: Extraction of embedded attachments from incoming PDF/A-3 invoices.

Tests cover:
1. ValidationResult with extracted_attachments
2. PDF embedded file extraction (InvoiceValidator._extract_embedded_attachments)
3. XML AdditionalReferencedDocument parsing
4. InvoiceAttachment record creation during import
"""

import os
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from invoice_app.services.incoming_invoice_service import IncomingInvoiceService
from invoice_app.utils.incoming_xml import IncomingXmlParser
from invoice_app.utils.validation import ValidationResult


User = get_user_model()


# ============================================================================
# 1. ValidationResult Tests
# ============================================================================


class ValidationResultAttachmentsTestCase(TestCase):
    """Test ValidationResult with extracted_attachments field."""

    def test_default_empty_attachments(self):
        """ValidationResult should default to empty attachments list."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], extracted_xml="<xml/>")
        self.assertEqual(result.extracted_attachments, [])

    def test_explicit_attachments(self):
        """ValidationResult should store extracted_attachments."""
        attachments = [
            {
                "filename": "lieferschein.pdf",
                "content": b"%PDF-1.4",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            },
        ]
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            extracted_xml="<xml/>",
            extracted_attachments=attachments,
        )
        self.assertEqual(len(result.extracted_attachments), 1)
        self.assertEqual(result.extracted_attachments[0]["filename"], "lieferschein.pdf")
        self.assertEqual(result.extracted_attachments[0]["af_relationship"], "/Supplement")

    def test_none_attachments_becomes_empty_list(self):
        """ValidationResult should convert None attachments to empty list."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            extracted_xml="<xml/>",
            extracted_attachments=None,
        )
        self.assertEqual(result.extracted_attachments, [])

    def test_backward_compatibility(self):
        """Existing code creating ValidationResult without attachments should still work."""
        result = ValidationResult(is_valid=False, errors=["test error"], warnings=["warn"])
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ["test error"])
        self.assertEqual(result.extracted_attachments, [])


# ============================================================================
# 2. PDF Embedded Attachment Extraction Tests
# ============================================================================


class PdfAttachmentExtractionTestCase(TestCase):
    """Test extraction of non-XML embedded files from PDF/A-3."""

    def _create_pdf_with_attachments(self, attachments_data):
        """
        Create a minimal PDF/A-3 with embedded files for testing.

        Args:
            attachments_data: list of (filename, content_bytes, af_relationship) tuples

        Returns:
            str: Path to the temporary PDF file
        """
        import pikepdf

        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(612, 792))

        names_array = []
        af_array = []

        for filename, content, af_rel in attachments_data:
            stream = pikepdf.Stream(pdf, content)
            stream.Type = pikepdf.Name("/EmbeddedFile")

            filespec = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/Filespec"),
                    "/F": filename,
                    "/UF": filename,
                    "/EF": pikepdf.Dictionary({"/F": stream}),
                    "/AFRelationship": pikepdf.Name(af_rel),
                }
            )

            names_array.extend([filename, pdf.make_indirect(filespec)])
            af_array.append(pdf.make_indirect(filespec))

        embedded_files = pikepdf.Dictionary({"/Names": pikepdf.Array(names_array)})
        pdf.Root["/Names"] = pikepdf.Dictionary({"/EmbeddedFiles": embedded_files})
        pdf.Root["/AF"] = pikepdf.Array(af_array)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf.save(tmp.name)
        pdf.close()
        return tmp.name

    def test_extract_no_attachments(self):
        """PDF without embedded files should yield empty list."""
        import pikepdf

        from invoice_app.utils.validation import InvoiceValidator

        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(612, 792))
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf.save(tmp.name)
        pdf.close()

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(tmp.name)
            self.assertEqual(result, [])
        finally:
            os.unlink(tmp.name)

    def test_extract_supplement_pdf(self):
        """Should extract PDF embedded as /Supplement."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_content = b"%PDF-1.4 fake supplement content"
        pdf_path = self._create_pdf_with_attachments(
            [
                ("lieferschein.pdf", pdf_content, "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["filename"], "lieferschein.pdf")
            self.assertEqual(result[0]["content"], pdf_content)
            self.assertEqual(result[0]["mime_type"], "application/pdf")
            self.assertEqual(result[0]["af_relationship"], "/Supplement")
        finally:
            os.unlink(pdf_path)

    def test_extract_multiple_attachments(self):
        """Should extract multiple embedded files of different types."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_path = self._create_pdf_with_attachments(
            [
                ("lieferschein.pdf", b"%PDF-supplement", "/Supplement"),
                ("zeitaufstellung.csv", b"date,hours\n2024-01-01,8", "/Supplement"),
                ("foto.png", b"\x89PNG\r\n\x1a\n fake png", "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            self.assertEqual(len(result), 3)

            filenames = [r["filename"] for r in result]
            self.assertIn("lieferschein.pdf", filenames)
            self.assertIn("zeitaufstellung.csv", filenames)
            self.assertIn("foto.png", filenames)

            mime_types = {r["filename"]: r["mime_type"] for r in result}
            self.assertEqual(mime_types["lieferschein.pdf"], "application/pdf")
            self.assertEqual(mime_types["zeitaufstellung.csv"], "text/csv")
            self.assertEqual(mime_types["foto.png"], "image/png")
        finally:
            os.unlink(pdf_path)

    def test_skip_xml_files(self):
        """XML files should be skipped (already handled via extracted_xml)."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_path = self._create_pdf_with_attachments(
            [
                ("factur-x.xml", b"<xml>invoice</xml>", "/Data"),
                ("lieferschein.pdf", b"%PDF-supplement", "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            # Should only have the PDF, not the XML
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["filename"], "lieferschein.pdf")
        finally:
            os.unlink(pdf_path)

    def test_skip_disallowed_extensions(self):
        """Files with disallowed extensions should be skipped."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_path = self._create_pdf_with_attachments(
            [
                ("script.exe", b"MZ dangerous", "/Supplement"),
                ("lieferschein.pdf", b"%PDF-safe", "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["filename"], "lieferschein.pdf")
        finally:
            os.unlink(pdf_path)

    def test_detect_af_relationship(self):
        """Should correctly detect AFRelationship per file."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_path = self._create_pdf_with_attachments(
            [
                ("data.pdf", b"%PDF-data", "/Data"),
                ("supplement.pdf", b"%PDF-supplement", "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            af_rels = {r["filename"]: r["af_relationship"] for r in result}
            self.assertEqual(af_rels["data.pdf"], "/Data")
            self.assertEqual(af_rels["supplement.pdf"], "/Supplement")
        finally:
            os.unlink(pdf_path)

    def test_xlsx_extraction(self):
        """Should extract XLSX files with correct MIME type."""
        from invoice_app.utils.validation import InvoiceValidator

        pdf_path = self._create_pdf_with_attachments(
            [
                ("aufstellung.xlsx", b"PK\x03\x04 fake xlsx", "/Supplement"),
            ]
        )

        try:
            validator = object.__new__(InvoiceValidator)
            result = validator._extract_embedded_attachments(pdf_path)
            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0]["mime_type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        finally:
            os.unlink(pdf_path)

    def test_nonexistent_file(self):
        """Should return empty list for nonexistent file."""
        from invoice_app.utils.validation import InvoiceValidator

        validator = object.__new__(InvoiceValidator)
        result = validator._extract_embedded_attachments("/does/not/exist.pdf")
        self.assertEqual(result, [])


# ============================================================================
# 3. XML AdditionalReferencedDocument Parsing Tests
# ============================================================================


class AdditionalReferencedDocumentTestCase(TestCase):
    """Test parsing of AdditionalReferencedDocument from CII XML."""

    def setUp(self):
        self.parser = IncomingXmlParser()

    def _build_xml(self, additional_docs_xml=""):
        """Build a minimal CII XML with optional AdditionalReferencedDocument entries."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <CrossIndustryInvoice xmlns="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                             xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                             xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
            <ExchangedDocumentContext/>
            <ExchangedDocument>
                <ID>INV-001</ID>
                <TypeCode>380</TypeCode>
                <IssueDateTime>
                    <udt:DateTimeString>20240101</udt:DateTimeString>
                </IssueDateTime>
            </ExchangedDocument>
            <SupplyChainTradeTransaction>
                <ApplicableHeaderTradeAgreement>
                    <SellerTradeParty>
                        <ram:Name>Supplier GmbH</ram:Name>
                    </SellerTradeParty>
                    <BuyerTradeParty>
                        <ram:Name>Our Company</ram:Name>
                    </BuyerTradeParty>
                    {additional_docs_xml}
                </ApplicableHeaderTradeAgreement>
                <ApplicableHeaderTradeSettlement>
                    <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
                    <SpecifiedTradeSettlementHeaderMonetarySummation>
                        <GrandTotalAmount>1000.00</GrandTotalAmount>
                        <TaxTotalAmount>190.00</TaxTotalAmount>
                    </SpecifiedTradeSettlementHeaderMonetarySummation>
                </ApplicableHeaderTradeSettlement>
            </SupplyChainTradeTransaction>
        </CrossIndustryInvoice>"""

    def test_no_additional_documents(self):
        """Should return empty list when no AdditionalReferencedDocument exists."""
        xml = self._build_xml()
        data = self.parser.extract_invoice_data(xml)
        self.assertEqual(data["additional_referenced_documents"], [])

    def test_single_document_with_all_fields(self):
        """Should parse a complete AdditionalReferencedDocument."""
        docs_xml = """
        <ram:AdditionalReferencedDocument>
            <ram:IssuerAssignedID>LS-2024-042</ram:IssuerAssignedID>
            <ram:TypeCode>916</ram:TypeCode>
            <ram:Name>Lieferschein vom 15.01.2024</ram:Name>
            <ram:AttachmentBinaryObject filename="lieferschein.pdf" mimeCode="application/pdf"/>
        </ram:AdditionalReferencedDocument>
        """
        xml = self._build_xml(docs_xml)
        data = self.parser.extract_invoice_data(xml)

        docs = data["additional_referenced_documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["issuer_assigned_id"], "LS-2024-042")
        self.assertEqual(docs[0]["type_code"], "916")
        self.assertEqual(docs[0]["description"], "Lieferschein vom 15.01.2024")
        self.assertEqual(docs[0]["filename"], "lieferschein.pdf")

    def test_document_with_uri(self):
        """Should parse URIID (external reference)."""
        docs_xml = """
        <ram:AdditionalReferencedDocument>
            <ram:IssuerAssignedID>EXT-001</ram:IssuerAssignedID>
            <ram:TypeCode>916</ram:TypeCode>
            <ram:URIID>https://example.com/doc/ext-001.pdf</ram:URIID>
        </ram:AdditionalReferencedDocument>
        """
        xml = self._build_xml(docs_xml)
        data = self.parser.extract_invoice_data(xml)

        docs = data["additional_referenced_documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["external_uri"], "https://example.com/doc/ext-001.pdf")
        self.assertEqual(docs[0]["filename"], "")  # no AttachmentBinaryObject

    def test_multiple_documents(self):
        """Should parse multiple AdditionalReferencedDocument entries."""
        docs_xml = """
        <ram:AdditionalReferencedDocument>
            <ram:IssuerAssignedID>LS-001</ram:IssuerAssignedID>
            <ram:TypeCode>916</ram:TypeCode>
            <ram:Name>Lieferschein</ram:Name>
            <ram:AttachmentBinaryObject filename="lieferschein.pdf"/>
        </ram:AdditionalReferencedDocument>
        <ram:AdditionalReferencedDocument>
            <ram:IssuerAssignedID>ZA-001</ram:IssuerAssignedID>
            <ram:TypeCode>916</ram:TypeCode>
            <ram:Name>Zeitaufstellung</ram:Name>
            <ram:AttachmentBinaryObject filename="zeitaufstellung.csv"/>
        </ram:AdditionalReferencedDocument>
        """
        xml = self._build_xml(docs_xml)
        data = self.parser.extract_invoice_data(xml)

        docs = data["additional_referenced_documents"]
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["filename"], "lieferschein.pdf")
        self.assertEqual(docs[1]["filename"], "zeitaufstellung.csv")

    def test_document_minimal_fields(self):
        """Should handle document with only TypeCode."""
        docs_xml = """
        <ram:AdditionalReferencedDocument>
            <ram:TypeCode>916</ram:TypeCode>
        </ram:AdditionalReferencedDocument>
        """
        xml = self._build_xml(docs_xml)
        data = self.parser.extract_invoice_data(xml)

        docs = data["additional_referenced_documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type_code"], "916")
        self.assertEqual(docs[0]["issuer_assigned_id"], "")
        self.assertEqual(docs[0]["description"], "")
        self.assertEqual(docs[0]["filename"], "")

    def test_delivery_note_type_code(self):
        """Should parse TypeCode 50 (delivery note)."""
        docs_xml = """
        <ram:AdditionalReferencedDocument>
            <ram:IssuerAssignedID>DN-100</ram:IssuerAssignedID>
            <ram:TypeCode>50</ram:TypeCode>
            <ram:Name>Delivery Note</ram:Name>
        </ram:AdditionalReferencedDocument>
        """
        xml = self._build_xml(docs_xml)
        data = self.parser.extract_invoice_data(xml)
        self.assertEqual(data["additional_referenced_documents"][0]["type_code"], "50")


# ============================================================================
# 4. InvoiceAttachment Record Creation Tests
# ============================================================================


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AttachmentRecordCreationTestCase(TestCase):
    """Test creation of InvoiceAttachment records during incoming invoice processing."""

    @patch("invoice_app.services.incoming_invoice_service.InvoiceValidator")
    @patch("invoice_app.services.incoming_invoice_service.InvoiceFileManager")
    @patch("invoice_app.services.incoming_invoice_service.SupplierDataExtractor")
    @patch("invoice_app.services.incoming_invoice_service.IncomingXmlParser")
    def setUp(self, mock_parser, mock_extractor, mock_file_manager, mock_validator):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()

        self.mock_parser = Mock()
        self.mock_extractor = Mock()
        self.mock_file_manager = Mock()
        self.mock_validator = Mock()

        mock_parser.return_value = self.mock_parser
        mock_extractor.return_value = self.mock_extractor
        mock_file_manager.return_value = self.mock_file_manager
        mock_validator.return_value = self.mock_validator

        self.service = IncomingInvoiceService(base_directory=self.temp_dir)

        self.test_user = User.objects.create_user(
            username="testuser_att", email="test@att.com", password="testpass123"
        )

        self._create_test_invoice()

    def _create_test_invoice(self):
        """Create a test invoice for attachment tests."""
        from invoice_app.models import Company, Country, Invoice

        germany = Country.objects.get_or_create(
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

        company = Company.objects.create(
            name="Test Supplier for Attachments",
            address_line1="Test St 1",
            city="Berlin",
            postal_code="10115",
            country=germany,
        )

        self.invoice = Invoice.objects.create(
            invoice_number="INC-ATT-001",
            invoice_type=Invoice.InvoiceType.INVOICE,
            company=company,
            issue_date="2024-01-15",
            currency="EUR",
            total_amount=1000.00,
            tax_amount=190.00,
            subtotal=810.00,
            status=Invoice.InvoiceStatus.SENT,
            created_by=self.test_user,
        )

    def test_create_attachments_empty_list(self):
        """Should handle empty attachment list gracefully."""
        result = self.service._create_attachment_records(self.invoice.id, [], {"additional_referenced_documents": []})
        self.assertEqual(result, [])

    def test_create_single_attachment(self):
        """Should create one InvoiceAttachment from extracted embedded file."""
        from invoice_app.models import InvoiceAttachment

        attachments = [
            {
                "filename": "lieferschein.pdf",
                "content": b"%PDF-1.4 fake content here",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {"additional_referenced_documents": []}

        created_ids = self.service._create_attachment_records(
            self.invoice.id,
            attachments,
            invoice_data,
        )

        self.assertEqual(len(created_ids), 1)
        att = InvoiceAttachment.objects.get(id=created_ids[0])
        self.assertEqual(att.invoice_id, self.invoice.id)
        self.assertEqual(att.original_filename, "lieferschein.pdf")
        self.assertEqual(att.mime_type, "application/pdf")
        # "lieferschein" in filename triggers heuristic → delivery_note
        self.assertEqual(att.attachment_type, "delivery_note")
        self.assertIn("lieferschein", att.file.name)

    def test_create_multiple_attachments(self):
        """Should create multiple InvoiceAttachment records."""
        from invoice_app.models import InvoiceAttachment

        attachments = [
            {
                "filename": "lieferschein.pdf",
                "content": b"%PDF-data",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            },
            {
                "filename": "stunden.csv",
                "content": b"date,hours\n2024-01-01,8",
                "mime_type": "text/csv",
                "af_relationship": "/Supplement",
            },
            {
                "filename": "foto.png",
                "content": b"\x89PNG fake",
                "mime_type": "image/png",
                "af_relationship": "/Supplement",
            },
        ]
        invoice_data = {"additional_referenced_documents": []}

        created_ids = self.service._create_attachment_records(self.invoice.id, attachments, invoice_data)

        self.assertEqual(len(created_ids), 3)
        self.assertEqual(InvoiceAttachment.objects.filter(invoice=self.invoice).count(), 3)

    def test_enrich_with_xml_metadata(self):
        """Should use XML AdditionalReferencedDocument metadata for description."""
        from invoice_app.models import InvoiceAttachment

        attachments = [
            {
                "filename": "lieferschein.pdf",
                "content": b"%PDF-data",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "lieferschein.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "LS-2024-042",
                    "description": "Lieferschein vom 15.01.2024",
                    "external_uri": "",
                }
            ],
        }

        created_ids = self.service._create_attachment_records(
            self.invoice.id,
            attachments,
            invoice_data,
        )

        att = InvoiceAttachment.objects.get(id=created_ids[0])
        self.assertEqual(att.description, "Lieferschein vom 15.01.2024")

    def test_xml_metadata_issuer_id_as_fallback_description(self):
        """When XML has no description, should use issuer_assigned_id."""
        from invoice_app.models import InvoiceAttachment

        attachments = [
            {
                "filename": "beleg.pdf",
                "content": b"%PDF",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "beleg.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "REF-99",
                    "description": "",
                    "external_uri": "",
                }
            ],
        }

        created_ids = self.service._create_attachment_records(
            self.invoice.id,
            attachments,
            invoice_data,
        )
        att = InvoiceAttachment.objects.get(id=created_ids[0])
        self.assertEqual(att.description, "REF-99")

    def test_determine_type_from_xml_typecode_916(self):
        """TypeCode 916 should map to supporting_document."""
        result = self.service._determine_attachment_type(
            "file.pdf",
            "/Supplement",
            {"type_code": "916", "filename": "file.pdf"},
        )
        self.assertEqual(result, "supporting_document")

    def test_determine_type_from_xml_typecode_50(self):
        """TypeCode 50 should map to delivery_note."""
        result = self.service._determine_attachment_type(
            "file.pdf",
            "/Supplement",
            {"type_code": "50", "filename": "file.pdf"},
        )
        self.assertEqual(result, "delivery_note")

    def test_determine_type_from_filename_lieferschein(self):
        """Filename containing 'lieferschein' should map to delivery_note."""
        result = self.service._determine_attachment_type(
            "Lieferschein_2024.pdf",
            "/Supplement",
            None,
        )
        self.assertEqual(result, "delivery_note")

    def test_determine_type_from_filename_timesheet(self):
        """Filename containing 'zeitaufstellung' should map to timesheet."""
        result = self.service._determine_attachment_type(
            "Zeitaufstellung_Jan.xlsx",
            "/Supplement",
            None,
        )
        self.assertEqual(result, "timesheet")

    def test_determine_type_default(self):
        """Unknown filename should default to supporting_document."""
        result = self.service._determine_attachment_type(
            "random_document.pdf",
            "/Supplement",
            None,
        )
        self.assertEqual(result, "supporting_document")

    def test_file_stored_in_correct_path(self):
        """Attachment file should be stored under invoices/attachments/invoice_{number}/."""
        from invoice_app.models import InvoiceAttachment

        attachments = [
            {
                "filename": "beleg.pdf",
                "content": b"%PDF-stored",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {"additional_referenced_documents": []}

        created_ids = self.service._create_attachment_records(
            self.invoice.id,
            attachments,
            invoice_data,
        )

        att = InvoiceAttachment.objects.get(id=created_ids[0])
        self.assertIn(f"invoice_{self.invoice.invoice_number}", att.file.name)

    def test_unmatched_xml_ref_adds_warning_to_notes(self):
        """XML ref with filename not in PDF should add warning to invoice notes."""
        from invoice_app.models import Invoice

        attachments = []  # No embedded files
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "lieferschein.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "LS-001",
                    "description": "Lieferschein Januar",
                    "external_uri": "",
                },
            ],
        }

        self.service._create_attachment_records(self.invoice.id, attachments, invoice_data)

        invoice = Invoice.objects.get(id=self.invoice.id)
        self.assertIn("⚠️", invoice.notes)
        self.assertIn("Lieferschein Januar", invoice.notes)

    def test_unmatched_xml_ref_with_uri(self):
        """Unmatched XML ref with external_uri should include URI in warning."""
        from invoice_app.models import Invoice

        attachments = []
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "report.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "RPT-001",
                    "description": "Externer Bericht",
                    "external_uri": "https://example.com/report.pdf",
                },
            ],
        }

        self.service._create_attachment_records(self.invoice.id, attachments, invoice_data)

        invoice = Invoice.objects.get(id=self.invoice.id)
        self.assertIn("extern: https://example.com/report.pdf", invoice.notes)

    def test_matched_ref_no_warning(self):
        """XML ref matching an embedded file should NOT produce a warning."""
        from invoice_app.models import Invoice

        attachments = [
            {
                "filename": "beleg.pdf",
                "content": b"%PDF",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "beleg.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "B-001",
                    "description": "Beleg",
                    "external_uri": "",
                },
            ],
        }

        self.service._create_attachment_records(self.invoice.id, attachments, invoice_data)

        invoice = Invoice.objects.get(id=self.invoice.id)
        self.assertNotIn("⚠️", invoice.notes)

    def test_partial_match_warns_for_missing_only(self):
        """When one ref matches and one doesn't, only the missing one gets a warning."""
        from invoice_app.models import Invoice

        attachments = [
            {
                "filename": "beleg.pdf",
                "content": b"%PDF",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]
        invoice_data = {
            "additional_referenced_documents": [
                {
                    "filename": "beleg.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "B-001",
                    "description": "Vorhandener Beleg",
                    "external_uri": "",
                },
                {
                    "filename": "missing.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "M-001",
                    "description": "Fehlender Beleg",
                    "external_uri": "",
                },
            ],
        }

        created_ids = self.service._create_attachment_records(self.invoice.id, attachments, invoice_data)

        # One attachment created for beleg.pdf
        self.assertEqual(len(created_ids), 1)

        invoice = Invoice.objects.get(id=self.invoice.id)
        self.assertIn("Fehlender Beleg", invoice.notes)
        self.assertNotIn("Vorhandener Beleg", invoice.notes)

    def test_no_attachments_no_refs_no_warning(self):
        """Empty attachments + empty refs should not modify notes."""
        from invoice_app.models import Invoice

        original_notes = self.invoice.notes
        self.service._create_attachment_records(self.invoice.id, [], {"additional_referenced_documents": []})

        invoice = Invoice.objects.get(id=self.invoice.id)
        self.assertEqual(invoice.notes, original_notes)


# ============================================================================
# 5. Integration: Full Pipeline with Attachments
# ============================================================================


class PipelineAttachmentIntegrationTestCase(TestCase):
    """Integration test: process_single_invoice with embedded attachments."""

    @patch("invoice_app.services.incoming_invoice_service.InvoiceValidator")
    @patch("invoice_app.services.incoming_invoice_service.InvoiceFileManager")
    @patch("invoice_app.services.incoming_invoice_service.SupplierDataExtractor")
    @patch("invoice_app.services.incoming_invoice_service.IncomingXmlParser")
    def setUp(self, mock_parser, mock_extractor, mock_file_manager, mock_validator):
        self.temp_dir = tempfile.mkdtemp()

        self.mock_parser = Mock()
        self.mock_file_manager = Mock()
        self.mock_validator = Mock()

        mock_parser.return_value = self.mock_parser
        mock_extractor.return_value = Mock()
        mock_file_manager.return_value = self.mock_file_manager
        mock_validator.return_value = self.mock_validator

        self.service = IncomingInvoiceService(base_directory=self.temp_dir)

        self.test_user = User.objects.create_user(
            username="testuser_pipe", email="pipe@test.com", password="testpass123"
        )

        self.realistic_invoice_data = {
            "invoice_number": "PIPE-ATT-001",
            "issue_date": "2024-06-15",
            "type_code": "380",
            "seller_name": "Pipeline Supplier GmbH",
            "seller_id": "DE111222333",
            "buyer_name": "Our Company",
            "total_amount": 5000.00,
            "tax_amount": 950.00,
            "currency": "EUR",
            "line_items": [{"description": "Services", "quantity": 1.0, "unit_price": 5000.00, "line_total": 5000.00}],
            "additional_referenced_documents": [
                {
                    "filename": "lieferschein.pdf",
                    "type_code": "916",
                    "issuer_assigned_id": "LS-PIPE-001",
                    "description": "Lieferschein zur Rechnung",
                    "external_uri": "",
                },
            ],
        }
        self.mock_parser.extract_invoice_data.return_value = self.realistic_invoice_data

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_full_pipeline_creates_attachments(self):
        """Full pipeline should create invoice AND attachment records."""
        from invoice_app.models import InvoiceAttachment

        extracted_attachments = [
            {
                "filename": "lieferschein.pdf",
                "content": b"%PDF-pipeline-test",
                "mime_type": "application/pdf",
                "af_relationship": "/Supplement",
            }
        ]

        validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            extracted_xml="<xml>valid</xml>",
            extracted_attachments=extracted_attachments,
        )
        self.mock_validator.validate_invoice_file.return_value = validation_result
        self.mock_validator.check_duplicate_invoice.return_value = False
        self.mock_file_manager.move_to_processed.return_value = "/processed/file.pdf"

        result = self.service.process_single_invoice("/test/incoming.pdf")

        self.assertTrue(result.success)
        self.assertIsNotNone(result.invoice_id)

        # Verify attachment was created
        attachments = InvoiceAttachment.objects.filter(invoice_id=result.invoice_id)
        self.assertEqual(attachments.count(), 1)
        self.assertEqual(attachments.first().original_filename, "lieferschein.pdf")
        self.assertEqual(attachments.first().description, "Lieferschein zur Rechnung")

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_pipeline_without_attachments(self):
        """Pipeline should work fine when no attachments are embedded."""
        validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            extracted_xml="<xml>valid</xml>",
            extracted_attachments=[],
        )
        self.mock_validator.validate_invoice_file.return_value = validation_result
        self.mock_validator.check_duplicate_invoice.return_value = False
        self.mock_file_manager.move_to_processed.return_value = "/processed/file.pdf"

        # Remove additional_referenced_documents from data
        self.realistic_invoice_data["additional_referenced_documents"] = []

        result = self.service.process_single_invoice("/test/incoming.pdf")

        self.assertTrue(result.success)
        self.assertIsNotNone(result.invoice_id)
