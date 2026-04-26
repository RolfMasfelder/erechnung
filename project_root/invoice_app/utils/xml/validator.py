"""
ZUGFeRD/Factur-X XML Validator.

Modernized XML validator with pluggable backends that automatically selects
the best validation strategy based on available schemas.
"""

import logging

from lxml import etree

from invoice_app.utils.xml.backends import (
    CombinedBackend,
    NoOpBackend,
    SchematronSaxonBackend,
    ValidationResult,
    XsdOnlyBackend,
)
from invoice_app.utils.xml.constants import (
    ENABLE_SCHEMATRON_VALIDATION,
    REQUIRE_VALIDATION_SCHEMAS,
    SCHEMATRON_STRICT_MODE,
    SCHEMATRON_XSLT_PATH,
    XML_VALIDATION_TIMING_THRESHOLD_MS,
    XSD_PATH,
)


logger = logging.getLogger(__name__)


class ZugferdXmlValidator:
    """
    Modernized ZUGFeRD/Factur-X XML validator with pluggable backends.

    Automatically selects the best validation backend based on available schemas:
    - CombinedBackend: Both XSD and Schematron available
    - XsdOnlyBackend: Only XSD available
    - SchematronSaxonBackend: Only Schematron available (via Saxon-HE)
    - NoOpBackend: No schemas available (fallback)
    """

    def __init__(self, backend=None):
        """
        Initialize the validator with optional backend override.

        Args:
            backend (ValidationBackend, optional): Specific backend to use.
                                                 If None, auto-detects based on available schemas.
        """
        self.xsd_schema = None
        self.schematron_backend = None
        self._backend = None

        if backend is None:
            self._load_schemas()
            self._select_backend()
        else:
            self._backend = backend

    def _load_schemas(self):
        """Load the XSD and Schematron schemas for validation."""
        try:
            # Load XSD schema
            if XSD_PATH.exists():
                try:
                    self.xsd_schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
                    logger.info(f"Loaded XSD schema from {XSD_PATH}")
                except Exception as e:
                    logger.warning(f"Error loading XSD schema: {e}")
                    self.xsd_schema = None
            else:
                logger.debug(f"XSD schema file not found: {XSD_PATH}")

            # Load Schematron via Saxon-HE (only if enabled)
            if ENABLE_SCHEMATRON_VALIDATION and SCHEMATRON_XSLT_PATH.exists():
                try:
                    self.schematron_backend = SchematronSaxonBackend(SCHEMATRON_XSLT_PATH)
                    logger.info(f"Loaded Schematron XSLT via Saxon from {SCHEMATRON_XSLT_PATH}")
                except Exception as e:
                    logger.warning(f"Error loading Schematron Saxon backend: {e}")
                    self.schematron_backend = None
            elif not ENABLE_SCHEMATRON_VALIDATION:
                logger.debug("Schematron validation disabled in settings")
            else:
                logger.debug(f"Schematron XSLT file not found: {SCHEMATRON_XSLT_PATH}")

        except Exception as e:
            logger.error(f"Error loading schemas: {e}")
            self.xsd_schema = None
            self.schematron_backend = None

    def _select_backend(self):
        """Select appropriate validation backend based on available schemas."""
        if self.xsd_schema and self.schematron_backend:
            self._backend = CombinedBackend(XsdOnlyBackend(self.xsd_schema), self.schematron_backend)
            logger.info("Using combined XSD + Schematron-Saxon validation backend")
        elif self.xsd_schema:
            self._backend = XsdOnlyBackend(self.xsd_schema)
            logger.info("Using XSD-only validation backend")
        elif self.schematron_backend:
            self._backend = self.schematron_backend
            logger.info("Using Schematron-Saxon-only validation backend")
        # No validation schemas available - this is a configuration error
        elif REQUIRE_VALIDATION_SCHEMAS:
            error_msg = (
                "CRITICAL: No validation schemas available! "
                f"XSD path: {XSD_PATH} (exists: {XSD_PATH.exists()}), "
                f"Schematron XSLT path: {SCHEMATRON_XSLT_PATH} (exists: {SCHEMATRON_XSLT_PATH.exists()}). "
                "XML validation cannot be performed without schemas. "
                "Set REQUIRE_VALIDATION_SCHEMAS=False to allow NoOp backend (not recommended)."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            # Only use NoOp if explicitly allowed (not recommended)
            self._backend = NoOpBackend()
            logger.warning(
                "No validation schemas available, using NoOp backend. WARNING: This means NO validation is performed!"
            )

    def validate_xml(self, xml_content):
        """
        Validate XML using the selected backend.

        Args:
            xml_content (str or bytes): XML content to validate

        Returns:
            ValidationResult: Structured validation result with timing metrics
        """
        result = self._backend.validate(xml_content)

        # Log timing if above threshold
        if result.validation_time_ms > XML_VALIDATION_TIMING_THRESHOLD_MS:
            logger.info(f"XML validation took {result.validation_time_ms:.1f}ms (backend: {result.backend_used})")

        return result

    def validate_xml_legacy(self, xml_content):
        """
        Legacy method returning tuple format for backward compatibility.

        Args:
            xml_content (str or bytes): XML content to validate

        Returns:
            tuple: (is_valid, validation_errors) - for backward compatibility
        """
        result = self.validate_xml(xml_content)
        return result.is_valid, result.errors

    def validate_file(self, file_path):
        """
        Validate XML file using the selected backend.

        Args:
            file_path (str): Path to XML file

        Returns:
            ValidationResult: Structured validation result
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                xml_content = f.read()
            return self.validate_xml(xml_content)
        except Exception as e:
            logger.error(f"Error reading XML file: {e}")
            result = ValidationResult(is_valid=False, backend_used=self._backend.__class__.__name__)
            result.add_error(f"File error: {e}")
            return result

    def validate_file_legacy(self, file_path):
        """
        Legacy method returning tuple format for backward compatibility.

        Args:
            file_path (str): Path to XML file

        Returns:
            tuple: (is_valid, validation_errors) - for backward compatibility
        """
        result = self.validate_file(file_path)
        return result.is_valid, result.errors

    def get_validation_info(self) -> dict:
        """
        Get information about current validation configuration.

        Returns:
            dict: Validation configuration details
        """
        return {
            "xsd_available": XSD_PATH.exists(),
            "schematron_available": SCHEMATRON_XSLT_PATH.exists(),
            "schematron_enabled": ENABLE_SCHEMATRON_VALIDATION,
            "strict_mode": SCHEMATRON_STRICT_MODE,
            "timing_threshold_ms": XML_VALIDATION_TIMING_THRESHOLD_MS,
            "xsd_path": str(XSD_PATH),
            "schematron_path": str(SCHEMATRON_XSLT_PATH),
            "backend_type": self._backend.__class__.__name__,
            "schemas_loaded": {
                "xsd": self.xsd_schema is not None,
                "schematron": self.schematron_backend is not None,
            },
        }
