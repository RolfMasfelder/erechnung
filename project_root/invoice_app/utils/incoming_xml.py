"""
Incoming XML utilities for processing ZUGFeRD/Factur-X invoices.

This module provides utilities for extracting structured data from incoming
supplier invoices in ZUGFeRD/Factur-X format.
"""

from datetime import datetime

from lxml import etree


# Constants
PLACEHOLDER_TEXT = "[To be updated]"
DEFAULT_POSTAL_CODE = "00000"
DEFAULT_COUNTRY = "DE"


class IncomingXmlParser:
    """
    Parser for extracting data from incoming ZUGFeRD/Factur-X XML invoices.

    This utility focuses on parsing XML from supplier invoices and extracting
    the data needed to create Invoice records in our system.
    """

    # ZUGFeRD/Factur-X namespaces
    NAMESPACES = {
        "inv": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
        "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    }

    def extract_invoice_data(self, xml_content: str) -> dict:
        """
        Extract invoice data from ZUGFeRD/Factur-X XML content.

        Args:
            xml_content (str): ZUGFeRD/Factur-X XML content

        Returns:
            dict: Extracted invoice data with keys:
                - invoice_number: str
                - issue_date: str (YYYY-MM-DD format)
                - type_code: str
                - seller_name: str
                - seller_id: str
                - buyer_name: str
                - total_amount: float
                - tax_amount: float
                - currency: str
                - line_items: list[dict]
        """
        try:
            # Parse XML
            root = etree.fromstring(xml_content.encode("utf-8"))

            # Extract basic invoice information
            invoice_data = {}

            # Invoice ID
            invoice_data["invoice_number"] = self._extract_text(root, ".//inv:Header/inv:ID", default="")

            # Issue Date
            issue_date_elem = root.find(".//inv:Header/inv:IssueDateTime/udt:DateTimeString", self.NAMESPACES)
            invoice_data["issue_date"] = self._parse_date(issue_date_elem)

            # Invoice Type
            invoice_data["type_code"] = self._extract_text(root, ".//inv:Header/inv:TypeCode", default="380")

            # Seller Information (supplier)
            invoice_data["seller_name"] = self._extract_text(root, ".//inv:SellerTradeParty/ram:Name", default="")
            invoice_data["seller_id"] = self._extract_text(root, ".//inv:SellerTradeParty/ram:ID", default="")

            # Buyer Information (us)
            invoice_data["buyer_name"] = self._extract_text(root, ".//inv:BuyerTradeParty/ram:Name", default="")

            # Financial totals
            invoice_data["total_amount"] = self._extract_amount(root, ".//inv:DocumentTotals/inv:GrandTotal")
            invoice_data["tax_amount"] = self._extract_amount(root, ".//inv:DocumentTotals/inv:TaxTotal")

            # Currency
            invoice_data["currency"] = self._extract_text(
                root, ".//inv:DocumentTotals/inv:InvoiceCurrencyCode", default="EUR"
            )

            # Line Items
            invoice_data["line_items"] = self._extract_line_items(root)

            # AdditionalReferencedDocument entries (supporting documents referenced in XML)
            invoice_data["additional_referenced_documents"] = self._extract_additional_referenced_documents(root)

            return invoice_data

        except Exception as e:
            raise ValueError(f"Error extracting invoice data from XML: {e}") from e

    def _extract_text(self, root, xpath: str, default: str = "") -> str:
        """Extract text from XML element using XPath."""
        elem = root.find(xpath, self.NAMESPACES)
        return elem.text if elem is not None else default

    def _extract_amount(self, root, xpath: str, default: float = 0.0) -> float:
        """Extract amount from XML element."""
        elem = root.find(xpath, self.NAMESPACES)
        if elem is not None:
            try:
                return float(elem.text)
            except (ValueError, TypeError):
                pass
        return default

    def _parse_date(self, date_elem) -> str:
        """Parse date from XML element to YYYY-MM-DD format."""
        if date_elem is None:
            return datetime.now().date().isoformat()

        date_str = date_elem.text

        # Handle YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # Handle other formats
        try:
            # Try parsing various date formats
            for fmt in ("%Y-%m-%d", "%Y%m%d", "%d.%m.%Y", "%d/%m/%Y"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
        except Exception:
            pass

        # Fallback to current date
        return datetime.now().date().isoformat()

    def _extract_line_items(self, root) -> list[dict]:
        """Extract line items from invoice XML."""
        line_items = []
        line_item_elems = root.findall(".//inv:LineItem", self.NAMESPACES)

        for line_elem in line_item_elems:
            line_data = {}

            # Description
            line_data["description"] = self._extract_text(line_elem, ".//inv:Description", default="")

            # Quantity
            line_data["quantity"] = self._extract_amount(line_elem, ".//inv:Quantity", default=0.0)

            # Unit Price
            line_data["unit_price"] = self._extract_amount(line_elem, ".//inv:UnitPrice", default=0.0)

            # Line Total (if available)
            line_data["line_total"] = self._extract_amount(
                line_elem, ".//inv:LineTotal", default=line_data["quantity"] * line_data["unit_price"]
            )

            line_items.append(line_data)

        return line_items

    def _extract_additional_referenced_documents(self, root) -> list[dict]:
        """
        Extract AdditionalReferencedDocument entries from CII XML.

        These represent supporting documents (Lieferscheine, Zeitaufstellungen etc.)
        referenced via BG-24 / BT-122..BT-125 in the invoice XML.

        Returns a list of dicts with:
          - filename (str): Referenced filename (BT-125)
          - type_code (str): Document type code, e.g. '916' for supporting document
          - issuer_assigned_id (str): Document reference ID (BT-122)
          - description (str): Document description (BT-123)
          - external_uri (str): External URL (BT-124), if any
        """
        docs = []
        ns = self.NAMESPACES

        # CII path: SupplyChainTradeTransaction > ApplicableHeaderTradeAgreement
        #            > AdditionalReferencedDocument
        doc_elems = root.findall(".//ram:ApplicableHeaderTradeAgreement/ram:AdditionalReferencedDocument", ns)

        if not doc_elems:
            # Try broader search in case namespace nesting differs
            doc_elems = root.findall(".//ram:AdditionalReferencedDocument", ns)

        for doc_elem in doc_elems:
            doc = {
                "issuer_assigned_id": "",
                "type_code": "",
                "description": "",
                "filename": "",
                "external_uri": "",
            }

            # BT-122: IssuerAssignedID
            id_elem = doc_elem.find("ram:IssuerAssignedID", ns)
            if id_elem is not None and id_elem.text:
                doc["issuer_assigned_id"] = id_elem.text

            # TypeCode (e.g. 916 = supporting document)
            type_elem = doc_elem.find("ram:TypeCode", ns)
            if type_elem is not None and type_elem.text:
                doc["type_code"] = type_elem.text

            # BT-123: Name / Description
            name_elem = doc_elem.find("ram:Name", ns)
            if name_elem is not None and name_elem.text:
                doc["description"] = name_elem.text

            # BT-125: AttachmentBinaryObject@filename
            binary_elem = doc_elem.find("ram:AttachmentBinaryObject", ns)
            if binary_elem is not None:
                doc["filename"] = binary_elem.get("filename", "")

            # BT-124: URIID (external reference)
            uri_elem = doc_elem.find("ram:URIID", ns)
            if uri_elem is not None and uri_elem.text:
                doc["external_uri"] = uri_elem.text

            docs.append(doc)

        return docs


class SupplierDataExtractor:
    """
    Utility for extracting and normalizing supplier information from incoming invoices.
    """

    def extract_supplier_info(self, xml_content: str) -> dict:
        """
        Extract comprehensive supplier information from XML.

        Args:
            xml_content (str): ZUGFeRD/Factur-X XML content

        Returns:
            dict: Supplier data suitable for Company model creation
        """
        try:
            root = etree.fromstring(xml_content.encode("utf-8"))
            ns = IncomingXmlParser.NAMESPACES

            supplier_data = {}

            # Basic information
            supplier_data["name"] = self._extract_text(root, ".//inv:SellerTradeParty/ram:Name", default="")

            # Tax/Registration numbers
            supplier_data["tax_id"] = self._extract_text(
                root, ".//inv:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", default=""
            )

            # Address information
            address_elem = root.find(".//inv:SellerTradeParty/ram:PostalTradeAddress", ns)
            if address_elem is not None:
                supplier_data["address_line1"] = self._extract_text(
                    address_elem, ".//ram:LineOne", default=PLACEHOLDER_TEXT
                )
                supplier_data["city"] = self._extract_text(address_elem, ".//ram:CityName", default=PLACEHOLDER_TEXT)
                supplier_data["postal_code"] = self._extract_text(
                    address_elem, ".//ram:PostcodeCode", default=DEFAULT_POSTAL_CODE
                )
                supplier_data["country"] = self._extract_text(
                    address_elem, ".//ram:CountryID", default=DEFAULT_COUNTRY
                )
            else:
                # Defaults for missing address
                supplier_data.update(
                    {
                        "address_line1": PLACEHOLDER_TEXT,
                        "city": PLACEHOLDER_TEXT,
                        "postal_code": DEFAULT_POSTAL_CODE,
                        "country": DEFAULT_COUNTRY,
                    }
                )

            # Contact information
            contact_elem = root.find(".//inv:SellerTradeParty/ram:DefinedTradeContact", ns)
            if contact_elem is not None:
                supplier_data["email"] = self._extract_text(
                    contact_elem, ".//ram:EmailURIUniversalCommunication/ram:URIID", default=""
                )
                supplier_data["phone"] = self._extract_text(
                    contact_elem, ".//ram:TelephoneUniversalCommunication/ram:CompleteNumber", default=""
                )
            else:
                supplier_data.update(
                    {
                        "email": "",
                        "phone": "",
                    }
                )

            # Note: Removed is_supplier field - doesn't exist in Company model
            # Company records are suppliers by virtue of being in supplier invoices

            return supplier_data

        except Exception as e:
            raise ValueError(f"Error extracting supplier data from XML: {e}") from e

    def _extract_text(self, element_or_root, xpath: str, default: str = "") -> str:
        """Extract text from XML element using XPath."""
        ns = IncomingXmlParser.NAMESPACES
        elem = element_or_root.find(xpath, ns)
        return elem.text if elem is not None else default
