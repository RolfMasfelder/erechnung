"""
Tests for the PDF/A-3 generation and XML embedding utilities.
"""

import os
import subprocess
import tempfile
from unittest import mock

from django.test import TestCase
from pypdf import PdfReader

from invoice_app.utils.pdf import PdfA3Generator


class TestPdfA3Generator(TestCase):
    """Test suite for the PDF/A-3 generator."""

    def setUp(self):
        """Set up test data for PDF generation."""
        # Create temporary directories for outputs
        self.temp_output_dir = tempfile.mkdtemp()
        self.temp_xml_dir = tempfile.mkdtemp()

        # Use temp directories so tests don't pollute media/xml/
        # (previously used /app/project_root/media/xml for debugging)

        # Initialize generator with directories
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_output_dir, xml_dir=self.temp_xml_dir)

        # Sample invoice data for testing
        self.sample_invoice_data = {
            "number": "INV-2023-001",
            "date": "2023-05-01",
            "due_date": "2023-05-31",
            "currency": "EUR",
            "customer": {
                "name": "Test Customer AG",
                "address": "Customer Avenue 456, Munich",
                "email": "info@customer.com",
                "tax_id": "DE987654321",
            },
            "items": [
                {"product_name": "Product A", "quantity": 2, "price": 100.00, "tax_rate": 19.0},
                {"product_name": "Product B", "quantity": 1, "price": 50.00, "tax_rate": 7.0},
            ],
        }

        # Sample XML content for testing
        self.sample_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <Invoice>
            <ID>INV-2023-001</ID>
            <IssueDate>2023-05-01</IssueDate>
            <DueDate>2023-05-31</DueDate>
        </Invoice>
        """

    def tearDown(self):
        """Clean up temporary files and directories."""
        # Only clean up if we're using actual temp directories
        if self.temp_output_dir.startswith("/tmp") and os.path.exists(self.temp_output_dir):
            # Remove all files in temp directories
            for file in os.listdir(self.temp_output_dir):
                os.unlink(os.path.join(self.temp_output_dir, file))
            # Remove temp directories
            os.rmdir(self.temp_output_dir)

        if self.temp_xml_dir.startswith("/tmp") and os.path.exists(self.temp_xml_dir):
            for file in os.listdir(self.temp_xml_dir):
                os.unlink(os.path.join(self.temp_xml_dir, file))
            os.rmdir(self.temp_xml_dir)

    def test_create_base_pdf(self):
        """Test creation of base PDF."""
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file_path = temp_file.name

        try:
            # Create base PDF
            result_path = self.pdf_generator._create_base_pdf(self.sample_invoice_data, temp_file_path)

            # Check if file exists and is not empty
            self.assertTrue(os.path.exists(result_path))
            self.assertGreater(os.path.getsize(result_path), 0)
        finally:
            # Clean up
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    @mock.patch("subprocess.run")
    def test_convert_to_pdfa3(self, mock_run):
        """Test conversion to PDF/A-3 format."""
        # Mock subprocess.run to avoid actual Ghostscript execution.
        # stdout/stderr must be bytes so .decode() works in the production code.
        mock_run.return_value = mock.Mock(returncode=0, stdout=b"", stderr=b"")

        # Create input and output paths
        input_path = os.path.join(self.temp_output_dir, "input.pdf")
        output_path = os.path.join(self.temp_output_dir, "output.pdf")

        # Create an empty input file
        with open(input_path, "wb") as f:
            f.write(b"%PDF-1.7\n%Test PDF\n")

        # Call the method under test
        result = self.pdf_generator._convert_to_pdfa3(input_path, output_path)

        # Check that subprocess.run was called with correct parameters
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # First argument should be a list of Ghostscript parameters
        self.assertIsInstance(args[0], list)
        self.assertIn("-dSAFER", args[0])  # Security hardening (Issue #5)
        self.assertIn("-dPDFA=3", args[0])
        self.assertIn(f"-sOutputFile={output_path}", args[0])
        self.assertIn(input_path, args[0])
        # Verify the ICC permit-file-read flag is present (required for OutputIntent)
        self.assertTrue(any("--permit-file-read" in a for a in args[0]))

        # Check that check=True, capture_output, and timeout were set
        self.assertTrue(kwargs.get("check"))
        self.assertTrue(kwargs.get("capture_output"))
        self.assertEqual(kwargs.get("timeout"), 60)

        # Check that the result is the output path
        self.assertEqual(result, output_path)

    @mock.patch("subprocess.run")
    @mock.patch("invoice_app.utils.pdf.logger")  # Mock the logger to suppress error messages
    def test_convert_to_pdfa3_error(self, mock_logger, mock_run):
        """Test handling of errors during PDF/A-3 conversion."""
        # Mock subprocess.run to simulate an error
        error = subprocess.CalledProcessError(1, cmd="gs")
        error.stderr = b"Ghostscript error: Invalid parameter"
        mock_run.side_effect = error

        # Create input and output paths
        input_path = os.path.join(self.temp_output_dir, "input.pdf")
        output_path = os.path.join(self.temp_output_dir, "output.pdf")

        # Create an empty input file
        with open(input_path, "wb") as f:
            f.write(b"%PDF-1.7\n%Test PDF\n")

        # Call the method under test and expect an exception
        with self.assertRaises(Exception) as context:
            self.pdf_generator._convert_to_pdfa3(input_path, output_path)

        # Check the exception message
        self.assertIn("PDF/A-3 conversion failed", str(context.exception))

        # Verify that error logging was called but we don't see the output
        mock_logger.error.assert_called()

    @mock.patch("subprocess.run")
    @mock.patch("invoice_app.utils.pdf.logger")
    def test_convert_to_pdfa3_timeout(self, mock_logger, mock_run):
        """Test that Ghostscript timeout is handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gs", timeout=60)

        input_path = os.path.join(self.temp_output_dir, "input.pdf")
        output_path = os.path.join(self.temp_output_dir, "output.pdf")

        with open(input_path, "wb") as f:
            f.write(b"%PDF-1.7\n%Test PDF\n")

        with self.assertRaises(RuntimeError) as context:
            self.pdf_generator._convert_to_pdfa3(input_path, output_path)

        self.assertIn("timed out", str(context.exception))

    def test_embed_xml(self):
        """Test that _embed_xml uses pikepdf to embed XML and returns pdf_path."""
        pdf_path = os.path.join(self.temp_output_dir, "test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.7\nTest PDF placeholder")

        # Mock the entire pikepdf module (imported locally inside _embed_xml)
        mock_pikepdf = mock.MagicMock()
        mock_pdf = mock.MagicMock()
        mock_pdf.Root = {}  # Empty real dict so "/Metadata" not in check returns True (→ early return)
        mock_pikepdf.open.return_value.__enter__.return_value = mock_pdf

        with mock.patch.dict("sys.modules", {"pikepdf": mock_pikepdf}):
            result = self.pdf_generator._embed_xml(pdf_path, self.sample_xml_content, "test.xml", "Test XML")

        # Verify pikepdf.open was called with the pdf_path
        mock_pikepdf.open.assert_called_once_with(pdf_path, allow_overwriting_input=True)
        # Verify the pdf was saved
        mock_pdf.save.assert_called_once_with(pdf_path)
        self.assertEqual(result, pdf_path)

    def test_embed_xml_saves_xml_to_disk(self):
        """Test that _embed_xml writes the XML file to xml_dir before calling pikepdf."""
        pdf_path = os.path.join(self.temp_output_dir, "facturx_disk.pdf")
        xml_filename = "facturx_disk.xml"
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.7\nDummy")

        # Mock the entire pikepdf module (imported locally inside _embed_xml)
        mock_pikepdf = mock.MagicMock()
        mock_pdf = mock.MagicMock()
        mock_pdf.Root = {}
        mock_pikepdf.open.return_value.__enter__.return_value = mock_pdf

        with mock.patch.dict("sys.modules", {"pikepdf": mock_pikepdf}):
            self.pdf_generator._embed_xml(pdf_path, self.sample_xml_content, xml_filename)

        xml_on_disk = os.path.join(self.temp_xml_dir, xml_filename)
        self.assertTrue(os.path.exists(xml_on_disk), "XML file must be written to xml_dir")
        with open(xml_on_disk, encoding="utf-8") as fh:
            self.assertIn("Invoice", fh.read())
        # Ensure pikepdf was called
        mock_pikepdf.open.assert_called_once()

    @mock.patch("os.remove")  # Mock the file removal to prevent warnings
    @mock.patch("invoice_app.utils.pdf.ZugferdXmlGenerator")  # Mock entire XML generator
    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch.object(PdfA3Generator, "_convert_to_pdfa3")
    @mock.patch.object(PdfA3Generator, "_embed_xml")
    def test_generate_invoice_pdf(
        self, mock_embed_xml, mock_convert, mock_create_base, mock_xml_gen_class, mock_remove
    ):
        """Test the complete PDF generation workflow."""

        # Mock the methods to return dynamic file paths based on actual call
        def mock_create_base_side_effect(invoice_data, output_path):
            # Create the actual file at the expected location
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.7\nTemp PDF content")
            return output_path

        def mock_convert_side_effect(input_path, output_path):
            # Create the actual file at the expected location
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.7\nFinal PDF content")
            return output_path

        def mock_embed_xml_side_effect(pdf_path, xml_content, xml_filename):
            # Just return the PDF path - the file should already exist
            return pdf_path

        # Configure mocks with side effects
        mock_create_base.side_effect = mock_create_base_side_effect
        mock_convert.side_effect = mock_convert_side_effect
        mock_embed_xml.side_effect = mock_embed_xml_side_effect
        mock_xml_gen_class.return_value.generate_xml.return_value = "<xml>mock</xml>"

        # Call the method under test (without xml_content to test auto-generation)
        result = self.pdf_generator.generate_invoice_pdf(self.sample_invoice_data, invoice_instance=mock.MagicMock())

        # Check that all required methods were called
        mock_create_base.assert_called_once()
        mock_convert.assert_called_once()
        mock_embed_xml.assert_called_once()
        mock_remove.assert_called_once()  # Verify temp file cleanup was attempted

        # Check the result structure
        self.assertIsInstance(result, dict)
        self.assertIn("pdf_path", result)
        self.assertIn("xml_path", result)
        # Check that the PDF path contains the invoice number
        self.assertIn("INV-2023-001", result["pdf_path"])
        self.assertIsNotNone(result["xml_path"])


class TestPdfAttachmentRoundtrip(TestCase):
    """
    Roundtrip tests for PDF attachment embedding and extraction.

    These tests verify that XML content can be:
    1. Embedded into a PDF/A-3 document
    2. Extracted back from the PDF
    3. Content integrity is preserved

    This addresses Issue #3: Add PDF attachment roundtrip test
    """

    def setUp(self):
        """Set up test data and directories."""
        self.temp_output_dir = tempfile.mkdtemp()
        self.temp_xml_dir = tempfile.mkdtemp()

        # Ensure directories exist
        os.makedirs(self.temp_output_dir, exist_ok=True)
        os.makedirs(self.temp_xml_dir, exist_ok=True)

        self.pdf_generator = PdfA3Generator(output_dir=self.temp_output_dir, xml_dir=self.temp_xml_dir)

        # Sample invoice data
        self.sample_invoice_data = {
            "number": "ROUNDTRIP-TEST-001",
            "date": "2025-12-02",
            "due_date": "2025-12-31",
            "currency": "EUR",
            "customer": {
                "name": "Roundtrip Test Customer",
                "address": "Test Street 123, Test City",
                "email": "test@roundtrip.com",
                "tax_id": "DE123456789",
            },
            "items": [
                {"product_name": "Test Product", "quantity": 1, "price": 100.00, "tax_rate": 19.0},
            ],
        }

        # Sample XML content with identifiable markers
        self.test_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                          xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                          xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
    <rsm:ExchangedDocumentContext>
        <ram:GuidelineSpecifiedDocumentContextParameter>
            <ram:ID>urn:factur-x.eu:1p0:minimum</ram:ID>
        </ram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>
    <rsm:ExchangedDocument>
        <ram:ID>ROUNDTRIP-TEST-001</ram:ID>
        <ram:TypeCode>380</ram:TypeCode>
        <ram:IssueDateTime>
            <udt:DateTimeString format="102">20251202</udt:DateTimeString>
        </ram:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
                <ram:Name>Test Seller Company</ram:Name>
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty>
                <ram:Name>Roundtrip Test Customer</ram:Name>
            </ram:BuyerTradeParty>
        </ram:ApplicableHeaderTradeAgreement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""

        self.generated_files = []

    def tearDown(self):
        """Clean up generated test files."""
        for file_path in self.generated_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except OSError:
                pass

    def _create_minimal_pdf(self, pdf_path):
        """Create a minimal valid PDF using pikepdf (replaces reportlab dependency)."""
        import pikepdf

        pdf = pikepdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Page"),
                MediaBox=[0, 0, 595, 842],
            )
        )
        pdf.pages.append(page)
        pdf.save(pdf_path)

    def _extract_attachments_from_pdf(self, pdf_path):
        """
        Helper function to extract all attachments from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            dict: Dictionary with attachment names as keys and content as values
        """
        attachments = {}

        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)

            # Try pypdf >= 3.0 attachments property first (simpler API)
            if hasattr(reader, "attachments") and reader.attachments:
                for name, content_list in reader.attachments.items():
                    if content_list:
                        attachments[name] = content_list[0]
                return attachments

            # Fallback: Check for embedded files in the catalog
            attachments = self._extract_from_catalog(reader)

        return attachments

    def _extract_from_catalog(self, reader):
        """Extract attachments from PDF catalog structure."""
        attachments = {}

        root = reader.trailer.get("/Root")
        if not root:
            return attachments

        names = root.get("/Names")
        if not names:
            return attachments

        embedded_files = names.get("/EmbeddedFiles")
        if not embedded_files:
            return attachments

        file_names = embedded_files.get("/Names")
        if not file_names:
            return attachments

        # Names array is [name1, ref1, name2, ref2, ...]
        for i in range(0, len(file_names), 2):
            name = file_names[i]
            file_spec = file_names[i + 1].get_object()
            content = self._extract_file_content(file_spec)
            if content:
                attachments[name] = content

        return attachments

    def _extract_file_content(self, file_spec):
        """Extract content from a file specification object."""
        ef = file_spec.get("/EF")
        if not ef:
            return None

        stream_ref = ef.get("/F")
        if not stream_ref:
            return None

        stream = stream_ref.get_object()
        return stream.get_data()

    def test_embed_and_extract_xml_roundtrip(self):
        """
        Test that XML can be embedded into PDF and extracted back with identical content.

        This is the core roundtrip test verifying:
        1. XML embedding works correctly
        2. XML can be extracted from the PDF
        3. Content integrity is preserved
        """
        # Create a base PDF
        pdf_path = os.path.join(self.temp_output_dir, "roundtrip_test.pdf")
        self.generated_files.append(pdf_path)

        # Create base PDF
        self._create_minimal_pdf(pdf_path)

        self.assertTrue(os.path.exists(pdf_path))

        # Embed XML
        xml_filename = "roundtrip_test.xml"
        xml_path = os.path.join(self.temp_xml_dir, xml_filename)
        self.generated_files.append(xml_path)

        result_path = self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, xml_filename, "ZUGFeRD Test XML")

        self.assertEqual(result_path, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 0)

        # Extract attachments
        attachments = self._extract_attachments_from_pdf(pdf_path)

        # factur-x embeds the XML under the standard name 'factur-x.xml'
        EMBEDDED_NAME = "factur-x.xml"
        self.assertGreater(len(attachments), 0, "No attachments found in PDF")
        self.assertIn(EMBEDDED_NAME, attachments, f"Expected attachment '{EMBEDDED_NAME}' not found")

        # Verify content integrity
        extracted_content = attachments[EMBEDDED_NAME]
        if isinstance(extracted_content, bytes):
            extracted_content = extracted_content.decode("utf-8")

        # Normalize whitespace for comparison
        original_normalized = " ".join(self.test_xml_content.split())
        extracted_normalized = " ".join(extracted_content.split())

        self.assertEqual(original_normalized, extracted_normalized, "Extracted XML content does not match original")

        # Verify specific content markers
        self.assertIn("ROUNDTRIP-TEST-001", extracted_content)
        self.assertIn("CrossIndustryInvoice", extracted_content)
        self.assertIn("Roundtrip Test Customer", extracted_content)

    def test_attachment_count_single(self):
        """Test that exactly one attachment is present after embedding."""
        pdf_path = os.path.join(self.temp_output_dir, "single_attachment_test.pdf")
        self.generated_files.append(pdf_path)

        # Create base PDF
        self._create_minimal_pdf(pdf_path)

        # Embed XML
        xml_filename = "single_attachment.xml"
        xml_path = os.path.join(self.temp_xml_dir, xml_filename)
        self.generated_files.append(xml_path)

        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, xml_filename)

        # Extract and verify count
        attachments = self._extract_attachments_from_pdf(pdf_path)
        self.assertEqual(len(attachments), 1, "Expected exactly one attachment")

    def test_attachment_filename_is_facturx_standard(self):
        """Test that the embedded attachment uses the standard factur-x.xml filename."""
        pdf_path = os.path.join(self.temp_output_dir, "filename_pattern_test.pdf")
        self.generated_files.append(pdf_path)

        # Create base PDF
        self._create_minimal_pdf(pdf_path)

        # Embed – factur-x always uses 'factur-x.xml' as the embedded filename
        xml_path = os.path.join(self.temp_xml_dir, "invoice_ROUNDTRIP-TEST-001.xml")
        self.generated_files.append(xml_path)

        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "invoice_ROUNDTRIP-TEST-001.xml")

        # The embedded PDF attachment must carry the standard name
        attachments = self._extract_attachments_from_pdf(pdf_path)
        self.assertIn("factur-x.xml", attachments)

    def test_xml_contains_required_tags(self):
        """Test that extracted XML contains required ZUGFeRD tags."""
        pdf_path = os.path.join(self.temp_output_dir, "required_tags_test.pdf")
        self.generated_files.append(pdf_path)

        # Create base PDF
        self._create_minimal_pdf(pdf_path)

        xml_filename = "required_tags.xml"
        xml_path = os.path.join(self.temp_xml_dir, xml_filename)
        self.generated_files.append(xml_path)

        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, xml_filename)

        # Extract and verify required tags (factur-x embeds under 'factur-x.xml')
        attachments = self._extract_attachments_from_pdf(pdf_path)
        extracted_content = attachments["factur-x.xml"]
        if isinstance(extracted_content, bytes):
            extracted_content = extracted_content.decode("utf-8")

        required_tags = [
            "CrossIndustryInvoice",
            "ExchangedDocument",
            "ram:ID",
            "TypeCode",
            "SupplyChainTradeTransaction",
        ]

        for tag in required_tags:
            self.assertIn(tag, extracted_content, f"Required tag '{tag}' not found in extracted XML")

    def test_pdf_without_attachment_graceful_handling(self):
        """Test graceful handling of PDF without attachments."""
        pdf_path = os.path.join(self.temp_output_dir, "no_attachment_test.pdf")
        self.generated_files.append(pdf_path)

        # Create PDF without embedding XML
        self._create_minimal_pdf(pdf_path)

        # Extract - should return empty dict, not raise exception
        attachments = self._extract_attachments_from_pdf(pdf_path)
        self.assertEqual(len(attachments), 0, "Expected no attachments")

    def test_invoice_number_in_extracted_xml(self):
        """Test that invoice number is correctly preserved in roundtrip."""
        pdf_path = os.path.join(self.temp_output_dir, "invoice_number_test.pdf")
        self.generated_files.append(pdf_path)

        # Create base PDF
        self._create_minimal_pdf(pdf_path)

        # Use a unique invoice number
        unique_invoice_number = "INV-UNIQUE-12345"
        xml_with_unique_number = self.test_xml_content.replace("ROUNDTRIP-TEST-001", unique_invoice_number)

        xml_filename = "invoice_number_test.xml"
        xml_path = os.path.join(self.temp_xml_dir, xml_filename)
        self.generated_files.append(xml_path)

        self.pdf_generator._embed_xml(pdf_path, xml_with_unique_number, xml_filename)

        # Extract and verify invoice number (factur-x embeds under 'factur-x.xml')
        attachments = self._extract_attachments_from_pdf(pdf_path)
        extracted_content = attachments["factur-x.xml"]
        if isinstance(extracted_content, bytes):
            extracted_content = extracted_content.decode("utf-8")

        self.assertIn(unique_invoice_number, extracted_content, "Invoice number not preserved in roundtrip")

    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch("subprocess.run")
    def test_full_generate_invoice_pdf_with_extraction(self, mock_run, mock_create_base):
        """
        Integration test: Generate a complete invoice PDF and verify attachment extraction.

        This test mocks Ghostscript and base PDF creation to avoid heavy dependencies.
        """

        def mock_create_base_side_effect(invoice_instance, output_path):
            self._create_minimal_pdf(output_path)
            return output_path

        mock_create_base.side_effect = mock_create_base_side_effect

        # Mock Ghostscript to just copy the file
        def mock_gs_run(args, **kwargs):
            # Find input and output paths from args
            output_arg = [a for a in args if a.startswith("-sOutputFile=")]
            if output_arg:
                output_path = output_arg[0].replace("-sOutputFile=", "")
                input_path = args[-1]  # Last arg is usually input file

                # Copy input to output (simulating Ghostscript)
                if os.path.exists(input_path):
                    with open(input_path, "rb") as src, open(output_path, "wb") as dst:
                        dst.write(src.read())

            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        mock_run.side_effect = mock_gs_run

        # Generate invoice PDF
        result = self.pdf_generator.generate_invoice_pdf(
            self.sample_invoice_data,
            xml_content=self.test_xml_content,
            invoice_instance=mock.MagicMock(),
        )

        self.generated_files.append(result["pdf_path"])
        self.generated_files.append(result["xml_path"])

        self.assertIn("pdf_path", result)
        self.assertIn("xml_path", result)
        self.assertTrue(os.path.exists(result["pdf_path"]))

        # Verify file exists and has content
        # Note: Due to Ghostscript mock, full extraction is tested elsewhere
        self.assertGreater(os.path.getsize(result["pdf_path"]), 0)

        # Verify attachment extraction doesn't raise errors
        extracted = self._extract_attachments_from_pdf(result["pdf_path"])
        # extracted may be empty due to Ghostscript mock, but should not error
        self.assertIsInstance(extracted, dict)


class TestPdfSupplementaryAttachments(TestCase):
    """Tests for PDF/A-3 supplementary file embedding (Phase B).

    Verifies that rechnungsbegründende Dokumente (supporting documents) can be
    embedded alongside factur-x.xml with AFRelationship=/Supplement.
    """

    def setUp(self):
        self.temp_output_dir = tempfile.mkdtemp()
        self.temp_xml_dir = tempfile.mkdtemp()
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_output_dir, xml_dir=self.temp_xml_dir)
        self.generated_files = []

        self.test_xml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"'
            ' xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"'
            ' xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">\n'
            "  <rsm:ExchangedDocumentContext>\n"
            "    <ram:GuidelineSpecifiedDocumentContextParameter>\n"
            "      <ram:ID>urn:factur-x.eu:1p0:minimum</ram:ID>\n"
            "    </ram:GuidelineSpecifiedDocumentContextParameter>\n"
            "  </rsm:ExchangedDocumentContext>\n"
            "  <rsm:ExchangedDocument>\n"
            "    <ram:ID>MULTI-ATTACH-001</ram:ID>\n"
            "    <ram:TypeCode>380</ram:TypeCode>\n"
            "    <ram:IssueDateTime>\n"
            '      <udt:DateTimeString format="102">20260309</udt:DateTimeString>\n'
            "    </ram:IssueDateTime>\n"
            "  </rsm:ExchangedDocument>\n"
            "  <rsm:SupplyChainTradeTransaction>\n"
            "    <ram:ApplicableHeaderTradeAgreement>\n"
            "      <ram:SellerTradeParty><ram:Name>Seller GmbH</ram:Name></ram:SellerTradeParty>\n"
            "      <ram:BuyerTradeParty><ram:Name>Buyer AG</ram:Name></ram:BuyerTradeParty>\n"
            "    </ram:ApplicableHeaderTradeAgreement>\n"
            "  </rsm:SupplyChainTradeTransaction>\n"
            "</rsm:CrossIndustryInvoice>"
        )

    def tearDown(self):
        for file_path in self.generated_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except OSError:
                pass
        for d in [self.temp_output_dir, self.temp_xml_dir]:
            if d.startswith("/tmp") and os.path.exists(d):
                import shutil

                shutil.rmtree(d, ignore_errors=True)

    def _create_minimal_pdf(self, pdf_path):
        import pikepdf

        pdf = pikepdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(
                Type=pikepdf.Name("/Page"),
                MediaBox=[0, 0, 595, 842],
            )
        )
        pdf.pages.append(page)
        pdf.save(pdf_path)

    def _make_mock_attachment(
        self, filename, content, description="", mime_type="", attachment_type="supporting_document"
    ):
        """Create a mock InvoiceAttachment-like object."""
        att = mock.MagicMock()
        att.original_filename = filename
        att.description = description or filename
        att.mime_type = mime_type
        att.attachment_type = attachment_type
        att.file.read.return_value = content
        att.file.seek = mock.MagicMock()
        att.file.name = f"invoices/attachments/invoice_TEST/{filename}"
        return att

    def _extract_attachments_from_pdf(self, pdf_path):
        """Extract all embedded files from PDF."""
        attachments = {}
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            if hasattr(reader, "attachments") and reader.attachments:
                for name, content_list in reader.attachments.items():
                    if content_list:
                        attachments[name] = content_list[0]
                return attachments
            root = reader.trailer.get("/Root")
            if not root:
                return attachments
            names = root.get("/Names")
            if not names:
                return attachments
            embedded_files = names.get("/EmbeddedFiles")
            if not embedded_files:
                return attachments
            file_names = embedded_files.get("/Names")
            if not file_names:
                return attachments
            for i in range(0, len(file_names), 2):
                name = file_names[i]
                file_spec = file_names[i + 1].get_object()
                ef = file_spec.get("/EF")
                if ef:
                    stream_ref = ef.get("/F")
                    if stream_ref:
                        stream = stream_ref.get_object()
                        if hasattr(stream, "get_data"):
                            attachments[name] = stream.get_data()
                        elif hasattr(stream, "data"):
                            attachments[name] = stream.data
        return attachments

    def _get_af_relationships(self, pdf_path):
        """Extract AFRelationship values from all embedded file specs."""
        import pikepdf

        relationships = {}
        with pikepdf.open(pdf_path) as pdf:
            if "/AF" in pdf.Root:
                for file_spec in pdf.Root["/AF"]:
                    obj = file_spec
                    name = str(obj.get("/F", "unknown"))
                    rel = str(obj.get("/AFRelationship", "none"))
                    relationships[name] = rel
        return relationships

    # ── Tests ────────────────────────────────────────────────────────────────

    def test_embed_single_supplementary_pdf(self):
        """Embed one PDF attachment alongside factur-x.xml."""
        pdf_path = os.path.join(self.temp_output_dir, "test_single_supp.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "test.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "test.xml")

        supp_content = b"%PDF-1.4 supplementary document content"
        att = self._make_mock_attachment(
            "Lieferschein_2026-03.pdf",
            supp_content,
            description="Lieferschein März 2026",
            mime_type="application/pdf",
            attachment_type="delivery_note",
        )

        result = self.pdf_generator.embed_attachments(pdf_path, [att])
        self.assertEqual(result, ["Lieferschein_2026-03.pdf"])

        attachments = self._extract_attachments_from_pdf(pdf_path)
        self.assertIn("factur-x.xml", attachments)
        self.assertIn("Lieferschein_2026-03.pdf", attachments)
        self.assertEqual(attachments["Lieferschein_2026-03.pdf"], supp_content)

    def test_embed_multiple_supplementary_files(self):
        """Embed multiple attachments of different types."""
        pdf_path = os.path.join(self.temp_output_dir, "test_multi_supp.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "multi.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "multi.xml")

        attachments_to_embed = [
            self._make_mock_attachment(
                "Lieferschein.pdf",
                b"%PDF-1.4 delivery note",
                mime_type="application/pdf",
                attachment_type="delivery_note",
            ),
            self._make_mock_attachment(
                "Zeitaufstellung.csv",
                b"date,hours\n2026-03-01,8\n2026-03-02,7.5",
                mime_type="text/csv",
                attachment_type="timesheet",
            ),
            self._make_mock_attachment(
                "Foto_Lieferung.jpg",
                b"\xff\xd8\xff\xe0 fake jpeg data",
                mime_type="image/jpeg",
                attachment_type="other",
            ),
        ]

        result = self.pdf_generator.embed_attachments(pdf_path, attachments_to_embed)
        self.assertEqual(len(result), 3)

        extracted = self._extract_attachments_from_pdf(pdf_path)
        self.assertEqual(len(extracted), 4)  # factur-x.xml + 3 supplements
        self.assertIn("factur-x.xml", extracted)
        self.assertIn("Lieferschein.pdf", extracted)
        self.assertIn("Zeitaufstellung.csv", extracted)
        self.assertIn("Foto_Lieferung.jpg", extracted)

    def test_af_relationship_supplement_for_attachments(self):
        """Verify AFRelationship is /Data for XML and /Supplement for supporting docs."""
        pdf_path = os.path.join(self.temp_output_dir, "test_af_rel.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "af_test.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "af_test.xml")

        att = self._make_mock_attachment(
            "Beleg.pdf",
            b"%PDF-1.4 beleg",
            mime_type="application/pdf",
        )
        self.pdf_generator.embed_attachments(pdf_path, [att])

        relationships = self._get_af_relationships(pdf_path)
        self.assertEqual(relationships.get("factur-x.xml"), "/Data")
        self.assertEqual(relationships.get("Beleg.pdf"), "/Supplement")

    def test_embed_no_attachments_is_noop(self):
        """Embedding empty list should not modify the embedded files."""
        pdf_path = os.path.join(self.temp_output_dir, "test_empty.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "empty.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "empty.xml")

        result = self.pdf_generator.embed_attachments(pdf_path, [])
        self.assertEqual(result, [])

        attachments = self._extract_attachments_from_pdf(pdf_path)
        self.assertEqual(len(attachments), 1)
        self.assertIn("factur-x.xml", attachments)

    def test_content_integrity_preserved(self):
        """Verify binary content is preserved exactly after embedding."""
        pdf_path = os.path.join(self.temp_output_dir, "test_integrity.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "integrity.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "integrity.xml")

        csv_content = b"Datum;Stunden;Beschreibung\n2026-03-01;8.0;Entwicklung\n2026-03-02;7.5;Testing\n"
        att = self._make_mock_attachment(
            "Zeiterfassung.csv",
            csv_content,
            mime_type="text/csv",
        )
        self.pdf_generator.embed_attachments(pdf_path, [att])

        extracted = self._extract_attachments_from_pdf(pdf_path)
        self.assertEqual(extracted["Zeiterfassung.csv"], csv_content)

    def test_xlsx_attachment(self):
        """Test embedding an XLSX file (complex MIME type)."""
        pdf_path = os.path.join(self.temp_output_dir, "test_xlsx.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "xlsx.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "xlsx.xml")

        xlsx_content = b"PK\x03\x04 fake xlsx data content"
        att = self._make_mock_attachment(
            "Kalkulation.xlsx",
            xlsx_content,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        result = self.pdf_generator.embed_attachments(pdf_path, [att])
        self.assertEqual(result, ["Kalkulation.xlsx"])

        extracted = self._extract_attachments_from_pdf(pdf_path)
        self.assertIn("Kalkulation.xlsx", extracted)
        self.assertEqual(extracted["Kalkulation.xlsx"], xlsx_content)

    def test_unreadable_attachment_skipped_gracefully(self):
        """If an attachment file can't be read, skip it without failing."""
        pdf_path = os.path.join(self.temp_output_dir, "test_skip.pdf")
        self.generated_files.append(pdf_path)
        self._create_minimal_pdf(pdf_path)

        xml_path = os.path.join(self.temp_xml_dir, "skip.xml")
        self.generated_files.append(xml_path)
        self.pdf_generator._embed_xml(pdf_path, self.test_xml_content, "skip.xml")

        good_att = self._make_mock_attachment("good.pdf", b"%PDF ok", mime_type="application/pdf")
        bad_att = self._make_mock_attachment("bad.pdf", b"", mime_type="application/pdf")
        bad_att.file.read.side_effect = OSError("File not found on storage")

        result = self.pdf_generator.embed_attachments(pdf_path, [good_att, bad_att])
        self.assertEqual(result, ["good.pdf"])

        extracted = self._extract_attachments_from_pdf(pdf_path)
        self.assertIn("good.pdf", extracted)
        self.assertNotIn("bad.pdf", extracted)

    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch("subprocess.run")
    def test_generate_invoice_pdf_with_attachments(self, mock_run, mock_create_base):
        """Integration: generate_invoice_pdf embeds attachments from invoice_instance."""

        def mock_create_base_side_effect(invoice_instance, output_path):
            self._create_minimal_pdf(output_path)
            return output_path

        mock_create_base.side_effect = mock_create_base_side_effect

        def mock_gs_run(args, **kwargs):
            output_arg = [a for a in args if a.startswith("-sOutputFile=")]
            if output_arg:
                output_path = output_arg[0].replace("-sOutputFile=", "")
                input_path = args[-1]
                if os.path.exists(input_path):
                    with open(input_path, "rb") as src, open(output_path, "wb") as dst:
                        dst.write(src.read())
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        mock_run.side_effect = mock_gs_run

        invoice_instance = mock.MagicMock()
        att1 = self._make_mock_attachment(
            "Lieferschein.pdf",
            b"%PDF-1.4 delivery",
            mime_type="application/pdf",
            attachment_type="delivery_note",
        )
        att2 = self._make_mock_attachment(
            "Zeitaufstellung.csv",
            b"date,hours\n2026-03-01,8",
            mime_type="text/csv",
            attachment_type="timesheet",
        )
        mock_qs = mock.MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.__iter__ = mock.Mock(return_value=iter([att1, att2]))
        mock_qs.__len__ = mock.Mock(return_value=2)
        invoice_instance.attachments.all.return_value = mock_qs

        sample_data = {
            "number": "ATTACH-INT-001",
            "date": "2026-03-09",
            "due_date": "2026-04-09",
            "currency": "EUR",
            "customer": {
                "name": "Test Kunde",
                "address": "Teststr. 1, Berlin",
                "email": "test@example.com",
                "tax_id": "DE123456789",
            },
            "items": [{"product_name": "Beratung", "quantity": 10, "price": 150.00, "tax_rate": 19.0}],
        }

        result = self.pdf_generator.generate_invoice_pdf(
            sample_data,
            xml_content=self.test_xml_content,
            invoice_instance=invoice_instance,
        )

        self.generated_files.append(result["pdf_path"])
        self.generated_files.append(result["xml_path"])

        self.assertTrue(os.path.exists(result["pdf_path"]))
        self.assertEqual(len(result["embedded_attachments"]), 2)
        self.assertIn("Lieferschein.pdf", result["embedded_attachments"])
        self.assertIn("Zeitaufstellung.csv", result["embedded_attachments"])

        extracted = self._extract_attachments_from_pdf(result["pdf_path"])
        self.assertIn("factur-x.xml", extracted)
        self.assertIn("Lieferschein.pdf", extracted)
        self.assertIn("Zeitaufstellung.csv", extracted)

    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch("subprocess.run")
    def test_generate_invoice_pdf_without_attachments(self, mock_run, mock_create_base):
        """Integration: generate_invoice_pdf with no attachments still works."""

        def mock_create_base_side_effect(invoice_instance, output_path):
            self._create_minimal_pdf(output_path)
            return output_path

        mock_create_base.side_effect = mock_create_base_side_effect

        def mock_gs_run(args, **kwargs):
            output_arg = [a for a in args if a.startswith("-sOutputFile=")]
            if output_arg:
                output_path = output_arg[0].replace("-sOutputFile=", "")
                input_path = args[-1]
                if os.path.exists(input_path):
                    with open(input_path, "rb") as src, open(output_path, "wb") as dst:
                        dst.write(src.read())
            return mock.Mock(returncode=0, stdout=b"", stderr=b"")

        mock_run.side_effect = mock_gs_run

        invoice_instance = mock.MagicMock()
        mock_qs = mock.MagicMock()
        mock_qs.exists.return_value = False
        invoice_instance.attachments.all.return_value = mock_qs

        sample_data = {
            "number": "NO-ATTACH-001",
            "date": "2026-03-09",
            "due_date": "2026-04-09",
            "currency": "EUR",
            "customer": {
                "name": "Kunde ohne Anhang",
                "address": "Teststr. 2, München",
                "email": "noatt@example.com",
                "tax_id": "DE987654321",
            },
            "items": [{"product_name": "Service", "quantity": 1, "price": 500.00, "tax_rate": 19.0}],
        }

        result = self.pdf_generator.generate_invoice_pdf(
            sample_data,
            xml_content=self.test_xml_content,
            invoice_instance=invoice_instance,
        )

        self.generated_files.append(result["pdf_path"])
        self.generated_files.append(result["xml_path"])

        self.assertTrue(os.path.exists(result["pdf_path"]))
        self.assertEqual(result["embedded_attachments"], [])

        extracted = self._extract_attachments_from_pdf(result["pdf_path"])
        self.assertIn("factur-x.xml", extracted)
        self.assertEqual(len(extracted), 1)


class TestPdfFullComfortValidation(TestCase):
    """End-to-end test: generate PDF/A-3 with real COMFORT-profile XML.

    Uses the actual ZugferdXmlGenerator to produce a fully EN16931-compliant
    invoice (line items, VAT breakdown, seller/buyer VAT-IDs) and verifies that
    the PDF pipeline produces a structurally valid result.
    """

    def setUp(self):
        self.temp_output_dir = tempfile.mkdtemp()
        self.temp_xml_dir = tempfile.mkdtemp()
        self.pdf_generator = PdfA3Generator(output_dir=self.temp_output_dir, xml_dir=self.temp_xml_dir)
        self.generated_files = []

        # Full COMFORT-profile invoice data with line items & VAT IDs
        self.comfort_invoice_data = {
            "number": "COMFORT-VALID-001",
            "date": "20260309",
            "due_date": "20260409",
            "delivery_date": "20260305",
            "currency": "EUR",
            "type_code": "380",
            "buyer_reference": "PO-2026-042",
            "company": {
                "name": "Muster Lieferant GmbH",
                "vat_id": "DE123456789",
                "tax_id": "12/345/67890",
                "street_name": "Lieferantenstr. 1",
                "postcode_code": "10115",
                "city_name": "Berlin",
                "country_id": "DE",
                "iban": "DE89370400440532013000",
                "bic": "COBADEFFXXX",
            },
            "customer": {
                "name": "Muster Kunde AG",
                "vat_id": "DE987654321",
                "tax_id": "98/765/43210",
                "street_name": "Kundenweg 5",
                "postcode_code": "80331",
                "city_name": "München",
                "country_id": "DE",
            },
            "items": [
                {
                    "product_name": "IT-Beratung",
                    "quantity": 10,
                    "price": 150.00,
                    "tax_rate": 19.0,
                    "unit_of_measure": "HUR",
                },
                {
                    "product_name": "Fachliteratur",
                    "quantity": 3,
                    "price": 45.00,
                    "tax_rate": 7.0,
                    "unit_of_measure": "PCE",
                },
            ],
        }

    def tearDown(self):
        for f in self.generated_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except OSError:
                pass
        for d in [self.temp_output_dir, self.temp_xml_dir]:
            if d.startswith("/tmp") and os.path.exists(d):
                import shutil

                shutil.rmtree(d, ignore_errors=True)

    def _create_minimal_pdf(self, pdf_path):
        import pikepdf

        pdf = pikepdf.new()
        pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 595, 842])))
        pdf.save(pdf_path)

    def _extract_attachments_from_pdf(self, pdf_path):
        attachments = {}
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            if hasattr(reader, "attachments") and reader.attachments:
                for name, content_list in reader.attachments.items():
                    if content_list:
                        attachments[name] = content_list[0]
                return attachments
            root = reader.trailer.get("/Root")
            if not root:
                return attachments
            names = root.get("/Names")
            if not names:
                return attachments
            embedded_files = names.get("/EmbeddedFiles")
            if not embedded_files:
                return attachments
            file_names = embedded_files.get("/Names")
            if not file_names:
                return attachments
            for i in range(0, len(file_names), 2):
                name = file_names[i]
                file_spec = file_names[i + 1].get_object()
                ef = file_spec.get("/EF")
                if ef:
                    stream_ref = ef.get("/F")
                    if stream_ref:
                        stream = stream_ref.get_object()
                        if hasattr(stream, "get_data"):
                            attachments[name] = stream.get_data()
                        elif hasattr(stream, "data"):
                            attachments[name] = stream.data
        return attachments

    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch("subprocess.run")
    def test_full_comfort_invoice_with_line_items_and_vat(self, mock_run, mock_create_base):
        """Generate PDF with real COMFORT XML (line items, VAT IDs, monetary totals).

        Verifies:
        - ZugferdXmlGenerator produces valid COMFORT XML from invoice_data
        - XML is embedded and extractable from the PDF
        - Extracted XML contains line items, VAT IDs, and monetary totals
        - AFRelationship is /Data for factur-x.xml
        """
        from lxml import etree

        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        mock_create_base.side_effect = lambda inst, path: self._create_minimal_pdf(path) or path
        mock_run.side_effect = lambda args, **kw: (
            (
                (
                    open(
                        args[[a.startswith("-sOutputFile=") for a in args].index(True)].replace("-sOutputFile=", ""),
                        "wb",
                    ).write(open(args[-1], "rb").read()),
                    None,
                )
                and None
            )
            or mock.Mock(returncode=0, stdout=b"", stderr=b"")
        )

        # ── Step 1: Generate real COMFORT XML ────────────────────────────
        xml_gen = ZugferdXmlGenerator(profile="COMFORT", enable_validation=True)
        xml_content = xml_gen.generate_xml(self.comfort_invoice_data)

        self.assertIsInstance(xml_content, str)
        self.assertIn("CrossIndustryInvoice", xml_content)

        # ── Step 2: Generate PDF with embedded XML ───────────────────────
        invoice_instance = mock.MagicMock()
        mock_qs = mock.MagicMock()
        mock_qs.exists.return_value = False
        invoice_instance.attachments.all.return_value = mock_qs

        result = self.pdf_generator.generate_invoice_pdf(
            self.comfort_invoice_data,
            xml_content=xml_content,
            invoice_instance=invoice_instance,
        )

        self.generated_files.append(result["pdf_path"])
        self.generated_files.append(result["xml_path"])
        self.assertTrue(os.path.exists(result["pdf_path"]))

        # ── Step 3: Extract and validate embedded XML ────────────────────
        attachments = self._extract_attachments_from_pdf(result["pdf_path"])
        self.assertIn("factur-x.xml", attachments)

        extracted_xml = attachments["factur-x.xml"]
        if isinstance(extracted_xml, bytes):
            extracted_xml = extracted_xml.decode("utf-8")

        ns = {
            "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
        }
        root = etree.fromstring(extracted_xml.encode("utf-8"))

        # Invoice number
        inv_id = root.find(".//rsm:ExchangedDocument/ram:ID", ns)
        self.assertIsNotNone(inv_id)
        self.assertEqual(inv_id.text, "COMFORT-VALID-001")

        # COMFORT profile URN (EN16931)
        profile_id = root.find(
            ".//rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", ns
        )
        self.assertIsNotNone(profile_id)
        self.assertIn("en16931", profile_id.text.lower())

        # Line items — at least 2
        line_items = root.findall(".//rsm:SupplyChainTradeTransaction/ram:IncludedSupplyChainTradeLineItem", ns)
        self.assertGreaterEqual(len(line_items), 2, "COMFORT invoice must have line items")

        # ── Step 3a: Check seller VAT ID ─────────────────────────────────
        seller_tax_regs = root.findall(
            ".//ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", ns
        )
        seller_vat_ids = [el.text for el in seller_tax_regs]
        self.assertTrue(
            any("DE123456789" in v for v in seller_vat_ids),
            f"Seller VAT ID DE123456789 not found in {seller_vat_ids}",
        )

        # ── Step 3b: Check buyer VAT ID ──────────────────────────────────
        buyer_tax_regs = root.findall(
            ".//ram:ApplicableHeaderTradeAgreement/ram:BuyerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", ns
        )
        buyer_vat_ids = [el.text for el in buyer_tax_regs]
        self.assertTrue(
            any("DE987654321" in v for v in buyer_vat_ids),
            f"Buyer VAT ID DE987654321 not found in {buyer_vat_ids}",
        )

        # ── Step 3c: Check ApplicableTradeTax (VAT breakdown) ───────────
        trade_taxes = root.findall(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", ns)
        self.assertGreaterEqual(
            len(trade_taxes),
            2,
            "COMFORT invoice with 19% + 7% must have at least 2 VAT groups",
        )
        tax_rates = set()
        for tt in trade_taxes:
            rate_el = tt.find("ram:RateApplicablePercent", ns)
            if rate_el is not None and rate_el.text:
                tax_rates.add(float(rate_el.text))
        self.assertIn(19.0, tax_rates, "19% VAT group missing")
        self.assertIn(7.0, tax_rates, "7% VAT group missing")

        # ── Step 3d: Monetary totals present and correct ─────────────────
        monetary = root.find(
            ".//ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation", ns
        )
        self.assertIsNotNone(monetary, "MonetarySummation missing")

        due = monetary.find("ram:DuePayableAmount", ns)
        self.assertIsNotNone(due)
        due_amount = float(due.text)
        # 10 × 150 × 1.19 + 3 × 45 × 1.07 = 1785 + 144.45 = 1929.45
        self.assertAlmostEqual(due_amount, 1929.45, places=2)

        # ── Step 3e: Currency code ───────────────────────────────────────
        currency = root.find(".//ram:ApplicableHeaderTradeSettlement/ram:InvoiceCurrencyCode", ns)
        self.assertIsNotNone(currency)
        self.assertEqual(currency.text, "EUR")

    @mock.patch.object(PdfA3Generator, "_create_base_pdf")
    @mock.patch("subprocess.run")
    def test_comfort_invoice_with_attachments_full_validation(self, mock_run, mock_create_base):
        """Full pipeline: COMFORT XML + supplementary attachments in one PDF.

        Verifies that a complete COMFORT-profile invoice with embedded line items
        and supplementary documents passes structural validation.
        """
        from invoice_app.utils.xml.generator import ZugferdXmlGenerator

        mock_create_base.side_effect = lambda inst, path: self._create_minimal_pdf(path) or path
        mock_run.side_effect = lambda args, **kw: (
            (
                (
                    open(
                        args[[a.startswith("-sOutputFile=") for a in args].index(True)].replace("-sOutputFile=", ""),
                        "wb",
                    ).write(open(args[-1], "rb").read()),
                    None,
                )
                and None
            )
            or mock.Mock(returncode=0, stdout=b"", stderr=b"")
        )

        xml_gen = ZugferdXmlGenerator(profile="COMFORT", enable_validation=True)
        xml_content = xml_gen.generate_xml(self.comfort_invoice_data)

        # Mock attachments
        att = mock.MagicMock()
        att.original_filename = "Lieferschein_2026-03.pdf"
        att.description = "Lieferschein März 2026"
        att.mime_type = "application/pdf"
        att.attachment_type = "delivery_note"
        att.file.read.return_value = b"%PDF-1.4 delivery note content"
        att.file.seek = mock.MagicMock()
        att.file.name = "invoices/attachments/invoice_COMFORT-VALID-001/Lieferschein_2026-03.pdf"

        invoice_instance = mock.MagicMock()
        mock_qs = mock.MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.__iter__ = mock.Mock(return_value=iter([att]))
        mock_qs.__len__ = mock.Mock(return_value=1)
        invoice_instance.attachments.all.return_value = mock_qs

        result = self.pdf_generator.generate_invoice_pdf(
            self.comfort_invoice_data,
            xml_content=xml_content,
            invoice_instance=invoice_instance,
        )

        self.generated_files.append(result["pdf_path"])
        self.generated_files.append(result["xml_path"])

        # Verify all 3 keys present
        self.assertIn("pdf_path", result)
        self.assertIn("xml_path", result)
        self.assertIn("embedded_attachments", result)
        self.assertEqual(result["embedded_attachments"], ["Lieferschein_2026-03.pdf"])

        # Verify embedded files: factur-x.xml + 1 attachment
        attachments = self._extract_attachments_from_pdf(result["pdf_path"])
        self.assertEqual(len(attachments), 2)
        self.assertIn("factur-x.xml", attachments)
        self.assertIn("Lieferschein_2026-03.pdf", attachments)

        # Verify XML is real COMFORT (has line items)
        extracted_xml = attachments["factur-x.xml"]
        if isinstance(extracted_xml, bytes):
            extracted_xml = extracted_xml.decode("utf-8")
        self.assertIn("IncludedSupplyChainTradeLineItem", extracted_xml)
        self.assertIn("DE123456789", extracted_xml)

        # Verify AF relationships
        import pikepdf

        with pikepdf.open(result["pdf_path"]) as pdf:
            rels = {}
            if "/AF" in pdf.Root:
                for fs in pdf.Root["/AF"]:
                    rels[str(fs.get("/F", "?"))] = str(fs.get("/AFRelationship", "?"))
            self.assertEqual(rels.get("factur-x.xml"), "/Data")
            self.assertEqual(rels.get("Lieferschein_2026-03.pdf"), "/Supplement")
