# PDF and XML Handling Documentation

## Overview

This module handles the creation of PDF/A-3 documents with embedded XML for ZUGFeRD/EN16931 compliance. It consists of several components:

1. PDF Generation with WeasyPrint
2. XML Validation using XSD and Schematron
3. PDF/A-3 Conformance with embedded XML
4. Document Integrity Verification

## PDF Generation

The `PdfA3Generator` class in `invoice_app/utils/pdf.py` handles PDF creation using WeasyPrint:

```python
from invoice_app.utils.pdf import PdfA3Generator

# Create a new PDF/A-3 generator
generator = PdfA3Generator()

# Generate invoice PDF with embedded XML
result = generator.generate_invoice_pdf(invoice_data, xml_data)
```

## XML Validation

XML validation is done in two steps:

1. XSD Schema Validation - Ensures the XML structure is correct
2. Schematron Validation - Ensures business rules are followed

```python
from invoice_app.utils.xml import validate_xml

# Validate XML against XSD and Schematron
is_valid, errors = validate_xml(xml_data, xsd_path, sch_path)
```

## ZUGFeRD/EN16931 Compliance

The system ensures compliance with:

- ZUGFeRD 2.1 (Comfort/Extended profile)
- EN16931 (European e-invoicing standard)
- German GoBD requirements

## Integration with Django

The PDF/XML functionality is integrated with Django through:

1. API endpoints for generating and validating documents
2. Model methods for creating compliant documents
3. Admin interface actions for document operations

## Configuration

Key settings in `settings.py`:

- `PDF_OUTPUT_DIR` - Directory where PDFs are stored
- `XML_OUTPUT_DIR` - Directory where XMLs are stored
- `ZUGFERD_PROFILE` - ZUGFeRD profile to use (BASIC, COMFORT, EXTENDED)

## Dependencies

- WeasyPrint - HTML/CSS to PDF generation
- pikepdf - PDF manipulation and PDF/A-3 embedding
- lxml - XML processing and validation
