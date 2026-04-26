# ZUGFeRD/Factur-X Validation Schemas

This directory contains the official validation schemas for ZUGFeRD/Factur-X (EN16931) electronic invoicing.

## Contents

### 1. UN/CEFACT Cross Industry Invoice (CII) XSD Schemas

**Source:** UN/CEFACT (United Nations Centre for Trade Facilitation and Electronic Business)
**URL:** https://unece.org/trade/uncefact/xml-schemas
**Download:** http://www.unece.org/fileadmin/DAM/cefact/xml_schemas/D16B_SCRDM__Subset__CII.zip
**Version:** D16B (2016)
**License:** Public Domain (UN/CEFACT standard)

**Location:** `D16B SCRDM (Subset) CII/`

Key files:
- `CrossIndustryInvoice_100pD16B.xsd` - Main CII schema
- `CrossIndustryInvoice_ReusableAggregateBusinessInformationEntity_100pD16B.xsd` - Business entities (RAM namespace)
- `CrossIndustryInvoice_QualifiedDataType_100pD16B.xsd` - Qualified data types (QDT namespace)
- `CrossIndustryInvoice_UnqualifiedDataType_100pD16B.xsd` - Unqualified data types (UDT namespace)

### 2. EN16931 Schematron Validation Rules

**Source:** CEN/TC 434 - ConnectingEurope
**Repository:** https://github.com/ConnectingEurope/eInvoicing-EN16931
**Version:** 1.3.13 (October 2024)
**License:** European Union Public Licence (EUPL) version 1.2

**Location:** `en16931-schematron/`

Key files:
- `xslt/EN16931-CII-validation.xslt` - Pre-compiled XSLT for CII validation (used by Saxon)
- `schematron/EN16931-CII-validation.sch` - Original Schematron rules
- `schematron/codelist/EN16931-CII-codes.sch` - Code list validation rules

Validated via `saxonche` (Saxon-HE Python bindings) with XPath 2.0+ support.

## Usage

The schemas are used by `invoice_app/utils/xml.py` for validating generated ZUGFeRD XML invoices.

### XSD Validation (Active)
Validates the XML structure against the UN/CEFACT CII schema.
This catches structural errors and namespace issues.

### Schematron Validation (Active — via Saxon-HE)
Validates business rules according to EN16931 European e-Invoicing standard.
Uses pre-compiled XSLT with `saxonche` (Saxon-HE) for XPath 2.0+ support.
Enable/disable via `ENABLE_SCHEMATRON_VALIDATION` Django setting.

## Updates

To update the schemas:

1. **CII XSD Schemas:**
   - Download latest from: https://unece.org/trade/uncefact/xml-schemas
   - Look for "Cross Industry Invoice" subset

2. **EN16931 Schematron (if adding support):**
   - Check releases: https://github.com/ConnectingEurope/eInvoicing-EN16931/releases
   - Download the `en16931-cii-X.X.X.zip` file

## Related Standards

- **ZUGFeRD 2.1/2.2:** German e-invoicing standard based on Factur-X
- **Factur-X 1.0:** French-German e-invoicing standard
- **EN16931:** European e-invoicing standard (CEN/TC 434)
- **XRechnung:** German CIUS (Core Invoice Usage Specification) for EN16931

## References

- UN/CEFACT: https://unece.org/trade/uncefact
- EN16931 GitHub: https://github.com/ConnectingEurope/eInvoicing-EN16931
- ZUGFeRD: https://www.ferd-net.de/
- Factur-X: https://fnfe-mpe.org/factur-x/

---
Last updated: November 2025
