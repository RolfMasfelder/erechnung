"""
Validation backends for ZUGFeRD/Factur-X XML validation.

Provides pluggable backends for different validation strategies:
- NoOpBackend: No validation (fallback)
- XsdOnlyBackend: XSD schema validation only
- SchematronBackend: Schematron rules validation only (lxml, XPath 1.0)
- SchematronSaxonBackend: Schematron via Saxon-HE (XPath 2.0+)
- CombinedBackend: Both XSD and Schematron validation
"""

import logging
import time
from abc import ABC, abstractmethod

from lxml import etree


logger = logging.getLogger(__name__)


class ValidationResult:
    """
    Structured result for XML validation operations.

    Provides a consistent interface for validation results across different
    backend implementations, including error aggregation and timing metrics.
    """

    def __init__(self, is_valid=True, validation_time_ms=0, backend_used="unknown"):
        """
        Initialize validation result.

        Args:
            is_valid (bool): Whether validation passed
            validation_time_ms (float): Time taken for validation in milliseconds
            backend_used (str): Name of the backend that performed validation
        """
        self.is_valid = is_valid
        self.errors = []
        self.warnings = []
        self.validation_time_ms = validation_time_ms
        self.backend_used = backend_used

    def add_error(self, error_message):
        """Add an error message and mark result as invalid."""
        self.errors.append(error_message)
        self.is_valid = False

    def add_warning(self, warning_message):
        """Add a warning message without affecting validity."""
        self.warnings.append(warning_message)

    def merge(self, other_result):
        """
        Merge another ValidationResult into this one.

        Args:
            other_result (ValidationResult): Another validation result to merge
        """
        if not other_result.is_valid:
            self.is_valid = False
        self.errors.extend(other_result.errors)
        self.warnings.extend(other_result.warnings)
        self.validation_time_ms += other_result.validation_time_ms


class ValidationBackend(ABC):
    """Abstract base class for validation backends."""

    @abstractmethod
    def validate(self, xml_content):
        """
        Validate XML content and return ValidationResult.

        Args:
            xml_content (str or bytes): XML content to validate

        Returns:
            ValidationResult: Structured validation result
        """
        pass


class NoOpBackend(ValidationBackend):
    """
    No-operation validation backend.

    Returns invalid result with an error that no validation schemas are available.
    This backend should only be used when REQUIRE_VALIDATION_SCHEMAS=False.
    Missing validation schemas is a configuration error that must be addressed.
    """

    def validate(self, xml_content):
        """Returns invalid with error - missing schemas is a validation failure."""
        result = ValidationResult(is_valid=False, backend_used="NoOp")
        result.add_error(
            "VALIDATION ERROR: No validation schemas available. "
            "Cannot validate XML without XSD or Schematron schemas. "
            "Please ensure schema files are properly installed."
        )
        return result


class XsdOnlyBackend(ValidationBackend):
    """XSD-only validation backend."""

    def __init__(self, xsd_schema):
        """
        Initialize with XSD schema.

        Args:
            xsd_schema: Parsed lxml XMLSchema object
        """
        self.xsd_schema = xsd_schema

    def validate(self, xml_content):
        """Validate XML against XSD schema only."""
        start_time = time.time()
        result = ValidationResult(backend_used="XSD-only")

        try:
            # Parse XML content
            if isinstance(xml_content, str):
                xml_doc = etree.fromstring(xml_content.encode("utf-8"))
            else:
                xml_doc = etree.fromstring(xml_content)

            # Validate against XSD
            if not self.xsd_schema.validate(xml_doc):
                for error in self.xsd_schema.error_log:
                    result.add_error(f"XSD: {error.message}")

        except Exception as e:
            result.add_error(f"XSD validation error: {e}")

        result.validation_time_ms = (time.time() - start_time) * 1000
        return result


class SchematronBackend(ValidationBackend):
    """ISO Schematron-only validation backend."""

    def __init__(self, schematron):
        """
        Initialize with Schematron schema.

        Args:
            schematron: Parsed lxml isoschematron.Schematron object
        """
        self.schematron = schematron

    def validate(self, xml_content):
        """Validate XML against Schematron rules only."""
        start_time = time.time()
        result = ValidationResult(backend_used="Schematron-only")

        try:
            # Parse XML content
            if isinstance(xml_content, str):
                xml_doc = etree.fromstring(xml_content.encode("utf-8"))
            else:
                xml_doc = etree.fromstring(xml_content)

            # Validate against Schematron
            if not self.schematron.validate(xml_doc):
                for error in self.schematron.error_log:
                    result.add_error(f"Schematron: {error.message}")

        except Exception as e:
            result.add_error(f"Schematron validation error: {e}")

        result.validation_time_ms = (time.time() - start_time) * 1000
        return result


class SchematronSaxonBackend(ValidationBackend):
    """
    EN16931 Schematron validation via Saxon-HE (XPath 2.0+).

    Uses pre-compiled XSLT (from .sch → .xslt) applied via saxonche
    to produce SVRL (Schematron Validation Report Language) output,
    then parses failed-assert elements as validation errors.
    """

    SVRL_NS = "http://purl.oclc.org/dsdl/svrl"

    def __init__(self, xslt_path):
        """
        Initialize with path to pre-compiled Schematron XSLT.

        Args:
            xslt_path (str or Path): Path to the EN16931-CII-validation.xslt file
        """
        import saxonche

        self._xslt_path = str(xslt_path)
        self._proc = saxonche.PySaxonProcessor(license=False)
        self._xslt_proc = self._proc.new_xslt30_processor()
        # Pre-compile the stylesheet once for reuse
        self._executable = self._xslt_proc.compile_stylesheet(stylesheet_file=self._xslt_path)
        logger.info(f"Saxon-HE Schematron backend initialized ({self._proc.version})")

    def validate(self, xml_content):
        """Validate XML against EN16931 Schematron rules via Saxon XSLT."""
        start_time = time.time()
        result = ValidationResult(backend_used="Schematron-Saxon")

        try:
            # Ensure bytes
            if isinstance(xml_content, str):
                xml_bytes = xml_content.encode("utf-8")
            else:
                xml_bytes = xml_content

            # Run XSLT transformation to produce SVRL report
            node = self._proc.parse_xml(xml_text=xml_bytes.decode("utf-8"))
            svrl_xml = self._executable.transform_to_string(xdm_node=node)

            if svrl_xml is None:
                result.add_error("Schematron-Saxon: XSLT transformation returned no output")
                result.validation_time_ms = (time.time() - start_time) * 1000
                return result

            # Parse SVRL output
            self._parse_svrl(svrl_xml, result)

        except Exception as e:
            result.add_error(f"Schematron-Saxon validation error: {e}")

        result.validation_time_ms = (time.time() - start_time) * 1000
        return result

    def _parse_svrl(self, svrl_xml, result):
        """
        Parse SVRL XML and extract failed-assert / successful-report elements.

        Args:
            svrl_xml (str): SVRL XML string from Saxon XSLT transformation
            result (ValidationResult): Result object to populate
        """
        svrl_doc = etree.fromstring(svrl_xml.encode("utf-8"))
        ns = {"svrl": self.SVRL_NS}

        # Extract failed assertions (errors)
        for failed in svrl_doc.findall(".//svrl:failed-assert", ns):
            location = failed.get("location", "unknown")
            rule_id = failed.get("id", "")
            flag = failed.get("flag", "error")
            text_el = failed.find("svrl:text", ns)
            text = text_el.text.strip() if text_el is not None and text_el.text else "Unknown error"

            msg = f"[{rule_id}] {text}" if rule_id else text
            if flag == "warning":
                result.add_warning(f"Schematron: {msg} (at {location})")
            else:
                result.add_error(f"Schematron: {msg} (at {location})")

        # Extract successful-report with flag="warning" (informational)
        for report in svrl_doc.findall(".//svrl:successful-report", ns):
            flag = report.get("flag", "")
            if flag == "warning":
                location = report.get("location", "unknown")
                text_el = report.find("svrl:text", ns)
                text = text_el.text.strip() if text_el is not None and text_el.text else ""
                if text:
                    result.add_warning(f"Schematron: {text} (at {location})")


class CombinedBackend(ValidationBackend):
    """Combined XSD + Schematron validation backend."""

    def __init__(self, xsd_backend, schematron_backend):
        """
        Initialize with XSD and Schematron backend instances.

        Args:
            xsd_backend (ValidationBackend): XSD validation backend
            schematron_backend (ValidationBackend): Schematron validation backend
        """
        self.xsd_backend = xsd_backend
        self.schematron_backend = schematron_backend

    def validate(self, xml_content):
        """Validate XML against both XSD and Schematron."""
        start_time = time.time()

        # Run both validations
        xsd_result = self.xsd_backend.validate(xml_content)
        schematron_result = self.schematron_backend.validate(xml_content)

        # Merge results
        combined_result = ValidationResult(backend_used="Combined (XSD + Schematron)")
        combined_result.merge(xsd_result)
        combined_result.merge(schematron_result)

        # Update timing to reflect total validation time
        combined_result.validation_time_ms = (time.time() - start_time) * 1000
        return combined_result
