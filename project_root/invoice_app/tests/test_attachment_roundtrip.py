"""
Integration tests for attachment roundtrip: embed → extract → verify.

Tests that supplementary documents (rechnungsbegründende Dokumente) survive
a full cycle through the PDF/A-3 embedding and extraction pipeline:
  1. Embed attachments into a PDF/A-3 via PdfA3Generator.embed_attachments()
  2. Extract them via InvoiceValidator._extract_embedded_attachments()
  3. Verify content, filenames, MIME types, and AFRelationship are preserved.

Also tests:
- AdditionalReferencedDocument XML generation (Phase C)
- Unicode filenames
- Near-limit file sizes
"""

import os
import tempfile

import pikepdf
from django.test import TestCase
from lxml import etree

from invoice_app.utils.pdf import PdfA3Generator
from invoice_app.utils.validation import InvoiceValidator
from invoice_app.utils.xml.constants import RAM_NS, RSM_NS
from invoice_app.utils.xml.generator import ZugferdXmlGenerator


class AttachmentRoundtripTestCase(TestCase):
    """Embed attachments into PDF, then extract and verify content integrity."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_dir, xml_dir=self.temp_dir)
        self.validator = object.__new__(InvoiceValidator)

    def _create_base_pdf(self):
        """Create a minimal PDF/A-3 with factur-x.xml already embedded."""
        pdf_path = os.path.join(self.temp_dir, "roundtrip_test.pdf")
        pdf = pikepdf.new()
        pdf.pages.append(
            pikepdf.Page(
                pikepdf.Dictionary(
                    Type=pikepdf.Name("/Page"),
                    MediaBox=[0, 0, 595, 842],
                )
            )
        )

        # Embed factur-x.xml so the base PDF is realistic
        xml_content = b'<?xml version="1.0" encoding="UTF-8"?><Invoice><ID>RT-001</ID></Invoice>'
        xml_stream = pikepdf.Stream(pdf, xml_content)
        xml_stream["/Type"] = pikepdf.Name("/EmbeddedFile")
        xml_stream["/Subtype"] = pikepdf.Object.parse(b"/text#2Fxml")

        xml_filespec = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Filespec"),
                F=pikepdf.String("factur-x.xml"),
                UF=pikepdf.String("factur-x.xml"),
                AFRelationship=pikepdf.Name("/Data"),
                EF=pikepdf.Dictionary(F=xml_stream),
            )
        )

        pdf.Root["/Names"] = pikepdf.Dictionary(
            EmbeddedFiles=pikepdf.Dictionary(Names=pikepdf.Array([pikepdf.String("factur-x.xml"), xml_filespec]))
        )
        pdf.Root["/AF"] = pikepdf.Array([xml_filespec])

        pdf.save(pdf_path)
        return pdf_path

    def _make_mock_attachment(self, filename, content, mime_type="application/octet-stream"):
        """Create a mock InvoiceAttachment for embed_attachments()."""
        from unittest.mock import MagicMock

        att = MagicMock()
        att.original_filename = filename
        att.description = filename
        att.mime_type = mime_type
        att.attachment_type = "supporting_document"
        att.file.read.return_value = content
        att.file.seek = MagicMock()
        att.file.name = f"invoices/attachments/invoice_TEST/{filename}"
        return att

    # ── Roundtrip Tests ──────────────────────────────────────────────────

    def test_roundtrip_single_pdf_attachment(self):
        """Embed a single PDF attachment, extract it, verify content."""
        pdf_path = self._create_base_pdf()
        original_content = b"%PDF-1.4 Lieferschein content here"
        att = self._make_mock_attachment("Lieferschein.pdf", original_content, "application/pdf")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["filename"], "Lieferschein.pdf")
        self.assertEqual(extracted[0]["content"], original_content)
        self.assertEqual(extracted[0]["mime_type"], "application/pdf")
        self.assertEqual(extracted[0]["af_relationship"], "/Supplement")

    def test_roundtrip_multiple_file_types(self):
        """Embed PDF + CSV + PNG, extract all, verify each."""
        pdf_path = self._create_base_pdf()
        files = [
            ("Stundenzettel.pdf", b"%PDF-1.4 timesheet data", "application/pdf"),
            ("Materialkosten.csv", b"pos,beschreibung,preis\n1,Schrauben,12.50", "text/csv"),
            ("Foto_Baustelle.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png"),
        ]
        attachments = [self._make_mock_attachment(f, c, m) for f, c, m in files]

        self.pdf_generator.embed_attachments(pdf_path, attachments)

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 3)

        by_name = {e["filename"]: e for e in extracted}
        for filename, content, mime in files:
            self.assertIn(filename, by_name, f"{filename} not found in extracted attachments")
            self.assertEqual(by_name[filename]["content"], content)
            self.assertEqual(by_name[filename]["mime_type"], mime)
            self.assertEqual(by_name[filename]["af_relationship"], "/Supplement")

    def test_roundtrip_preserves_facturx_xml(self):
        """Embedding attachments must not corrupt the existing factur-x.xml."""
        pdf_path = self._create_base_pdf()
        att = self._make_mock_attachment("Beleg.pdf", b"%PDF-1.4 receipt", "application/pdf")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        # Verify factur-x.xml is still accessible and intact
        with pikepdf.open(pdf_path) as pdf:
            names = list(pdf.Root["/Names"]["/EmbeddedFiles"]["/Names"])
            xml_found = False
            for i in range(0, len(names), 2):
                if str(names[i]) == "factur-x.xml":
                    filespec = names[i + 1]
                    xml_content = bytes(filespec["/EF"]["/F"].read_bytes())
                    self.assertIn(b"RT-001", xml_content)
                    xml_found = True
                    break
            self.assertTrue(xml_found, "factur-x.xml disappeared after embedding attachments")

    def test_roundtrip_af_relationships_correct(self):
        """factur-x.xml must be /Data, all others /Supplement."""
        pdf_path = self._create_base_pdf()
        att = self._make_mock_attachment("Nachweis.pdf", b"%PDF-1.4 proof", "application/pdf")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        with pikepdf.open(pdf_path) as pdf:
            rels = {}
            for fs in pdf.Root["/AF"]:
                name = str(fs.get("/F", "?"))
                rel = str(fs.get("/AFRelationship", "?"))
                rels[name] = rel

            self.assertEqual(rels.get("factur-x.xml"), "/Data")
            self.assertEqual(rels.get("Nachweis.pdf"), "/Supplement")

    def test_roundtrip_binary_content_exact_match(self):
        """Binary content must survive embed→extract without any modification."""
        pdf_path = self._create_base_pdf()
        # Create deterministic binary content with all byte values
        original_content = bytes(range(256)) * 40  # 10240 bytes, all byte values
        att = self._make_mock_attachment("binary_test.pdf", original_content, "application/pdf")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["content"], original_content)


class UnicodeFilenameTestCase(TestCase):
    """Test that Unicode filenames survive the embed→extract roundtrip."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_dir, xml_dir=self.temp_dir)
        self.validator = object.__new__(InvoiceValidator)

    def _create_base_pdf(self):
        """Create a minimal PDF with factur-x.xml embedded."""
        pdf_path = os.path.join(self.temp_dir, "unicode_test.pdf")
        pdf = pikepdf.new()
        pdf.pages.append(
            pikepdf.Page(
                pikepdf.Dictionary(
                    Type=pikepdf.Name("/Page"),
                    MediaBox=[0, 0, 595, 842],
                )
            )
        )

        xml_stream = pikepdf.Stream(pdf, b"<Invoice/>")
        xml_stream["/Type"] = pikepdf.Name("/EmbeddedFile")
        xml_filespec = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Filespec"),
                F=pikepdf.String("factur-x.xml"),
                UF=pikepdf.String("factur-x.xml"),
                AFRelationship=pikepdf.Name("/Data"),
                EF=pikepdf.Dictionary(F=xml_stream),
            )
        )
        pdf.Root["/Names"] = pikepdf.Dictionary(
            EmbeddedFiles=pikepdf.Dictionary(Names=pikepdf.Array([pikepdf.String("factur-x.xml"), xml_filespec]))
        )
        pdf.Root["/AF"] = pikepdf.Array([xml_filespec])
        pdf.save(pdf_path)
        return pdf_path

    def _make_mock_attachment(self, filename, content, mime_type="application/pdf"):
        from unittest.mock import MagicMock

        att = MagicMock()
        att.original_filename = filename
        att.description = filename
        att.mime_type = mime_type
        att.attachment_type = "supporting_document"
        att.file.read.return_value = content
        att.file.seek = MagicMock()
        att.file.name = f"invoices/attachments/invoice_TEST/{filename}"
        return att

    def test_german_umlauts_in_filename(self):
        """Filenames with ä, ö, ü, ß must survive roundtrip."""
        pdf_path = self._create_base_pdf()
        filename = "Stückliste_März_Größe.pdf"
        att = self._make_mock_attachment(filename, b"%PDF-1.4 umlaut test")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["filename"], filename)

    def test_french_accents_in_filename(self):
        """Accented characters (common in Factur-X context) must survive."""
        pdf_path = self._create_base_pdf()
        filename = "Résumé_données.pdf"
        att = self._make_mock_attachment(filename, b"%PDF-1.4 french test")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["filename"], filename)

    def test_spaces_and_special_chars_in_filename(self):
        """Spaces, parentheses, and hyphens in filenames."""
        pdf_path = self._create_base_pdf()
        filename = "Lieferschein (Kopie) 2026-03.pdf"
        att = self._make_mock_attachment(filename, b"%PDF-1.4 special chars")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["filename"], filename)

    def test_unicode_csv_filename(self):
        """Unicode in non-PDF attachment filename."""
        pdf_path = self._create_base_pdf()
        filename = "Übersicht_Stunden_März.csv"
        content = "Datum,Stunden,Beschäftigung\n2026-03-01,8,Entwicklung".encode()
        att = self._make_mock_attachment(filename, content, "text/csv")

        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["filename"], filename)
        self.assertEqual(extracted[0]["content"], content)
        self.assertEqual(extracted[0]["mime_type"], "text/csv")


class AttachmentSizeLimitTestCase(TestCase):
    """Test embedding and extraction near the 10 MB size limit."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_dir, xml_dir=self.temp_dir)
        self.validator = object.__new__(InvoiceValidator)

    def _create_base_pdf(self):
        pdf_path = os.path.join(self.temp_dir, "size_test.pdf")
        pdf = pikepdf.new()
        pdf.pages.append(
            pikepdf.Page(
                pikepdf.Dictionary(
                    Type=pikepdf.Name("/Page"),
                    MediaBox=[0, 0, 595, 842],
                )
            )
        )

        xml_stream = pikepdf.Stream(pdf, b"<Invoice/>")
        xml_stream["/Type"] = pikepdf.Name("/EmbeddedFile")
        xml_filespec = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Filespec"),
                F=pikepdf.String("factur-x.xml"),
                UF=pikepdf.String("factur-x.xml"),
                AFRelationship=pikepdf.Name("/Data"),
                EF=pikepdf.Dictionary(F=xml_stream),
            )
        )
        pdf.Root["/Names"] = pikepdf.Dictionary(
            EmbeddedFiles=pikepdf.Dictionary(Names=pikepdf.Array([pikepdf.String("factur-x.xml"), xml_filespec]))
        )
        pdf.Root["/AF"] = pikepdf.Array([xml_filespec])
        pdf.save(pdf_path)
        return pdf_path

    def _make_mock_attachment(self, filename, content, mime_type="application/pdf"):
        from unittest.mock import MagicMock

        att = MagicMock()
        att.original_filename = filename
        att.description = filename
        att.mime_type = mime_type
        att.attachment_type = "supporting_document"
        att.file.read.return_value = content
        att.file.seek = MagicMock()
        att.file.name = f"invoices/attachments/invoice_TEST/{filename}"
        return att

    def test_near_limit_attachment(self):
        """A 9.9 MB attachment should embed and extract correctly."""
        pdf_path = self._create_base_pdf()
        size_bytes = int(9.9 * 1024 * 1024)  # 9.9 MB
        # Use repeating pattern to detect corruption
        pattern = b"TESTBLOCK_" + bytes(range(256))
        original_content = (pattern * (size_bytes // len(pattern) + 1))[:size_bytes]
        att = self._make_mock_attachment("large_scan.pdf", original_content)

        embedded = self.pdf_generator.embed_attachments(pdf_path, [att])
        self.assertEqual(embedded, ["large_scan.pdf"])

        extracted = self.validator._extract_embedded_attachments(pdf_path)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(len(extracted[0]["content"]), size_bytes)
        self.assertEqual(extracted[0]["content"], original_content)


class AdditionalReferencedDocumentXmlTestCase(TestCase):
    """Test AdditionalReferencedDocument generation in ZUGFeRD XML (Phase C)."""

    def setUp(self):
        self.generator = ZugferdXmlGenerator(profile="COMFORT")
        self.nsmap = {"ram": RAM_NS, "rsm": RSM_NS}
        self.base_invoice_data = {
            "number": "XML-ARD-001",
            "date": "20260414",
            "due_date": "20260514",
            "currency": "EUR",
            "company": {"name": "Sender GmbH", "tax_id": "DE111111111"},
            "customer": {"name": "Empfänger AG", "tax_id": "DE222222222"},
            "items": [{"product_name": "Beratung", "quantity": 10, "price": 150.00, "tax_rate": 19.0}],
        }

    def _parse_xml(self, xml_string):
        return etree.fromstring(xml_string.encode("utf-8"))

    def test_no_documents_no_element(self):
        """Without additional_documents, no AdditionalReferencedDocument appears."""
        xml_string = self.generator.generate_xml(self.base_invoice_data)
        root = self._parse_xml(xml_string)
        refs = root.findall(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(len(refs), 0)

    def test_single_attachment_generates_element(self):
        """A single attachment produces one AdditionalReferencedDocument."""
        data = dict(self.base_invoice_data)
        data["additional_documents"] = [
            {"filename": "Stundenzettel.pdf", "description": "Stundenzettel März 2026", "type_code": "916"},
        ]
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        refs = root.findall(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(len(refs), 1)

        ref = refs[0]
        self.assertEqual(ref.find("ram:IssuerAssignedID", self.nsmap).text, "Stundenzettel.pdf")
        self.assertEqual(ref.find("ram:TypeCode", self.nsmap).text, "916")
        self.assertEqual(ref.find("ram:Name", self.nsmap).text, "Stundenzettel März 2026")

    def test_multiple_attachments(self):
        """Multiple attachments produce multiple AdditionalReferencedDocument elements."""
        data = dict(self.base_invoice_data)
        data["additional_documents"] = [
            {"filename": "Stundenzettel.pdf", "description": "Stundenzettel", "type_code": "916"},
            {"filename": "Lieferschein.pdf", "description": "Lieferschein", "type_code": "916"},
            {"filename": "Materialkosten.csv", "description": "Materialliste", "type_code": "916"},
        ]
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        refs = root.findall(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(len(refs), 3)

        filenames = [r.find("ram:IssuerAssignedID", self.nsmap).text for r in refs]
        self.assertEqual(filenames, ["Stundenzettel.pdf", "Lieferschein.pdf", "Materialkosten.csv"])

    def test_element_in_correct_xsd_position(self):
        """AdditionalReferencedDocument must come after BuyerOrderReferencedDocument."""
        data = dict(self.base_invoice_data)
        data["buyer_reference"] = "PO-2026-42"
        data["additional_documents"] = [
            {"filename": "Beleg.pdf", "description": "Beleg", "type_code": "916"},
        ]
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        agreement = root.find(".//ram:ApplicableHeaderTradeAgreement", self.nsmap)
        children = [etree.QName(c).localname for c in agreement]

        buyer_idx = children.index("BuyerOrderReferencedDocument")
        additional_idx = children.index("AdditionalReferencedDocument")
        self.assertGreater(
            additional_idx, buyer_idx, "AdditionalReferencedDocument must come after BuyerOrderReferencedDocument"
        )

    def test_unicode_in_description(self):
        """Unicode characters in description and filename must be preserved."""
        data = dict(self.base_invoice_data)
        data["additional_documents"] = [
            {"filename": "Stückliste_März.pdf", "description": "Stückliste für Größenänderung", "type_code": "916"},
        ]
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        ref = root.find(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(ref.find("ram:IssuerAssignedID", self.nsmap).text, "Stückliste_März.pdf")
        self.assertEqual(ref.find("ram:Name", self.nsmap).text, "Stückliste für Größenänderung")

    def test_default_type_code_is_916(self):
        """If no type_code is provided, it defaults to 916."""
        data = dict(self.base_invoice_data)
        data["additional_documents"] = [
            {"filename": "misc.pdf", "description": "Sonstiges"},
        ]
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        ref = root.find(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(ref.find("ram:TypeCode", self.nsmap).text, "916")

    def test_empty_additional_documents_list(self):
        """Empty additional_documents list produces no elements."""
        data = dict(self.base_invoice_data)
        data["additional_documents"] = []
        xml_string = self.generator.generate_xml(data)
        root = self._parse_xml(xml_string)

        refs = root.findall(".//ram:AdditionalReferencedDocument", self.nsmap)
        self.assertEqual(len(refs), 0)
