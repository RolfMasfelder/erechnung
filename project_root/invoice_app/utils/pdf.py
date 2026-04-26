"""PDF/A-3 generation utilities with XML embedding (WeasyPrint + Ghostscript + pikepdf).

Pipeline:
 1. WeasyPrint  → Basis-PDF aus invoice_pdf.html Template
 2. Ghostscript → PDF/A-3 Konvertierung (setzt XMP pdfaid:part=3/B und OutputIntent)
 3. pikepdf     → XML-Einbettung (preserviert die PDF/A-3 XMP-Metadaten)

Hinweis: factur-x ≥ 3.x nutzt pypdf als Backend, das alle von Ghostscript gesetzten
         PDF/A-3-Metadaten (XMP pdfaid:part, pdfaid:conformance, OutputIntent) beim
         Neu-Schreiben verliert. Deshalb wird pikepdf direkt verwendet, das die
         bestehende PDF-Struktur vollständig erhält.
"""

from __future__ import annotations  # noqa: I001

import logging
import os
import subprocess
import uuid
from datetime import datetime

import pikepdf
import weasyprint
from django.conf import settings
from django.template.loader import render_to_string

from .xml import ZugferdXmlGenerator

PDF_BACKEND = "pikepdf"  # factur-x 3.x uses pypdf (destroys PDF/A-3 XMP metadata); we use pikepdf directly


logger = logging.getLogger(__name__)


def _add_facturx_xmp(pdf, xml_filename: str, conformance: str = "COMFORT") -> None:
    """Fügt die Factur-X XMP-Schema-Extension in die bestehenden XMP-Metadaten ein.

    Ghostscript hat pdfaid:part=3 und pdfaid:conformance=B bereits gesetzt.
    Diese Funktion ergänzt:
    1. pdfaExtension:schemas – die Pflicht-Schema-Deklaration für eigene XMP-Namensräume
       (ohne die PDF/A-3-Validator akzeptiert keine benutzerdefinierten XMP-Properties)
    2. fx: Properties (DocumentType, DocumentFileName, Version, ConformanceLevel)

    Args:
        pdf: offenes pikepdf.Pdf-Objekt
        xml_filename: Name der eingebetteten XML-Datei (muss 'factur-x.xml' sein)
        conformance: ZUGFeRD/Factur-X Konformitätsstufe (default: 'COMFORT')
    """
    import re

    FX_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
    RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    PDFA_EXT_NS = "http://www.aiim.org/pdfa/ns/extension/"
    PDFA_SCHEMA_NS = "http://www.aiim.org/pdfa/ns/schema#"
    PDFA_PROP_NS = "http://www.aiim.org/pdfa/ns/property#"

    if "/Metadata" not in pdf.Root:
        logger.warning("_add_facturx_xmp: No /Metadata stream in PDF root – skipping XMP update")
        return

    try:
        existing_xmp = bytes(pdf.Root["/Metadata"].read_bytes()).decode("utf-8", errors="replace")

        # Bereits vorhandene fx:/nsX-Blöcke und pdfaExtension-Blöcke entfernen
        # (von einem vorherigen Einbettungsversuch), um Duplikate zu vermeiden
        existing_xmp = re.sub(
            r'<rdf:Description\b[^>]*xmlns:(?:fx|ns\d+)="urn:factur-x:[^"]*"[^>]*>.*?</rdf:Description>\s*',
            "",
            existing_xmp,
            flags=re.DOTALL,
        )
        existing_xmp = re.sub(
            r'<rdf:Description\b[^>]*xmlns:pdfaExtension="[^"]*"[^>]*>.*?</rdf:Description>\s*',
            "",
            existing_xmp,
            flags=re.DOTALL,
        )

        # pdfaExtension Schema-Deklaration für Factur-X (erforderlich für PDF/A-3)
        fx_schema_block = (
            f'<rdf:Description rdf:about=""\n'
            f'    xmlns:rdf="{RDF_NS}"\n'
            f'    xmlns:pdfaExtension="{PDFA_EXT_NS}"\n'
            f'    xmlns:pdfaSchema="{PDFA_SCHEMA_NS}"\n'
            f'    xmlns:pdfaProperty="{PDFA_PROP_NS}">\n'
            f"  <pdfaExtension:schemas>\n"
            f"    <rdf:Bag>\n"
            f'      <rdf:li rdf:parseType="Resource">\n'
            f"        <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>\n"
            f"        <pdfaSchema:namespaceURI>{FX_NS}</pdfaSchema:namespaceURI>\n"
            f"        <pdfaSchema:prefix>fx</pdfaSchema:prefix>\n"
            f"        <pdfaSchema:property>\n"
            f"          <rdf:Seq>\n"
            f'            <rdf:li rdf:parseType="Resource">\n'
            f"              <pdfaProperty:name>DocumentFileName</pdfaProperty:name>\n"
            f"              <pdfaProperty:valueType>Text</pdfaProperty:valueType>\n"
            f"              <pdfaProperty:category>external</pdfaProperty:category>\n"
            f"              <pdfaProperty:description>name of embedded XML invoice file</pdfaProperty:description>\n"
            f"            </rdf:li>\n"
            f'            <rdf:li rdf:parseType="Resource">\n'
            f"              <pdfaProperty:name>DocumentType</pdfaProperty:name>\n"
            f"              <pdfaProperty:valueType>Text</pdfaProperty:valueType>\n"
            f"              <pdfaProperty:category>external</pdfaProperty:category>\n"
            f"              <pdfaProperty:description>INVOICE</pdfaProperty:description>\n"
            f"            </rdf:li>\n"
            f'            <rdf:li rdf:parseType="Resource">\n'
            f"              <pdfaProperty:name>Version</pdfaProperty:name>\n"
            f"              <pdfaProperty:valueType>Text</pdfaProperty:valueType>\n"
            f"              <pdfaProperty:category>external</pdfaProperty:category>\n"
            f"              <pdfaProperty:description>Factur-X XML schema version</pdfaProperty:description>\n"
            f"            </rdf:li>\n"
            f'            <rdf:li rdf:parseType="Resource">\n'
            f"              <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>\n"
            f"              <pdfaProperty:valueType>Text</pdfaProperty:valueType>\n"
            f"              <pdfaProperty:category>external</pdfaProperty:category>\n"
            f"              <pdfaProperty:description>Factur-X conformance level</pdfaProperty:description>\n"
            f"            </rdf:li>\n"
            f"          </rdf:Seq>\n"
            f"        </pdfaSchema:property>\n"
            f"      </rdf:li>\n"
            f"    </rdf:Bag>\n"
            f"  </pdfaExtension:schemas>\n"
            f"</rdf:Description>\n"
            f'<rdf:Description rdf:about="" xmlns:fx="{FX_NS}">\n'
            f"  <fx:DocumentType>INVOICE</fx:DocumentType>\n"
            f"  <fx:DocumentFileName>{xml_filename}</fx:DocumentFileName>\n"
            f"  <fx:Version>1.0</fx:Version>\n"
            f"  <fx:ConformanceLevel>{conformance}</fx:ConformanceLevel>\n"
            f"</rdf:Description>"
        )

        updated_xmp = existing_xmp.replace("</rdf:RDF>", fx_schema_block + "\n</rdf:RDF>")

        new_meta = pikepdf.Stream(pdf, updated_xmp.encode("utf-8"))
        new_meta["/Type"] = pikepdf.Name("/Metadata")
        new_meta["/Subtype"] = pikepdf.Name("/XML")
        pdf.Root["/Metadata"] = new_meta
        logger.debug("Factur-X XMP extension added: %s / %s", xml_filename, conformance)

    except Exception as exc:
        logger.warning("_add_facturx_xmp failed (non-fatal, continuing): %s", exc)


class PdfA3Generator:
    """
    Class for generating PDF/A-3 documents with embedded XML files.

    This implementation uses:
    - WeasyPrint for creating the base PDF from an HTML template
    - Ghostscript for converting to PDF/A-3 format (sets XMP pdfaid metadata)
    - factur-x for embedding the ZUGFeRD/Factur-X XML (preserves PDF/A-3 metadata)
    """

    def __init__(self, output_dir=None, xml_dir=None):
        """
        Initialize the PDF/A-3 generator.

        Args:
            output_dir (str): Directory where PDF files will be saved
            xml_dir (str): Directory where XML files will be saved
        """
        self.output_dir = output_dir or settings.PDF_OUTPUT_DIR
        self.xml_dir = xml_dir or settings.XML_OUTPUT_DIR
        self.ghostscript_path = settings.GHOSTSCRIPT_PATH
        self.icc_profile_path = getattr(
            settings,
            "PDFA_RGB_ICC_PROFILE",
            "/usr/share/color/icc/ghostscript/srgb.icc",
        )

        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.xml_dir, exist_ok=True)

    def _format_date_german(self, date_str):
        """
        Convert date from YYYYMMDD format to German format (DD.MM.YYYY).

        Args:
            date_str (str): Date in YYYYMMDD format

        Returns:
            str: Date in DD.MM.YYYY format
        """
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{day}.{month}.{year}"
        except Exception:
            return date_str

    def _create_base_pdf(self, invoice_instance, output_path):
        """
        Create the base PDF using WeasyPrint and the invoice_pdf.html template.

        Args:
            invoice_instance: Django Invoice model instance
            output_path (str): Path where the PDF will be saved

        Returns:
            str: Path to the created PDF
        """
        # Render the Django template to HTML
        html_string = render_to_string(
            "invoice_app/invoice_pdf.html",
            {"invoice": invoice_instance},
        )

        # WeasyPrint cannot resolve Django's /media/... URLs directly.
        # Replace /media/ paths with absolute file:// URLs so WeasyPrint
        # can load logo images and other media assets from the filesystem.
        media_file_prefix = f"file://{settings.MEDIA_ROOT}/"
        html_string = html_string.replace('src="/media/', f'src="{media_file_prefix}').replace(
            "src='/media/", f"src='{media_file_prefix}"
        )

        weasyprint.HTML(
            string=html_string,
            base_url=f"file://{settings.BASE_DIR}/",
        ).write_pdf(output_path)

        logger.info(f"WeasyPrint rendered PDF: {output_path}")
        return output_path

    def _build_pdfa_def_ps(self, tmp_dir: str) -> str:
        """Write a temporary PDFA_def.ps prologue for Ghostscript.

        Reads Ghostscript's own PDFA_def.ps template and replaces the
        (srgb.icc) placeholder with the absolute ICC profile path so that
        Ghostscript can open the file and embed it as an OutputIntent.
        Without this, ISO 19005-3 §6.2.4.3 violations are raised for every
        DeviceRGB usage in the document.

        Returns:
            str: Path to the generated .ps file.
        """
        gs_template = "/usr/share/ghostscript/10.00.0/lib/PDFA_def.ps"
        with open(gs_template, encoding="utf-8") as f:
            ps_content = f.read()

        # Replace the (srgb.icc) placeholder with the absolute path to the
        # ICC profile so that GS can load it regardless of the working directory.
        ps_content = ps_content.replace("(srgb.icc)", f"({self.icc_profile_path})")

        ps_path = os.path.join(tmp_dir, "pdfa_def.ps")
        with open(ps_path, "w", encoding="utf-8") as f:
            f.write(ps_content)
        return ps_path

    def _convert_to_pdfa3(self, input_path, output_path):
        """
        Convert a PDF to PDF/A-3 format using Ghostscript.

        A temporary PDFA_def.ps prologue (derived from Ghostscript's own
        template) is generated on-the-fly to embed the sRGB ICC profile as an
        OutputIntent – required by ISO 19005-3 §6.2.4.3 when DeviceRGB colour
        spaces are used. ``--permit-file-read`` grants GS access to the profile.

        Args:
            input_path (str): Path to the input PDF
            output_path (str): Path where the PDF/A-3 will be saved

        Returns:
            str: Path to the created PDF/A-3 document
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdfa_def_ps = self._build_pdfa_def_ps(tmp_dir)

            gs_params = [
                self.ghostscript_path,
                "-dSAFER",  # Security: restrict file operations (Issue #5)
                "-dPDFA=3",
                "-dBATCH",
                "-dNOPAUSE",
                "-dNOOUTERSAVE",
                "-dPDFACompatibilityPolicy=1",
                "-sColorConversionStrategy=RGB",
                f"--permit-file-read={self.icc_profile_path}",
                f"--permit-file-read={pdfa_def_ps}",
                "-sDEVICE=pdfwrite",
                "-sOutputFile=" + output_path,
                "-dPDFSETTINGS=/prepress",
                pdfa_def_ps,  # PDFA_def.ps must come BEFORE the input PDF
                input_path,
            ]

            try:
                result = subprocess.run(
                    gs_params,
                    check=True,
                    capture_output=True,
                    timeout=60,  # Security: prevent runaway processes
                )

                # GS returns 0 but prints "aborted" if the ICC file was not readable.
                stdout = result.stdout.decode(errors="replace")
                if "PDF/A processing aborted" in stdout:
                    raise RuntimeError(
                        f"Ghostscript PDF/A processing aborted – ICC profile not readable: {self.icc_profile_path}"
                    )

                return output_path

            except subprocess.CalledProcessError as e:
                logger.error(f"Ghostscript process error: {e}")
                error_msg = e.stderr.decode() if e.stderr else "No error output"
                logger.error(f"Stderr: {error_msg}")
                raise RuntimeError(f"PDF/A-3 conversion failed: {e}") from e
            except subprocess.TimeoutExpired as e:
                logger.error("Ghostscript process timed out after 60s")
                raise RuntimeError("PDF/A-3 conversion timed out") from e
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error during PDF/A-3 conversion: {e}")
                raise

    def _embed_xml(self, pdf_path, xml_content, xml_filename=None, description=None):
        """Embed XML into a PDF/A-3 document using pikepdf directly.

        Verwendet pikepdf anstelle von factur-x, da factur-x ≥ 3.x pypdf als
        Backend nutzt, das alle von Ghostscript gesetzten PDF/A-3-Metadaten
        (XMP pdfaid:part=3, pdfaid:conformance=B, OutputIntent) zerstört.
        pikepdf erhält die bestehende PDF-Struktur vollständig.

        Implementiert den ZUGFeRD/Factur-X Anhang gemäß:
        - EN 16931 Annex: AF-Array, EmbeddedFiles-Namenstree, AFRelationship=/Data
        - Factur-X XMP schema extension (urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#)
        """
        import pikepdf
        from pikepdf import Array, Dictionary, Name, Stream

        # Der eingebettete Dateiname MUSS exakt 'factur-x.xml' sein (Factur-X Standard § 7).
        # xml_filename wird nur für die Disk-Kopie verwendet.
        disk_filename = xml_filename or f"factur-x_{uuid.uuid4().hex[:8]}.xml"
        embedded_filename = "factur-x.xml"  # Pflicht-Dateiname für ZUGFeRD/Factur-X
        description = description or "Factur-X/ZUGFeRD XML invoice data"
        xml_path = os.path.join(self.xml_dir, disk_filename)

        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content

        with open(xml_path, "wb") as f:
            f.write(xml_bytes)

        try:
            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                # 1. Embedded-File-Stream anlegen
                #    MIME type application/xml – verwendet pikepdf.Object.parse für korrekte
                #    PDF-Name-Kodierung (application#2Fxml) ohne #-Escaping-Dopplung
                ef_stream = Stream(pdf, xml_bytes)
                ef_stream["/Type"] = Name("/EmbeddedFile")
                ef_stream["/Subtype"] = pikepdf.Object.parse(b"/application#2Fxml")
                ef_stream["/Params"] = Dictionary(Size=len(xml_bytes))

                # 2. FileSpec-Dictionary anlegen
                # F und UF MÜSSEN "factur-x.xml" sein (nicht der Disk-Dateiname) –
                # Mustang und andere ZUGFeRD-Validatoren prüfen dieses Feld.
                file_spec = pdf.make_indirect(
                    Dictionary(
                        Type=Name("/Filespec"),
                        F=pikepdf.String(embedded_filename),
                        UF=pikepdf.String(embedded_filename),
                        Desc=pikepdf.String(description),
                        AFRelationship=Name("/Data"),
                        EF=Dictionary(F=ef_stream),
                    )
                )

                # 3. EmbeddedFiles-Namenstree im /Names-Dictionary des Root setzen
                if "/Names" not in pdf.Root:
                    pdf.Root["/Names"] = pdf.make_indirect(Dictionary())
                if "/EmbeddedFiles" not in pdf.Root["/Names"]:
                    pdf.Root["/Names"]["/EmbeddedFiles"] = Dictionary(
                        Names=Array([pikepdf.String(embedded_filename), file_spec])
                    )
                else:
                    names_node = pdf.Root["/Names"]["/EmbeddedFiles"]
                    if "/Names" in names_node:
                        names_node["/Names"].append(pikepdf.String(embedded_filename))
                        names_node["/Names"].append(file_spec)
                    else:
                        names_node["/Names"] = Array([pikepdf.String(embedded_filename), file_spec])

                # 4. AF-Array im Document-Catalog setzen (ISO 32000-2 §14.13)
                if "/AF" not in pdf.Root:
                    pdf.Root["/AF"] = Array([file_spec])
                else:
                    pdf.Root["/AF"].append(file_spec)

                # 5. XMP-Metadaten: Factur-X Schema-Extension hinzufügen
                #    (pdfaid:part=3 und pdfaid:conformance=B wurden von GS gesetzt;
                #     hier ergänzen wir die Factur-X-Namensraum-Erweiterung mittels lxml)
                _add_facturx_xmp(pdf, embedded_filename)

                pdf.save(pdf_path)

            size = os.path.getsize(pdf_path)
            logger.info(
                "Successfully embedded XML into PDF using pikepdf (PDF/A-3 metadata preserved): %s (size: %.1f KB)",
                pdf_path,
                size / 1024,
            )
            return pdf_path
        except Exception as e:  # noqa: BLE001 - broad to log any backend issue
            logger.error("Error embedding XML into PDF: %s", e)
            raise

    def embed_attachments(self, pdf_path, attachments):
        """Embed supplementary files (rechnungsbegründende Dokumente) into a PDF/A-3.

        Each attachment is embedded as a PDF/A-3 associated file with
        AFRelationship=/Supplement (ISO 32000-2 §14.13, ISO 19005-3 §6.8).
        The factur-x.xml must already be embedded (AFRelationship=/Data).

        Args:
            pdf_path: Path to the PDF/A-3 file (modified in-place).
            attachments: Iterable of InvoiceAttachment model instances.

        Returns:
            list[str]: Filenames of successfully embedded attachments.
        """
        import pikepdf
        from pikepdf import Array, Dictionary, Name, Stream

        attachment_list = list(attachments)
        if not attachment_list:
            return []

        # Map MIME types to PDF Name-encoded subtypes
        _mime_to_subtype = {
            "application/pdf": b"/application#2Fpdf",
            "image/png": b"/image#2Fpng",
            "image/jpeg": b"/image#2Fjpeg",
            "text/csv": b"/text#2Fcsv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
                b"/application#2Fvnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        }

        embedded_names = []

        try:
            with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
                for att in attachment_list:
                    try:
                        file_bytes = att.file.read()
                        att.file.seek(0)  # Reset for potential re-reads
                    except Exception as e:
                        logger.warning("Could not read attachment %s: %s", att.original_filename, e)
                        continue

                    filename = att.original_filename or os.path.basename(att.file.name)
                    mime = att.mime_type or "application/octet-stream"
                    subtype_bytes = _mime_to_subtype.get(mime, b"/application#2Foctet-stream")

                    # 1. EmbeddedFile stream
                    ef_stream = Stream(pdf, file_bytes)
                    ef_stream["/Type"] = Name("/EmbeddedFile")
                    ef_stream["/Subtype"] = pikepdf.Object.parse(subtype_bytes)
                    ef_stream["/Params"] = Dictionary(Size=len(file_bytes))

                    # 2. FileSpec dictionary — AFRelationship=/Supplement for supporting docs
                    file_spec = pdf.make_indirect(
                        Dictionary(
                            Type=Name("/Filespec"),
                            F=pikepdf.String(filename),
                            UF=pikepdf.String(filename),
                            Desc=pikepdf.String(att.description or filename),
                            AFRelationship=Name("/Supplement"),
                            EF=Dictionary(F=ef_stream),
                        )
                    )

                    # 3. Add to EmbeddedFiles name tree
                    if "/Names" not in pdf.Root:
                        pdf.Root["/Names"] = pdf.make_indirect(Dictionary())
                    if "/EmbeddedFiles" not in pdf.Root["/Names"]:
                        pdf.Root["/Names"]["/EmbeddedFiles"] = Dictionary(
                            Names=Array([pikepdf.String(filename), file_spec])
                        )
                    else:
                        names_node = pdf.Root["/Names"]["/EmbeddedFiles"]
                        if "/Names" in names_node:
                            names_node["/Names"].append(pikepdf.String(filename))
                            names_node["/Names"].append(file_spec)
                        else:
                            names_node["/Names"] = Array([pikepdf.String(filename), file_spec])

                    # 4. Add to AF array (Associated Files)
                    if "/AF" not in pdf.Root:
                        pdf.Root["/AF"] = Array([file_spec])
                    else:
                        pdf.Root["/AF"].append(file_spec)

                    embedded_names.append(filename)
                    logger.info("Embedded supplementary file: %s (%s, %d bytes)", filename, mime, len(file_bytes))

                pdf.save(pdf_path)

            if embedded_names:
                size = os.path.getsize(pdf_path)
                logger.info(
                    "Embedded %d supplementary files into PDF/A-3: %s (size: %.1f KB)",
                    len(embedded_names),
                    pdf_path,
                    size / 1024,
                )
        except Exception as e:  # noqa: BLE001
            logger.error("Error embedding attachments into PDF: %s", e)
            raise

        return embedded_names

    def generate_invoice_pdf(self, invoice_data, xml_content=None, invoice_instance=None):
        """
        Generate a complete PDF/A-3 invoice with embedded XML.

        Args:
            invoice_data (dict): Dictionary containing invoice data
            xml_content (str, optional): Custom XML content. If not provided,
                                       ZUGFeRD XML will be generated automatically
            invoice_instance: Django Invoice model instance (required for WeasyPrint rendering)

        Returns:
            dict: Dictionary containing paths to generated files:
                {
                    'pdf_path': str,
                    'xml_path': str
                }
        """
        invoice_number = invoice_data.get("number", str(uuid.uuid4().hex[:8]))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # Generate filenames
        base_filename = f"invoice_{invoice_number}_{timestamp}"
        temp_pdf_path = os.path.join(self.output_dir, f"{base_filename}_temp.pdf")
        final_pdf_path = os.path.join(self.output_dir, f"{base_filename}.pdf")
        xml_filename = f"{base_filename}.xml"
        xml_path = os.path.join(self.xml_dir, xml_filename)

        # Step 1: Create the base PDF using WeasyPrint + invoice_pdf.html template
        if invoice_instance is None:
            raise ValueError("invoice_instance is required for PDF generation with WeasyPrint")
        self._create_base_pdf(invoice_instance, temp_pdf_path)

        # Step 2: Convert to PDF/A-3
        self._convert_to_pdfa3(temp_pdf_path, final_pdf_path)

        # Remove temporary PDF
        try:
            os.remove(temp_pdf_path)
        except Exception as e:
            logger.warning(f"Could not remove temporary PDF file: {e}")

        # Step 3: Generate and embed XML
        # If no custom XML content is provided, generate ZUGFeRD XML automatically
        if xml_content is None:
            try:
                # Enable validation with our working schema files - use COMFORT profile for EN16931 compliance
                xml_generator = ZugferdXmlGenerator(profile="COMFORT", enable_validation=True)
                xml_content = xml_generator.generate_xml(invoice_data)
                logger.info(f"Generated ZUGFeRD XML for invoice {invoice_number}")
            except Exception as e:
                logger.error(f"Failed to generate ZUGFeRD XML: {e}")
                # Fallback: re-raise so callers see the real error
                raise

        # Save XML content
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # Embed XML into PDF
        self._embed_xml(final_pdf_path, xml_content, xml_filename)

        # Step 4: Embed supplementary attachments (rechnungsbegründende Dokumente)
        embedded_attachments = []
        if invoice_instance is not None:
            attachments = invoice_instance.attachments.all()
            if attachments.exists():
                embedded_attachments = self.embed_attachments(final_pdf_path, attachments)

        return {
            "pdf_path": final_pdf_path,
            "xml_path": xml_path,
            "embedded_attachments": embedded_attachments,
        }
