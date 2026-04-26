"""
Constants for ZUGFeRD/Factur-X XML generation and validation.

Contains schema paths, namespace definitions, and validation settings.
"""

from pathlib import Path  # noqa: I001

from django.conf import settings

# Set paths for schema files (official UN/CEFACT CII and EN16931 schemas)
# These are the official schemas from:
# - XSD: UN/CEFACT D16B Cross Industry Invoice
# - Schematron: EN16931 CII validation rules from ConnectingEurope
SCHEMAS_DIR = Path(settings.BASE_DIR) / "schemas"
XSD_PATH = (
    SCHEMAS_DIR
    / "D16B SCRDM (Subset) CII"
    / "D16B SCRDM (Subset) CII uncoupled"
    / "uncoupled clm"
    / "CII"
    / "uncefact"
    / "data"
    / "standard"
    / "CrossIndustryInvoice_100pD16B.xsd"
)
SCHEMATRON_PATH = SCHEMAS_DIR / "en16931-schematron" / "schematron" / "EN16931-CII-validation.sch"
# Pre-compiled XSLT for faster Schematron validation (use this instead of .sch for performance)
# NOTE: EN16931 Schematron uses XPath 2.0 which requires Saxon, not lxml
SCHEMATRON_XSLT_PATH = SCHEMAS_DIR / "en16931-schematron" / "xslt" / "EN16931-CII-validation.xslt"

# XRechnung-specific Schematron (stricter than EN16931, includes BR-DE-* national rules)
# Source: KoSIT xrechnung-schematron v2.5.0 (compatible with XRechnung 3.0.2)
XRECHNUNG_SCHEMATRON_XSLT_PATH = (
    SCHEMAS_DIR / "xrechnung-schematron" / "schematron" / "cii" / "XRechnung-CII-validation.xsl"
)

# Validation settings with defaults
# Schematron validation uses Saxon-HE (via saxonche) for XPath 2.0+ support.
# Set ENABLE_SCHEMATRON_VALIDATION=False in Django settings to disable.
ENABLE_SCHEMATRON_VALIDATION = getattr(settings, "ENABLE_SCHEMATRON_VALIDATION", True)
SCHEMATRON_STRICT_MODE = getattr(settings, "SCHEMATRON_STRICT_MODE", False)
XML_VALIDATION_TIMING_THRESHOLD_MS = getattr(settings, "XML_VALIDATION_TIMING_THRESHOLD_MS", 200)
# REQUIRE_VALIDATION_SCHEMAS: If True (default), missing validation schemas is an error.
# This prevents the NoOp backend from silently bypassing validation.
REQUIRE_VALIDATION_SCHEMAS = getattr(settings, "REQUIRE_VALIDATION_SCHEMAS", True)

# XML Namespaces
RSM_NS = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
UDT_NS = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"

# ZUGFeRD/Factur-X Profile URIs
# Source: Mustang Profiles.java (github.com/ZUGFeRD/mustangproject)
# Note: "1p0" is the spec part-version (not a calendar year) – stays unchanged.
# Note: ":2017" in the EN16931 URI refers to the standard publication year, not the invoice year.
PROFILE_MAP = {
    "MINIMUM": "urn:factur-x.eu:1p0:minimum",
    "BASICWL": "urn:factur-x.eu:1p0:basicwl",
    "BASIC": "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic",
    "COMFORT": "urn:cen.eu:en16931:2017",  # EN16931 CIUS (same as ZUGFeRD EN16931 profile)
    "EXTENDED": "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended",
    "XRECHNUNG": "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0",
}

# UN/ECE Recommendation 20 unit codes mapping
# Primärer Pfad: numerische IDs aus Product.UnitOfMeasure (int-Keys)
# Sekundärer Pfad: String-Aliase für direkte Generator-Aufrufe und Kompatiblität
UNIT_CODE_MAP = {
    # ── Numerische IDs (aus Product.UnitOfMeasure IntegerChoices) ──────────
    1: "C62",  # PCE – Stück
    2: "HUR",  # HUR – Stunde
    3: "DAY",  # DAY – Tag
    4: "KGM",  # KGM – Kilogramm
    5: "LTR",  # LTR – Liter
    6: "MON",  # MON – Monat
    # ── String-Aliase (Altdaten, Tests, direkte Generator-Aufrufe) ─────────
    "PCE": "C62",
    "PIECE": "C62",
    "UNIT": "C62",
    "EA": "C62",
    "HUR": "HUR",
    "HOUR": "HUR",
    "HR": "HUR",
    "DAY": "DAY",
    "KGM": "KGM",
    "KG": "KGM",
    "KILOGRAM": "KGM",
    "LTR": "LTR",
    "L": "LTR",
    "LITER": "LTR",
    "MON": "MON",
    "MONTH": "MON",
    # weitere gültige UN/CEFACT-Codes die direkt durchgereicht werden
    "MTR": "MTR",
    "M": "MTR",
    "METER": "MTR",
    "CMT": "CMT",
    "CM": "CMT",
    "GRM": "GRM",
    "MIN": "MIN",
    "MTK": "MTK",
    "M2": "MTK",
    "MTQ": "MTQ",
    "M3": "MTQ",
}

# Country code mapping for long names to ISO 3166-1 alpha-2
COUNTRY_CODE_MAP = {
    "Deutschland": "DE",
    "Germany": "DE",
    "Österreich": "AT",
    "Austria": "AT",
    "Schweiz": "CH",
    "Switzerland": "CH",
}
