"""
ZUGFeRD/Factur-X XML Generator.

Generates valid XML documents according to the ZUGFeRD/Factur-X standard
following the official UN/CEFACT Cross Industry Invoice D16B structure.
"""

import logging  # noqa: I001

from invoice_app.utils.xml.constants import COUNTRY_CODE_MAP, PROFILE_MAP, RAM_NS, RSM_NS, UDT_NS, UNIT_CODE_MAP
from lxml import etree

logger = logging.getLogger(__name__)


class ZugferdXmlGenerator:
    """
    Generates ZUGFeRD/Factur-X compliant XML from invoice data.
    """

    def __init__(self, profile="COMFORT", enable_validation=False):
        """
        Initialize the XML generator.

        Args:
            profile (str): ZUGFeRD profile to use (BASIC, COMFORT, or EXTENDED)
            enable_validation (bool): Whether to enable schema validation (requires valid schema files)
        """
        self.profile = profile
        self.enable_validation = enable_validation
        self._validator = None

        if self.enable_validation:
            from invoice_app.utils.xml.validator import ZugferdXmlValidator

            self._validator = ZugferdXmlValidator()

    def generate_xml(self, invoice_data):
        """
        Generate ZUGFeRD/Factur-X XML from invoice data.

        Follows official UN/CEFACT Cross Industry Invoice D16B structure:
        - Root: rsm:CrossIndustryInvoice
        - Child 1: rsm:ExchangedDocumentContext (profile info)
        - Child 2: rsm:ExchangedDocument (invoice metadata)
        - Child 3: rsm:SupplyChainTradeTransaction (all trade data)

        Args:
            invoice_data (dict): Dictionary containing invoice data

        Returns:
            str: XML content as string
        """
        nsmap = {
            "rsm": RSM_NS,
            "ram": RAM_NS,
            "udt": UDT_NS,
        }

        # Root element: rsm:CrossIndustryInvoice (CORRECT root per official CII schema)
        root = etree.Element(f"{{{RSM_NS}}}CrossIndustryInvoice", nsmap=nsmap)

        # 1. ExchangedDocumentContext (REQUIRED - contains profile specification)
        self._add_exchanged_document_context(root)

        # 2. ExchangedDocument (REQUIRED - invoice metadata)
        self._add_exchanged_document(root, invoice_data)

        # 3. SupplyChainTradeTransaction (REQUIRED - contains all trade data)
        self._add_supply_chain_trade_transaction(root, invoice_data)

        # Convert to string
        xml_string = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

        # Validate generated XML if validation is enabled
        if self._validator is not None:
            result = self._validator.validate_xml(xml_string)
            if not result.is_valid:
                logger.warning(
                    f"Generated XML for invoice {invoice_data.get('invoice_number', '?')} "
                    f"failed validation: {result.errors}"
                )

        return xml_string

    def _add_exchanged_document_context(self, root):
        """
        Add ExchangedDocumentContext element (REQUIRED by CII schema).

        Contains the business process and guideline specification.

        Args:
            root: Root XML element
        """
        context = etree.SubElement(root, f"{{{RSM_NS}}}ExchangedDocumentContext")

        # GuidelineSpecifiedDocumentContextParameter (identifies the profile)
        guideline = etree.SubElement(context, f"{{{RAM_NS}}}GuidelineSpecifiedDocumentContextParameter")
        guideline_id = etree.SubElement(guideline, f"{{{RAM_NS}}}ID")

        # Set profile identifier based on self.profile
        guideline_id.text = PROFILE_MAP.get(self.profile.upper(), "urn:cen.eu:en16931:2017")

    def _add_exchanged_document(self, root, invoice_data):
        """
        Add ExchangedDocument element with official ZUGFeRD structure.

        This includes all required metadata:
        - ID: Invoice number
        - TypeCode: Document type (380 = commercial invoice)
        - IssueDateTime: Invoice date

        Args:
            root: Root XML element
            invoice_data (dict): Invoice data dictionary
        """
        # Create ExchangedDocument with rsm namespace
        exchanged_doc = etree.SubElement(root, f"{{{RSM_NS}}}ExchangedDocument")

        # Add ID (invoice number) - using ram namespace
        id_element = etree.SubElement(exchanged_doc, f"{{{RAM_NS}}}ID")
        id_element.text = str(invoice_data.get("number", invoice_data.get("invoice_number", "")))

        # Add TypeCode - using ram namespace
        type_code_element = etree.SubElement(exchanged_doc, f"{{{RAM_NS}}}TypeCode")
        # 380 is the standard code for a commercial invoice
        type_code_element.text = str(invoice_data.get("type_code", "380"))

        # Add IssueDateTime - using ram namespace with DateTimeString child
        issue_dt = etree.SubElement(exchanged_doc, f"{{{RAM_NS}}}IssueDateTime")
        date_string = etree.SubElement(issue_dt, f"{{{UDT_NS}}}DateTimeString")
        date_string.set("format", "102")  # YYYYMMDD format

        # Format date as YYYYMMDD
        issue_date = invoice_data.get("date", "")
        if isinstance(issue_date, str):
            # Remove any separators and get only digits
            formatted_date = "".join(c for c in issue_date if c.isdigit())
            if len(formatted_date) >= 8:
                formatted_date = formatted_date[:8]
            else:
                formatted_date = "20000101"  # Fallback
        else:
            formatted_date = "20000101"  # Fallback
        date_string.text = formatted_date

    def _add_supply_chain_trade_transaction(self, root, invoice_data):
        """
        Add SupplyChainTradeTransaction element (REQUIRED by CII schema).

        NOTE: The element itself is in rsm namespace (as child of CrossIndustryInvoice),
        but its children are in ram namespace.

        This is the main container for all trade data:
        - IncludedSupplyChainTradeLineItem (line items)
        - ApplicableHeaderTradeAgreement (buyer/seller info)
        - ApplicableHeaderTradeDelivery (delivery info)
        - ApplicableHeaderTradeSettlement (payment/totals)

        Args:
            root: Root XML element
            invoice_data: Invoice data dictionary
        """
        transaction = etree.SubElement(root, f"{{{RSM_NS}}}SupplyChainTradeTransaction")

        # Add line items FIRST (per schema order)
        self._add_included_supply_chain_trade_line_items(transaction, invoice_data)

        # ApplicableHeaderTradeAgreement (buyer/seller)
        self._add_applicable_header_trade_agreement(transaction, invoice_data)

        # ApplicableHeaderTradeDelivery
        self._add_applicable_header_trade_delivery(transaction, invoice_data)

        # ApplicableHeaderTradeSettlement (payment terms & totals)
        self._add_applicable_header_trade_settlement(transaction, invoice_data)

    def _add_applicable_header_trade_agreement(self, transaction, invoice_data):
        """
        Add ApplicableHeaderTradeAgreement (buyer/seller party information).

        Args:
            transaction: SupplyChainTradeTransaction element
            invoice_data: Invoice data dictionary
        """
        agreement = etree.SubElement(transaction, f"{{{RAM_NS}}}ApplicableHeaderTradeAgreement")

        # SellerTradeParty
        seller_party = etree.SubElement(agreement, f"{{{RAM_NS}}}SellerTradeParty")
        seller_data = invoice_data.get("company", invoice_data.get("issuer", {}))
        self._add_trade_party_details(seller_party, seller_data)

        # BuyerTradeParty
        buyer_party = etree.SubElement(agreement, f"{{{RAM_NS}}}BuyerTradeParty")
        buyer_data = invoice_data.get("customer", {})
        self._add_trade_party_details(buyer_party, buyer_data)

        # SellerOrderReferencedDocument must come BEFORE BuyerOrderReferencedDocument
        # per the CII XSD sequence (HeaderTradeAgreementType). Wrong order causes
        # schema validation error (cvc-complex-type.2.4.a).
        seller_reference = invoice_data.get("seller_reference", "")
        if seller_reference:
            seller_order_doc = etree.SubElement(agreement, f"{{{RAM_NS}}}SellerOrderReferencedDocument")
            seller_order_id = etree.SubElement(seller_order_doc, f"{{{RAM_NS}}}IssuerAssignedID")
            seller_order_id.text = seller_reference

        # BuyerOrderReferencedDocument (optional - "Ihr Zeichen")
        buyer_reference = invoice_data.get("buyer_reference", "")
        if buyer_reference:
            buyer_order_doc = etree.SubElement(agreement, f"{{{RAM_NS}}}BuyerOrderReferencedDocument")
            buyer_order_id = etree.SubElement(buyer_order_doc, f"{{{RAM_NS}}}IssuerAssignedID")
            buyer_order_id.text = buyer_reference

        # AdditionalReferencedDocument (Phase C – rechnungsbegründende Dokumente)
        # Per XSD sequence: comes after BuyerOrderReferencedDocument
        self._add_additional_referenced_documents(agreement, invoice_data)

    def _add_additional_referenced_documents(self, agreement, invoice_data):
        """
        Add AdditionalReferencedDocument elements for embedded attachments.

        Each attached supporting document (Stundenzettel, Lieferschein, etc.) is
        referenced in the CII XML so that XML-only receivers know about embedded
        files in the PDF/A-3.

        Structure per CII D16B ReferencedDocumentType:
          - IssuerAssignedID: filename (unique identifier within the invoice)
          - TypeCode: 916 (referencing document) or 130 (invoiced object identifier)
          - Name: description / original filename

        TypeCode mapping from AttachmentType:
          - supporting_document → 916
          - delivery_note → 916
          - timesheet → 916
          - other → 916

        EN16931 CII-SR-113 produces a warning (not error) for this element.
        This is expected and correct for PDF/A-3 invoices with embedded documents.
        """
        attachments = invoice_data.get("additional_documents", [])
        if not attachments:
            return

        for doc in attachments:
            ref_doc = etree.SubElement(agreement, f"{{{RAM_NS}}}AdditionalReferencedDocument")

            # IssuerAssignedID (filename as identifier)
            issuer_id = etree.SubElement(ref_doc, f"{{{RAM_NS}}}IssuerAssignedID")
            issuer_id.text = doc.get("filename", "unknown")

            # TypeCode: 916 = additional document reference (referencing document)
            type_code = etree.SubElement(ref_doc, f"{{{RAM_NS}}}TypeCode")
            type_code.text = doc.get("type_code", "916")

            # Name (description or filename for human readability)
            name_el = etree.SubElement(ref_doc, f"{{{RAM_NS}}}Name")
            name_el.text = doc.get("description", doc.get("filename", ""))

    def _add_trade_party_details(self, party_element, party_data):
        """
        Add party details (name, address, tax registration).

        Args:
            party_element: TradeParty XML element
            party_data: Party data (dict or model)
        """
        # Name (required)
        name_element = etree.SubElement(party_element, f"{{{RAM_NS}}}Name")
        if isinstance(party_data, dict):
            name_element.text = party_data.get("name", "Unknown")
        else:
            name_element.text = getattr(party_data, "name", "Unknown")

        def get_val(key, default=""):
            if isinstance(party_data, dict):
                return party_data.get(key, default)
            return getattr(party_data, key, default)

        # SpecifiedLegalOrganization (commercial register – HRB/HRA)
        # Must appear after Name and before PostalTradeAddress per ZUGFeRD XSD sequence
        commercial_register = get_val("commercial_register")
        if commercial_register:
            legal_org = etree.SubElement(party_element, f"{{{RAM_NS}}}SpecifiedLegalOrganization")
            legal_org_id = etree.SubElement(legal_org, f"{{{RAM_NS}}}ID")
            # 0002 = DUNS/HRB; use as generic identifier for German commercial register
            legal_org_id.set("schemeID", "0002")
            legal_org_id.text = commercial_register

        # PostalTradeAddress
        address = etree.SubElement(party_element, f"{{{RAM_NS}}}PostalTradeAddress")

        # PostcodeCode
        postcode = etree.SubElement(address, f"{{{RAM_NS}}}PostcodeCode")
        postcode.text = get_val("postcode_code") or get_val("postal_code") or "00000"

        # LineOne (street)
        line_one = etree.SubElement(address, f"{{{RAM_NS}}}LineOne")
        line_one.text = get_val("street_name") or get_val("address_line1") or "Unknown Street"

        # CityName
        city = etree.SubElement(address, f"{{{RAM_NS}}}CityName")
        city.text = get_val("city_name") or get_val("city") or "Unknown City"

        # CountryID (ISO 3166-1 alpha-2)
        country = etree.SubElement(address, f"{{{RAM_NS}}}CountryID")
        country_val = get_val("country_id") or get_val("country") or "DE"
        if len(country_val) > 2:
            country_val = COUNTRY_CODE_MAP.get(country_val, "DE")
        country.text = country_val

        # SpecifiedTaxRegistration – two separate entries per ZUGFeRD spec:
        #   FC = Steuernummer (Finanzamt)  → tax_id
        #   VA = USt-Identifikationsnummer → vat_id
        tax_id_val = get_val("tax_id")
        if tax_id_val:
            tax_reg_fc = etree.SubElement(party_element, f"{{{RAM_NS}}}SpecifiedTaxRegistration")
            tax_reg_fc_id = etree.SubElement(tax_reg_fc, f"{{{RAM_NS}}}ID")
            tax_reg_fc_id.set("schemeID", "FC")  # FC = tax authority number
            tax_reg_fc_id.text = tax_id_val

        vat_id_val = get_val("vat_id")
        if vat_id_val:
            tax_reg_va = etree.SubElement(party_element, f"{{{RAM_NS}}}SpecifiedTaxRegistration")
            tax_reg_va_id = etree.SubElement(tax_reg_va, f"{{{RAM_NS}}}ID")
            tax_reg_va_id.set("schemeID", "VA")  # VA = VAT registration number
            tax_reg_va_id.text = vat_id_val

    def _add_applicable_header_trade_delivery(self, transaction, invoice_data):
        """
        Add ApplicableHeaderTradeDelivery element.

        Args:
            transaction: SupplyChainTradeTransaction element
            invoice_data: Invoice data dictionary
        """
        delivery = etree.SubElement(transaction, f"{{{RAM_NS}}}ApplicableHeaderTradeDelivery")

        # ActualDeliverySupplyChainEvent – BT-72 (Lieferdatum) ist in COMFORT/EN16931 Pflicht
        # [BR-FX-EN-04]: Rechnung muss BT-72, BG-14 oder BG-26 enthalten.
        # Fallback auf invoice_date ("date"), damit das Element nie leer bleibt.
        delivery_date = invoice_data.get("delivery_date") or invoice_data.get("date")
        if delivery_date:
            event = etree.SubElement(delivery, f"{{{RAM_NS}}}ActualDeliverySupplyChainEvent")
            occurrence = etree.SubElement(event, f"{{{RAM_NS}}}OccurrenceDateTime")
            date_str = etree.SubElement(occurrence, f"{{{UDT_NS}}}DateTimeString")
            date_str.set("format", "102")  # YYYYMMDD format
            # Convert date to YYYYMMDD
            if isinstance(delivery_date, str):
                date_str.text = "".join(c for c in delivery_date if c.isdigit())[:8]

    def _add_applicable_header_trade_settlement(self, transaction, invoice_data):
        """
        Add ApplicableHeaderTradeSettlement within SupplyChainTradeTransaction.

        Contains:
        - InvoiceCurrencyCode
        - SpecifiedTradeSettlementPaymentMeans
        - ApplicableTradeTax  (CII D16B: kommt VOR SpecifiedTradeAllowanceCharge)
        - SpecifiedTradeAllowanceCharge  (header level, nach ApplicableTradeTax)
        - SpecifiedTradePaymentTerms
        - SpecifiedTradeSettlementHeaderMonetarySummation

        Args:
            transaction: SupplyChainTradeTransaction element
            invoice_data: Invoice data dictionary
        """
        settlement = etree.SubElement(transaction, f"{{{RAM_NS}}}ApplicableHeaderTradeSettlement")

        # InvoiceCurrencyCode (required)
        currency = etree.SubElement(settlement, f"{{{RAM_NS}}}InvoiceCurrencyCode")
        currency.text = invoice_data.get("currency", "EUR")

        # InvoiceReferencedDocument (BT-25/BT-26) — for credit notes referencing original invoice
        inv_ref = invoice_data.get("invoice_referenced_document")
        if inv_ref:
            inv_ref_doc = etree.SubElement(settlement, f"{{{RAM_NS}}}InvoiceReferencedDocument")
            ref_id = etree.SubElement(inv_ref_doc, f"{{{RAM_NS}}}IssuerAssignedID")
            ref_id.text = inv_ref.get("issuer_assigned_id", "")
            ref_date = inv_ref.get("issue_date")
            if ref_date:
                ref_dt = etree.SubElement(inv_ref_doc, f"{{{RAM_NS}}}FormattedIssueDateTime")
                ref_date_str = etree.SubElement(ref_dt, f"{{{UDT_NS}}}DateTimeString")
                ref_date_str.set("format", "102")
                ref_date_str.text = ref_date

        # SpecifiedTradeSettlementPaymentMeans (IBAN/BIC – must come before ApplicableTradeTax)
        company_data = invoice_data.get("company", invoice_data.get("issuer", {}))
        if isinstance(company_data, dict):
            iban = company_data.get("iban")
            bic = company_data.get("bic")
        else:
            iban = getattr(company_data, "iban", None)
            bic = getattr(company_data, "bic", None)

        if iban:
            payment_means = etree.SubElement(settlement, f"{{{RAM_NS}}}SpecifiedTradeSettlementPaymentMeans")
            # TypeCode 58 = SEPA credit transfer
            type_code_el = etree.SubElement(payment_means, f"{{{RAM_NS}}}TypeCode")
            type_code_el.text = "58"
            creditor_account = etree.SubElement(payment_means, f"{{{RAM_NS}}}PayeePartyCreditorFinancialAccount")
            iban_el = etree.SubElement(creditor_account, f"{{{RAM_NS}}}IBANID")
            iban_el.text = iban
            if bic:
                creditor_institution = etree.SubElement(
                    payment_means, f"{{{RAM_NS}}}PayeeSpecifiedCreditorFinancialInstitution"
                )
                bic_el = etree.SubElement(creditor_institution, f"{{{RAM_NS}}}BICID")
                bic_el.text = bic

        # Compute proportionally-split allowances/charges for EN16931 BR-S-08 compliance.
        # When the invoice has multiple VAT rates, each header-level allowance/charge is
        # split into one element per rate (proportional share) so that the
        # SpecifiedTradeAllowanceCharge/CategoryTradeTax/RateApplicablePercent values match
        # the ApplicableTradeTax/BasisAmount computation exactly.
        items = invoice_data.get("items", [])
        line_tax_groups = self._compute_line_tax_groups(items)
        split_acs = self._split_allowances_charges_proportionally(
            invoice_data.get("allowances_charges", []), line_tax_groups
        )

        # ApplicableTradeTax (tax summary – kommt vor SpecifiedTradeAllowanceCharge in CII D16B)
        self._add_applicable_trade_tax(settlement, invoice_data, split_acs)

        # SpecifiedTradeAllowanceCharge (header level – kommt nach ApplicableTradeTax in CII D16B)
        # Write split entries (one per rate) when applicable, otherwise original entries.
        for ac in split_acs if split_acs else invoice_data.get("allowances_charges", []):
            self._add_header_allowance_charge(settlement, ac)

        # SpecifiedTradePaymentTerms
        due_date = invoice_data.get("due_date")
        if due_date:
            payment_terms = etree.SubElement(settlement, f"{{{RAM_NS}}}SpecifiedTradePaymentTerms")
            due_date_element = etree.SubElement(payment_terms, f"{{{RAM_NS}}}DueDateDateTime")
            date_str = etree.SubElement(due_date_element, f"{{{UDT_NS}}}DateTimeString")
            date_str.set("format", "102")
            if isinstance(due_date, str):
                date_str.text = "".join(c for c in due_date if c.isdigit())[:8]

        # SpecifiedTradeSettlementHeaderMonetarySummation (totals)
        self._add_monetary_summation(settlement, invoice_data, split_acs)

    def _compute_line_tax_groups(self, items):
        """
        Compute a dict of {tax_rate: total_line_amount} from invoice line items.

        Args:
            items: List of item dicts or item objects

        Returns:
            dict: {float tax_rate: float line_total}
        """
        tax_groups = {}
        for item in items:
            if isinstance(item, dict):
                tax_rate = float(item.get("tax_rate", 0))
                if "line_total" in item:
                    line_total = float(item["line_total"])
                else:
                    quantity = float(item.get("quantity", 1))
                    price = float(item.get("price", item.get("unit_price", 0)))
                    line_total = quantity * price
            else:
                tax_rate = float(getattr(item, "tax_rate", 0))
                line_total = float(getattr(item, "line_total", 0))
            tax_groups[tax_rate] = tax_groups.get(tax_rate, 0.0) + line_total
        return tax_groups

    def _split_allowances_charges_proportionally(self, allowances_charges, line_tax_groups):
        """
        Split each header-level allowance/charge proportionally across VAT-rate groups.

        EN16931 BR-S-08 requires that, for each VAT rate, the ApplicableTradeTax/BasisAmount
        equals the sum of line amounts PLUS per-rate charges MINUS per-rate allowances
        (determined from SpecifiedTradeAllowanceCharge/CategoryTradeTax/RateApplicablePercent).

        When a single header-level allowance/charge covers an invoice with multiple VAT rates
        it must therefore be split into one SpecifiedTradeAllowanceCharge element per rate,
        each carrying its proportional share of the original ActualAmount.

        If the invoice has only one tax rate the original entries are returned unchanged.

        Args:
            allowances_charges: list of allowance/charge dicts from invoice_data
            line_tax_groups: {tax_rate: line_total} as returned by _compute_line_tax_groups

        Returns:
            list: Split (or original) allowance/charge dicts
        """
        if not allowances_charges:
            return []
        if len(line_tax_groups) <= 1:
            # Single tax rate: enrich each entry with the rate so that
            # _add_applicable_trade_tax can match it to the correct tax group.
            single_rate = next(iter(line_tax_groups))
            enriched = []
            for ac in allowances_charges:
                copy = dict(ac)
                copy.setdefault("tax_rate", single_rate)
                enriched.append(copy)
            return enriched

        total = sum(line_tax_groups.values()) or 1.0
        rates = sorted(line_tax_groups.keys())
        result = []

        for ac in allowances_charges:
            original_amount = float(ac.get("actual_amount", 0))
            accumulated = 0.0
            for i, rate in enumerate(rates):
                share = line_tax_groups[rate] / total
                if i < len(rates) - 1:
                    split_amount = round(original_amount * share, 2)
                    accumulated += split_amount
                else:
                    # Last rate gets the remainder to avoid accumulated rounding errors.
                    split_amount = round(original_amount - accumulated, 2)

                if split_amount <= 0:
                    continue

                split_ac = dict(ac)  # shallow copy
                split_ac["actual_amount"] = split_amount
                split_ac["tax_rate"] = rate
                # calculation_percent / basis_amount are no longer meaningful after split
                split_ac["calculation_percent"] = None
                split_ac["basis_amount"] = None
                result.append(split_ac)

        return result

    def _add_header_allowance_charge(self, settlement, ac):
        """
        Add a SpecifiedTradeAllowanceCharge element at header level (EN16931 BG-20/BG-21).

        CII XSD sequence:
          ChargeIndicator → CalculationPercent? → BasisAmount? → ActualAmount
          → ReasonCode? → Reason? → CategoryTradeTax

        EN16931 BR-41: Either ReasonCode or Reason must be present.
        """
        is_charge = ac.get("is_charge", False)
        actual_amount = ac.get("actual_amount", 0)
        reason_code = ac.get("reason_code", "")
        reason = ac.get("reason", "")
        tax_rate = float(ac.get("tax_rate", 19))
        calculation_percent = ac.get("calculation_percent")
        basis_amount = ac.get("basis_amount")

        ac_el = etree.SubElement(settlement, f"{{{RAM_NS}}}SpecifiedTradeAllowanceCharge")

        # ChargeIndicator (required)
        indicator_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}ChargeIndicator")
        udt_indicator = etree.SubElement(indicator_el, f"{{{UDT_NS}}}Indicator")
        udt_indicator.text = "true" if is_charge else "false"

        # CalculationPercent (optional)
        if calculation_percent is not None:
            pct_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}CalculationPercent")
            pct_el.text = self._format_decimal(calculation_percent)

        # BasisAmount (optional)
        if basis_amount is not None:
            basis_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}BasisAmount")
            basis_el.text = self._format_decimal(basis_amount)

        # ActualAmount (required)
        amount_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}ActualAmount")
        amount_el.text = self._format_decimal(actual_amount)

        # ReasonCode (optional, EN16931 BR-41: at least one of ReasonCode/Reason required)
        if reason_code:
            rc_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}ReasonCode")
            rc_el.text = reason_code

        # Reason (free text)
        if reason:
            reason_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}Reason")
            reason_el.text = reason
        elif not reason_code:
            # BR-41: must have at least one of the two
            reason_el = etree.SubElement(ac_el, f"{{{RAM_NS}}}Reason")
            reason_el.text = "Charge" if is_charge else "Allowance"

        # CategoryTradeTax (required at header level)
        cat_tax = etree.SubElement(ac_el, f"{{{RAM_NS}}}CategoryTradeTax")
        type_code_el = etree.SubElement(cat_tax, f"{{{RAM_NS}}}TypeCode")
        type_code_el.text = "VAT"
        cat_code_el = etree.SubElement(cat_tax, f"{{{RAM_NS}}}CategoryCode")
        # Use explicit category code from A/C dict if available
        cat_code = ac.get("tax_category_code", "")
        if not cat_code:
            cat_code = "Z" if tax_rate == 0 else "S"
        cat_code_el.text = cat_code
        rate_el = etree.SubElement(cat_tax, f"{{{RAM_NS}}}RateApplicablePercent")
        rate_el.text = self._format_decimal(tax_rate)

    def _add_applicable_trade_tax(self, settlement, invoice_data, split_acs=None):
        """
        Add ApplicableTradeTax summary elements.

        EN16931 BR-CO-5: sum of all ApplicableTradeTax/BasisAmount must equal
        TaxBasisTotalAmount (= LineTotalAmount - AllowanceTotalAmount + ChargeTotalAmount).

        When split_acs is provided (non-empty list of per-rate allowance/charge dicts as
        returned by _split_allowances_charges_proportionally), the BasisAmount for each
        rate is computed as:
            sum(line totals for rate) + sum(charges for rate) - sum(allowances for rate)
        This ensures consistency with the SpecifiedTradeAllowanceCharge elements written
        in the same settlement (EN16931 BR-S-08).

        When split_acs is empty or None (no allowances/charges), a proportional
        distribution from invoice_data["charge_total"/"allowance_total"] is used as
        fallback to keep BR-CO-5 intact.

        Args:
            settlement: ApplicableHeaderTradeSettlement element
            invoice_data: Invoice data dictionary
            split_acs: Per-rate split allowance/charge dicts (from
                       _split_allowances_charges_proportionally), or None/[]
        """
        # Group items by tax rate AND category code (line totals only, before allowances/charges)
        tax_groups = {}
        items = invoice_data.get("items", [])

        for item in items:
            if isinstance(item, dict):
                tax_rate = float(item.get("tax_rate", 0))
                cat_code = item.get("tax_category_code", "")
                exemption_reason = item.get("tax_exemption_reason", "")
                if "line_total" in item:
                    line_total = float(item["line_total"])
                else:
                    quantity = float(item.get("quantity", 1))
                    price = float(item.get("price", item.get("unit_price", 0)))
                    line_total = quantity * price
            else:
                tax_rate = float(getattr(item, "tax_rate", 0))
                cat_code = getattr(item, "tax_category_code", "S")
                exemption_reason = getattr(item, "tax_exemption_reason", "")
                line_total = float(getattr(item, "line_total", 0))

            # Derive category code if not explicitly set
            if not cat_code:
                cat_code = "Z" if tax_rate == 0 else "S"

            group_key = (tax_rate, cat_code)
            if group_key not in tax_groups:
                tax_groups[group_key] = {"basis": 0, "tax": 0, "exemption_reason": exemption_reason}
            tax_groups[group_key]["basis"] += line_total

        if split_acs:
            # Per-rate adjustment: BasisAmount[rate] = line_total[rate]
            #                                          + charges_for_rate - allowances_for_rate
            # This is exactly what BR-S-08 checks against the SpecifiedTradeAllowanceCharge
            # elements written in the same settlement block.
            for ac in split_acs:
                ac_rate = float(ac.get("tax_rate", 0))
                ac_amount = float(ac.get("actual_amount", 0))
                is_charge = ac.get("is_charge", False)
                # Find matching group key by rate (category should match)
                matching_keys = [k for k in tax_groups if k[0] == ac_rate]
                for key in matching_keys:
                    if is_charge:
                        tax_groups[key]["basis"] += ac_amount / len(matching_keys)
                    else:
                        tax_groups[key]["basis"] -= ac_amount / len(matching_keys)
            for group_key, amounts in tax_groups.items():
                tax_rate = group_key[0]
                amounts["tax"] = amounts["basis"] * (tax_rate / 100)
        else:
            # Fallback: distribute allowances/charges proportionally across tax groups
            # so that sum(BasisAmount) == TaxBasisTotalAmount (EN16931 BR-CO-5).
            charge_total = float(invoice_data.get("charge_total", 0))
            allowance_total = float(invoice_data.get("allowance_total", 0))
            net_adjustment = charge_total - allowance_total  # positive = surcharge, negative = discount
            total_line_amount = sum(g["basis"] for g in tax_groups.values())

            for group_key, amounts in tax_groups.items():
                tax_rate = group_key[0]
                if total_line_amount != 0:
                    share = amounts["basis"] / total_line_amount
                else:
                    share = 1.0 / len(tax_groups) if tax_groups else 0
                adjusted_basis = amounts["basis"] + net_adjustment * share
                amounts["basis"] = adjusted_basis
                amounts["tax"] = adjusted_basis * (tax_rate / 100)

        # Add ApplicableTradeTax for each tax rate group
        for group_key, amounts in tax_groups.items():
            tax_rate, cat_code = group_key
            tax_element = etree.SubElement(settlement, f"{{{RAM_NS}}}ApplicableTradeTax")

            # CalculatedAmount
            calc_amount = etree.SubElement(tax_element, f"{{{RAM_NS}}}CalculatedAmount")
            calc_amount.text = self._format_decimal(amounts["tax"])

            # TypeCode
            type_code = etree.SubElement(tax_element, f"{{{RAM_NS}}}TypeCode")
            type_code.text = "VAT"

            # ExemptionReason (required for AE/G/E categories per EN16931)
            exemption_reason = amounts.get("exemption_reason", "")
            if exemption_reason and cat_code in ("AE", "G", "E"):
                exemption_el = etree.SubElement(tax_element, f"{{{RAM_NS}}}ExemptionReason")
                exemption_el.text = exemption_reason

            # BasisAmount
            basis = etree.SubElement(tax_element, f"{{{RAM_NS}}}BasisAmount")
            basis.text = self._format_decimal(amounts["basis"])

            # CategoryCode
            category = etree.SubElement(tax_element, f"{{{RAM_NS}}}CategoryCode")
            category.text = cat_code

            # RateApplicablePercent
            rate = etree.SubElement(tax_element, f"{{{RAM_NS}}}RateApplicablePercent")
            rate.text = self._format_decimal(tax_rate)

    def _add_monetary_summation(self, settlement, invoice_data, split_acs=None):
        """
        Add SpecifiedTradeSettlementHeaderMonetarySummation.

        Args:
            settlement: ApplicableHeaderTradeSettlement element
            invoice_data: Invoice data dictionary
            split_acs: Per-rate split allowance/charge dicts (from
                       _split_allowances_charges_proportionally), or None/[]
        """
        summation = etree.SubElement(settlement, f"{{{RAM_NS}}}SpecifiedTradeSettlementHeaderMonetarySummation")

        # Calculate totals
        line_total = 0
        items = invoice_data.get("items", [])
        tax_groups: dict[float, float] = {}  # tax_rate -> sum of item line totals

        for item in items:
            if isinstance(item, dict):
                tax_rate = float(item.get("tax_rate", 0))
                if "line_total" in item:
                    item_line = float(item["line_total"])
                else:
                    quantity = float(item.get("quantity", 1))
                    price = float(item.get("price", item.get("unit_price", 0)))
                    item_line = quantity * price
            else:
                item_line = float(getattr(item, "line_total", 0))
                tax_rate = float(getattr(item, "tax_rate", 0))

            line_total += item_line
            tax_groups[tax_rate] = tax_groups.get(tax_rate, 0.0) + item_line

        charge_total = float(invoice_data.get("charge_total", 0))
        allowance_total = float(invoice_data.get("allowance_total", 0))
        tax_basis = line_total - allowance_total + charge_total

        # EN16931 BR-CO-14: TaxTotalAmount = Σ ApplicableTradeTax/CalculatedAmount.
        # Must use the same BasisAmount logic as _add_applicable_trade_tax.
        tax_total = 0.0
        if split_acs:
            # Per-rate adjustment: same logic as _add_applicable_trade_tax when split_acs given.
            for rate, group_basis in tax_groups.items():
                charges_for_rate = sum(
                    float(ac["actual_amount"])
                    for ac in split_acs
                    if float(ac.get("tax_rate", 0)) == rate and ac.get("is_charge", False)
                )
                allowances_for_rate = sum(
                    float(ac["actual_amount"])
                    for ac in split_acs
                    if float(ac.get("tax_rate", 0)) == rate and not ac.get("is_charge", False)
                )
                adjusted_basis = group_basis + charges_for_rate - allowances_for_rate
                # BR-CO-14: round each contribution individually, matching the
                # per-rate CalculatedAmount written by _add_applicable_trade_tax.
                tax_total += round(adjusted_basis * (rate / 100), 2)
        else:
            # Fallback: proportional distribution (used when no explicit allowances_charges).
            net_adjustment = charge_total - allowance_total
            total_line_amount = sum(tax_groups.values()) or 1.0
            for rate, group_basis in tax_groups.items():
                share = group_basis / total_line_amount
                adjusted_basis = group_basis + net_adjustment * share
                # BR-CO-14: round each contribution individually, matching the
                # per-rate CalculatedAmount written by _add_applicable_trade_tax.
                tax_total += round(adjusted_basis * (rate / 100), 2)

        grand_total = tax_basis + tax_total

        # LineTotalAmount
        line_elem = etree.SubElement(summation, f"{{{RAM_NS}}}LineTotalAmount")
        line_elem.text = self._format_decimal(line_total)

        # ChargeTotalAmount
        charge_elem = etree.SubElement(summation, f"{{{RAM_NS}}}ChargeTotalAmount")
        charge_elem.text = self._format_decimal(charge_total)

        # AllowanceTotalAmount
        allow_elem = etree.SubElement(summation, f"{{{RAM_NS}}}AllowanceTotalAmount")
        allow_elem.text = self._format_decimal(allowance_total)

        # TaxBasisTotalAmount
        tax_basis_elem = etree.SubElement(summation, f"{{{RAM_NS}}}TaxBasisTotalAmount")
        tax_basis_elem.text = self._format_decimal(tax_basis)

        # TaxTotalAmount with currencyID
        tax_total_elem = etree.SubElement(summation, f"{{{RAM_NS}}}TaxTotalAmount")
        tax_total_elem.set("currencyID", invoice_data.get("currency", "EUR"))
        tax_total_elem.text = self._format_decimal(tax_total)

        # GrandTotalAmount
        grand_elem = etree.SubElement(summation, f"{{{RAM_NS}}}GrandTotalAmount")
        grand_elem.text = self._format_decimal(grand_total)

        # DuePayableAmount
        due_elem = etree.SubElement(summation, f"{{{RAM_NS}}}DuePayableAmount")
        due_elem.text = self._format_decimal(grand_total)

    def _add_included_supply_chain_trade_line_items(self, transaction, invoice_data):
        """
        Add IncludedSupplyChainTradeLineItem elements within SupplyChainTradeTransaction.

        Args:
            transaction: SupplyChainTradeTransaction element
            invoice_data: Invoice data dictionary
        """
        items = invoice_data.get("items", [])

        for idx, item in enumerate(items, start=1):
            line_item = etree.SubElement(transaction, f"{{{RAM_NS}}}IncludedSupplyChainTradeLineItem")

            # AssociatedDocumentLineDocument (line number)
            doc_line = etree.SubElement(line_item, f"{{{RAM_NS}}}AssociatedDocumentLineDocument")
            line_id = etree.SubElement(doc_line, f"{{{RAM_NS}}}LineID")
            line_id.text = str(idx)

            # SpecifiedTradeProduct
            self._add_specified_trade_product(line_item, item)

            # SpecifiedLineTradeAgreement
            self._add_specified_line_trade_agreement(line_item, item)

            # SpecifiedLineTradeDelivery
            self._add_specified_line_trade_delivery(line_item, item)

            # SpecifiedLineTradeSettlement
            self._add_specified_line_trade_settlement(line_item, item)

    def _add_specified_trade_product(self, line_item, item):
        """Add SpecifiedTradeProduct to line item."""
        product_element = etree.SubElement(line_item, f"{{{RAM_NS}}}SpecifiedTradeProduct")

        # Add product name
        name_element = etree.SubElement(product_element, f"{{{RAM_NS}}}Name")
        if isinstance(item, dict):
            product_name = item.get("product_name", item.get("description", "Unknown Product"))
        else:
            # Model instance
            product_name = getattr(item, "description", "Unknown Product")
        name_element.text = product_name

    def _add_specified_line_trade_agreement(self, line_item, item):
        """Add SpecifiedLineTradeAgreement (price information) to line item."""
        agreement_element = etree.SubElement(line_item, f"{{{RAM_NS}}}SpecifiedLineTradeAgreement")

        # NetPriceProductTradePrice
        net_price_element = etree.SubElement(agreement_element, f"{{{RAM_NS}}}NetPriceProductTradePrice")

        # ChargeAmount (unit price) - MUST come before BasisQuantity per schema
        charge_amount_element = etree.SubElement(net_price_element, f"{{{RAM_NS}}}ChargeAmount")
        if isinstance(item, dict):
            price = item.get("price", item.get("unit_price", 0))
        else:
            price = getattr(item, "unit_price", 0)
        charge_amount_element.text = self._format_decimal(price)

        # BasisQuantity with unitCode attribute (optional, defaults to 1)
        basis_qty_element = etree.SubElement(net_price_element, f"{{{RAM_NS}}}BasisQuantity")
        if isinstance(item, dict):
            unit_of_measure = item.get("unit_of_measure", "PCE")
            unit_code = self._map_unit_code(unit_of_measure)
        else:
            unit_code = getattr(item, "unit_code", "C62")
        basis_qty_element.set("unitCode", unit_code)
        basis_qty_element.text = "1"

    def _add_specified_line_trade_delivery(self, line_item, item):
        """Add SpecifiedLineTradeDelivery (quantity information) to line item."""
        delivery_element = etree.SubElement(line_item, f"{{{RAM_NS}}}SpecifiedLineTradeDelivery")

        # BilledQuantity with unitCode attribute (REQUIRED!)
        quantity_element = etree.SubElement(delivery_element, f"{{{RAM_NS}}}BilledQuantity")

        # Get unit code and quantity
        if isinstance(item, dict):
            quantity = item.get("quantity", 1)
            # Map unit_of_measure to UN/ECE code
            unit_of_measure = item.get("unit_of_measure", "PCE")
            unit_code = self._map_unit_code(unit_of_measure)
        else:
            quantity = getattr(item, "quantity", 1)
            unit_code = getattr(item, "unit_code", "C62")

        # Set unitCode attribute (REQUIRED by XSD!)
        quantity_element.set("unitCode", unit_code)
        quantity_element.text = self._format_decimal(quantity, decimals=2)

    def _add_specified_line_trade_settlement(self, line_item, item):
        """Add SpecifiedLineTradeSettlement (tax and totals) to line item."""
        settlement_element = etree.SubElement(line_item, f"{{{RAM_NS}}}SpecifiedLineTradeSettlement")

        # ApplicableTradeTax
        tax_element = etree.SubElement(settlement_element, f"{{{RAM_NS}}}ApplicableTradeTax")

        # TypeCode (always VAT for now)
        type_code = etree.SubElement(tax_element, f"{{{RAM_NS}}}TypeCode")
        type_code.text = "VAT"

        # CategoryCode (S, Z, E, AE, G)
        category_code = etree.SubElement(tax_element, f"{{{RAM_NS}}}CategoryCode")
        if isinstance(item, dict):
            # Use explicit tax_category_code if provided, else derive from rate
            category = item.get("tax_category_code", "")
            if not category:
                tax_rate = float(item.get("tax_rate", 0))
                if tax_rate == 0:
                    category = "Z"
                else:
                    category = "S"
        else:
            category = getattr(item, "tax_category_code", "S")
        category_code.text = category

        # ExemptionReason (required for AE=Reverse Charge, G=Export)
        if isinstance(item, dict):
            exemption_reason = item.get("tax_exemption_reason", "")
        else:
            exemption_reason = getattr(item, "tax_exemption_reason", "")
        if exemption_reason and category in ("AE", "G", "E"):
            exemption_el = etree.SubElement(tax_element, f"{{{RAM_NS}}}ExemptionReason")
            exemption_el.text = exemption_reason

        # RateApplicablePercent
        rate_element = etree.SubElement(tax_element, f"{{{RAM_NS}}}RateApplicablePercent")
        if isinstance(item, dict):
            tax_rate = item.get("tax_rate", 0)
        else:
            tax_rate = getattr(item, "tax_rate", 0)
        rate_element.text = self._format_decimal(tax_rate)

        # SpecifiedTradeAllowanceCharge at line level (if position discount present)
        if isinstance(item, dict):
            discount_amount = float(item.get("discount_amount", 0) or 0)
            discount_reason = item.get("discount_reason", "") or ""
        else:
            discount_amount = float(getattr(item, "discount_amount", 0) or 0)
            discount_reason = getattr(item, "discount_reason", "") or ""

        if discount_amount > 0:
            line_ac = etree.SubElement(settlement_element, f"{{{RAM_NS}}}SpecifiedTradeAllowanceCharge")
            indicator_el = etree.SubElement(line_ac, f"{{{RAM_NS}}}ChargeIndicator")
            udt_indicator = etree.SubElement(indicator_el, f"{{{UDT_NS}}}Indicator")
            udt_indicator.text = "false"
            actual_el = etree.SubElement(line_ac, f"{{{RAM_NS}}}ActualAmount")
            actual_el.text = self._format_decimal(discount_amount)
            reason_text = discount_reason if discount_reason else "Discount"
            reason_el = etree.SubElement(line_ac, f"{{{RAM_NS}}}Reason")
            reason_el.text = reason_text

        # SpecifiedTradeSettlementLineMonetarySummation
        summation_element = etree.SubElement(
            settlement_element, f"{{{RAM_NS}}}SpecifiedTradeSettlementLineMonetarySummation"
        )

        # LineTotalAmount: use precomputed line_total (after discounts) when available
        line_total_element = etree.SubElement(summation_element, f"{{{RAM_NS}}}LineTotalAmount")
        if isinstance(item, dict):
            if "line_total" in item:
                line_total = float(item["line_total"])
            else:
                quantity = float(item.get("quantity", 1))
                price = float(item.get("price", item.get("unit_price", 0)))
                line_total = quantity * price
        else:
            line_total = float(getattr(item, "line_total", 0))
        line_total_element.text = self._format_decimal(line_total)

    def _format_decimal(self, value, decimals=2):
        """Format decimal value to string with specified decimal places."""
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return f"{0:.{decimals}f}"

    def _map_unit_code(self, unit_of_measure):
        """
        Gibt den UN/CEFACT Rec. 20 Code zurück.

        Akzeptiert:
        - int: interne ID aus Product.UnitOfMeasure (1=Stück, 2=Stunde, ...)
        - str: UN/CEFACT-Code oder Alias ("PCE", "MTR", ...) für direkte Aufrufe

        Returns:
            str: UN/CEFACT Rec. 20 Code (z.B. "C62", "HUR")
        """
        if isinstance(unit_of_measure, int):
            return UNIT_CODE_MAP.get(unit_of_measure, "C62")
        if isinstance(unit_of_measure, str) and unit_of_measure:
            return UNIT_CODE_MAP.get(unit_of_measure.upper(), unit_of_measure.upper())
        return "C62"
