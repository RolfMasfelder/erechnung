"""
XML generation and validation utilities for ZUGFeRD/Factur-X invoices.

This package provides functionality for generating valid XML documents according to
the ZUGFeRD/Factur-X standard, as well as validating existing XML against the schema.
"""

from invoice_app.utils.xml.backends import (
    CombinedBackend,
    NoOpBackend,
    SchematronBackend,
    SchematronSaxonBackend,
    ValidationBackend,
    ValidationResult,
    XsdOnlyBackend,
)
from invoice_app.utils.xml.constants import (
    ENABLE_SCHEMATRON_VALIDATION,
    SCHEMAS_DIR,
    SCHEMATRON_PATH,
    SCHEMATRON_STRICT_MODE,
    SCHEMATRON_XSLT_PATH,
    XML_VALIDATION_TIMING_THRESHOLD_MS,
    XSD_PATH,
)
from invoice_app.utils.xml.generator import ZugferdXmlGenerator
from invoice_app.utils.xml.validator import ZugferdXmlValidator


__all__ = [
    # Generator
    "ZugferdXmlGenerator",
    # Validator
    "ZugferdXmlValidator",
    # Backends
    "ValidationResult",
    "ValidationBackend",
    "NoOpBackend",
    "XsdOnlyBackend",
    "SchematronBackend",
    "SchematronSaxonBackend",
    "CombinedBackend",
    # Constants
    "SCHEMAS_DIR",
    "XSD_PATH",
    "SCHEMATRON_PATH",
    "SCHEMATRON_XSLT_PATH",
    "ENABLE_SCHEMATRON_VALIDATION",
    "SCHEMATRON_STRICT_MODE",
    "XML_VALIDATION_TIMING_THRESHOLD_MS",
]
