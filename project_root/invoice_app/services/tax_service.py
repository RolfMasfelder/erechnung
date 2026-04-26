"""
Tax determination service for the invoice_app.

Implements EU tax logic for three scenarios:
1. Inland (Domestic): Company & customer in same country → normal VAT rates
2. EU Reverse Charge: Different EU country + valid VAT ID → 0%, category "AE"
3. Drittland (Export): Non-EU country → 0%, category "G"

Reference: EU VAT Directive 2006/112/EC, EN16931, ZUGFeRD 2.x
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


logger = logging.getLogger(__name__)


class TaxScenario(StrEnum):
    """Tax scenario based on customer location and VAT ID."""

    DOMESTIC = "DOMESTIC"
    EU_REVERSE_CHARGE = "EU_REVERSE_CHARGE"
    EXPORT = "EXPORT"


# EN16931 / UNTDID 5305 tax category codes
TAX_CATEGORY_CODES = {
    TaxScenario.DOMESTIC: "S",  # Standard (or Z/E for 0%/exempt products)
    TaxScenario.EU_REVERSE_CHARGE: "AE",  # Reverse Charge
    TaxScenario.EXPORT: "G",  # Export outside the EU
}

# ZUGFeRD exemption reason texts (required for AE and G categories)
EXEMPTION_REASONS = {
    TaxScenario.EU_REVERSE_CHARGE: "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)",
    TaxScenario.EXPORT: "Steuerbefreit – Ausfuhrlieferung gem. § 4 Nr. 1a UStG",
}

# EU VAT ID format patterns per country code (ISO 3166-1 alpha-2)
# Source: https://ec.europa.eu/taxation_customs/vies/faq.html
EU_VAT_ID_PATTERNS = {
    "AT": r"^ATU\d{8}$",
    "BE": r"^BE[01]\d{9}$",
    "BG": r"^BG\d{9,10}$",
    "CY": r"^CY\d{8}[A-Z]$",
    "CZ": r"^CZ\d{8,10}$",
    "DE": r"^DE\d{9}$",
    "DK": r"^DK\d{8}$",
    "EE": r"^EE\d{9}$",
    "EL": r"^EL\d{9}$",  # Greece uses EL, not GR
    "GR": r"^EL\d{9}$",  # Alias for Greece
    "ES": r"^ES[A-Z0-9]\d{7}[A-Z0-9]$",
    "FI": r"^FI\d{8}$",
    "FR": r"^FR[A-Z0-9]{2}\d{9}$",
    "HR": r"^HR\d{11}$",
    "HU": r"^HU\d{8}$",
    "IE": r"^IE\d{7}[A-Z]{1,2}$|^IE\d[A-Z+*]\d{5}[A-Z]$",
    "IT": r"^IT\d{11}$",
    "LT": r"^LT\d{9}$|^LT\d{12}$",
    "LU": r"^LU\d{8}$",
    "LV": r"^LV\d{11}$",
    "MT": r"^MT\d{8}$",
    "NL": r"^NL\d{9}B\d{2}$",
    "PL": r"^PL\d{10}$",
    "PT": r"^PT\d{9}$",
    "RO": r"^RO\d{2,10}$",
    "SE": r"^SE\d{12}$",
    "SI": r"^SI\d{8}$",
    "SK": r"^SK\d{10}$",
    # Northern Ireland special case (XI prefix post-Brexit)
    "XI": r"^XI\d{3}\d{4}\d{2}$|^XI\d{9}$|^XIGD\d{3}$|^XIHA\d{3}$",
}


@dataclass
class TaxDetermination:
    """Result of tax determination for an invoice line."""

    scenario: TaxScenario
    tax_rate: Decimal
    tax_category_code: str
    exemption_reason: str


class TaxService:
    """
    Service for determining applicable tax rates based on the
    relationship between the issuing company and the business partner.
    """

    @staticmethod
    def determine_tax_scenario(company_country_code: str, partner) -> TaxScenario:
        """
        Determine the tax scenario based on company and partner locations.

        Args:
            company_country_code: ISO 3166-1 alpha-2 code of the company (e.g., "DE")
            partner: BusinessPartner instance (or None)

        Returns:
            TaxScenario enum value
        """
        if not partner or not partner.country:
            # No partner or no country set → assume domestic
            return TaxScenario.DOMESTIC

        partner_country = partner.country  # Country model instance
        partner_country_code = partner_country.code

        # Same country → domestic
        if partner_country_code == company_country_code:
            return TaxScenario.DOMESTIC

        # Different country, check EU membership
        if partner_country.is_eu_member:
            # EU country — check for valid VAT ID for Reverse Charge
            if partner.vat_id and TaxService.validate_vat_id_format(partner.vat_id):
                return TaxScenario.EU_REVERSE_CHARGE
            else:
                # EU but no valid VAT ID → still domestic-style VAT
                # (Seller must charge VAT of their own country for B2C)
                return TaxScenario.DOMESTIC
        else:
            # Non-EU country → export (Drittland)
            return TaxScenario.EXPORT

    @staticmethod
    def get_tax_determination(
        product_tax_rate: Decimal,
        product_tax_category: str,
        company_country_code: str,
        partner,
    ) -> TaxDetermination:
        """
        Determine the full tax treatment for an invoice line.

        Args:
            product_tax_rate: The product's default tax rate (e.g., 19.00)
            product_tax_category: The product's tax category (STANDARD, REDUCED, etc.)
            company_country_code: ISO alpha-2 code of the issuing company
            partner: BusinessPartner instance

        Returns:
            TaxDetermination with rate, category code, and exemption reason
        """
        scenario = TaxService.determine_tax_scenario(company_country_code, partner)

        if scenario == TaxScenario.DOMESTIC:
            # Use the product's normal tax rate
            # Map product tax category to ZUGFeRD category code
            if product_tax_category == "EXEMPT":
                category_code = "E"
            elif product_tax_category == "ZERO" or product_tax_rate == Decimal("0"):
                category_code = "Z"
            else:
                category_code = "S"

            return TaxDetermination(
                scenario=scenario,
                tax_rate=product_tax_rate,
                tax_category_code=category_code,
                exemption_reason="",
            )

        elif scenario == TaxScenario.EU_REVERSE_CHARGE:
            return TaxDetermination(
                scenario=scenario,
                tax_rate=Decimal("0.00"),
                tax_category_code="AE",
                exemption_reason=EXEMPTION_REASONS[TaxScenario.EU_REVERSE_CHARGE],
            )

        else:  # EXPORT
            return TaxDetermination(
                scenario=scenario,
                tax_rate=Decimal("0.00"),
                tax_category_code="G",
                exemption_reason=EXEMPTION_REASONS[TaxScenario.EXPORT],
            )

    @staticmethod
    def validate_vat_id_format(vat_id: str) -> bool:
        """
        Validate EU VAT ID format (syntactic check, not VIES verification).

        Checks that the VAT ID matches the expected pattern for the
        country prefix. This is a format check only — it does NOT verify
        the ID against the EU VIES database.

        Args:
            vat_id: The VAT identification number (e.g., "DE123456789")

        Returns:
            True if the format is valid, False otherwise
        """
        if not vat_id or len(vat_id) < 4:
            return False

        vat_id = vat_id.strip().upper().replace(" ", "")

        # Extract country prefix (first 2 chars)
        country_prefix = vat_id[:2]

        pattern = EU_VAT_ID_PATTERNS.get(country_prefix)
        if not pattern:
            # Unknown country prefix — allow it (may be a non-standard format)
            logger.warning("Unknown VAT ID country prefix: %s (VAT ID: %s)", country_prefix, vat_id)
            return len(vat_id) >= 5  # Minimum reasonable length

        return bool(re.match(pattern, vat_id))

    @staticmethod
    def get_company_country_code(company) -> str:
        """
        Get the ISO country code for the issuing company.

        The Company model stores country as CharField (name or code).
        We use the country_id property which maps it to ISO alpha-2.

        Args:
            company: Company model instance

        Returns:
            str: ISO 3166-1 alpha-2 code (e.g., "DE")
        """
        if company:
            return company.country_id  # Uses property with COUNTRY_CODE_MAP
        return "DE"  # Default to Germany
