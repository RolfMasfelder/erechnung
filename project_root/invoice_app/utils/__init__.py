"""
Invoice App Utilities

This package provides utility modules for the invoice application:
- pdf: PDF/A-3 generation and handling
- xml: ZUGFeRD/Factur-X XML generation
- incoming_xml: XML parsing for incoming invoices
- validation: Invoice validation utilities
"""

# Import main utilities for easy access
from .incoming_xml import IncomingXmlParser, SupplierDataExtractor
from .pdf import PdfA3Generator
from .validation import InvoiceFileManager, InvoiceValidator, ValidationResult
from .xml import ZugferdXmlGenerator


__all__ = [
    # PDF utilities
    "PdfA3Generator",
    # XML utilities
    "ZugferdXmlGenerator",
    # Incoming invoice utilities
    "IncomingXmlParser",
    "SupplierDataExtractor",
    "InvoiceValidator",
    "InvoiceFileManager",
    "ValidationResult",
]
