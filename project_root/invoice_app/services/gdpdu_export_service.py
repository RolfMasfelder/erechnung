"""
GDPdU / IDEA export service.

Implements an export in the format required by the German Bundesministerium der
Finanzen for tax audits (GDPdU/GoBD §147 AO), structured per the BMF
"Beschreibungsstandard für die Datenträgerüberlassung" v0.6 (2018), which uses
the same DTD-based ``index.xml`` describing one or more CSV data tables.

The exporter produces a single in-memory ZIP archive with:

* ``index.xml``           — table catalogue per ``gdpdu-01-09-2004.dtd``
* ``invoices.csv``        — invoice header rows
* ``invoice_lines.csv``   — invoice line items
* ``business_partners.csv`` — referenced customers / suppliers

CSV files use ``;`` as column delimiter, ``"`` as text quoting, ISO-8601 dates
and ``.`` as decimal separator — matching the values declared in ``index.xml``.

The service deliberately keeps everything synchronous — see ADR-025
(``docs/arc42/adrs/ADR-025-import-export-async-and-audit.md``).
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable
from xml.sax.saxutils import escape as _xml_escape

from django.utils import timezone

from invoice_app.models import BusinessPartner, Invoice, InvoiceLine

# CSV dialect — must match what is declared in index.xml.
_CSV_DELIMITER = ";"
_CSV_QUOTECHAR = '"'
_CSV_RECORD_DELIMITER = "\r\n"
_CSV_DECIMAL = "."

# DTD identifier used by GDPdU/IDEA (BMF "gdpdu-01-09-2004.dtd").
_DTD_SYSTEM_ID = "gdpdu-01-09-2004.dtd"


# ---------------------------------------------------------------------------
# Schema description
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Column:
    """Description of a single CSV column for the index.xml."""

    name: str
    description: str
    kind: str  # "Numeric" or "AlphaNumeric"
    max_length: int | None = None
    accuracy: int | None = None  # number of decimal places (numeric only)


@dataclass(frozen=True)
class _Table:
    """Description of a single CSV table file for the index.xml."""

    name: str
    description: str
    url: str
    columns: tuple[_Column, ...]


_INVOICE_COLUMNS: tuple[_Column, ...] = (
    _Column("invoice_number", "Rechnungsnummer", "AlphaNumeric", max_length=50),
    _Column("invoice_type", "Rechnungstyp (380=Rechnung, 381=Gutschrift)", "AlphaNumeric", max_length=10),
    _Column("issue_date", "Rechnungsdatum (ISO 8601)", "AlphaNumeric", max_length=10),
    _Column("due_date", "Fälligkeitsdatum (ISO 8601)", "AlphaNumeric", max_length=10),
    _Column("delivery_date", "Lieferdatum (ISO 8601, optional)", "AlphaNumeric", max_length=10),
    _Column("currency", "Währung (ISO 4217)", "AlphaNumeric", max_length=3),
    _Column("subtotal", "Nettobetrag", "Numeric", accuracy=2),
    _Column("tax_amount", "Umsatzsteuerbetrag", "Numeric", accuracy=2),
    _Column("total_amount", "Bruttobetrag", "Numeric", accuracy=2),
    _Column("status", "Status", "AlphaNumeric", max_length=20),
    _Column("company_tax_id", "Steuernummer Verkäufer", "AlphaNumeric", max_length=50),
    _Column("business_partner_id", "Geschäftspartner-ID (FK)", "Numeric", accuracy=0),
)

_INVOICE_LINE_COLUMNS: tuple[_Column, ...] = (
    _Column("invoice_number", "Rechnungsnummer (FK)", "AlphaNumeric", max_length=50),
    _Column("line_number", "Positionsnummer", "Numeric", accuracy=0),
    _Column("description", "Bezeichnung", "AlphaNumeric", max_length=255),
    _Column("product_code", "Artikelnummer", "AlphaNumeric", max_length=100),
    _Column("quantity", "Menge", "Numeric", accuracy=3),
    _Column("unit_price", "Einzelpreis netto", "Numeric", accuracy=6),
    _Column("tax_rate", "USt-Satz (%)", "Numeric", accuracy=2),
    _Column("tax_amount", "USt-Betrag", "Numeric", accuracy=2),
    _Column("tax_category", "USt-Kategorie (EN16931)", "AlphaNumeric", max_length=5),
    _Column("line_subtotal", "Positions-Nettobetrag", "Numeric", accuracy=2),
    _Column("line_total", "Positions-Bruttobetrag", "Numeric", accuracy=2),
)

_BUSINESS_PARTNER_COLUMNS: tuple[_Column, ...] = (
    _Column("id", "Geschäftspartner-ID", "Numeric", accuracy=0),
    _Column("partner_number", "Partnernummer", "AlphaNumeric", max_length=50),
    _Column("partner_type", "Partnertyp (CO/IN)", "AlphaNumeric", max_length=10),
    _Column("company_name", "Firmenname", "AlphaNumeric", max_length=255),
    _Column("legal_name", "Rechtlicher Name", "AlphaNumeric", max_length=255),
    _Column("first_name", "Vorname", "AlphaNumeric", max_length=100),
    _Column("last_name", "Nachname", "AlphaNumeric", max_length=100),
    _Column("tax_id", "Steuernummer", "AlphaNumeric", max_length=50),
    _Column("vat_id", "USt-IdNr.", "AlphaNumeric", max_length=50),
    _Column("street", "Straße", "AlphaNumeric", max_length=255),
    _Column("postal_code", "PLZ", "AlphaNumeric", max_length=20),
    _Column("city", "Ort", "AlphaNumeric", max_length=100),
    _Column("country_code", "Länder-Code (ISO 3166-1 alpha-2)", "AlphaNumeric", max_length=2),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_period(start_date: date, end_date: date) -> bytes:
    """
    Return a GDPdU/IDEA ZIP archive covering invoices in ``[start_date, end_date]``.

    Both bounds are inclusive and matched against ``Invoice.issue_date``.
    """
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    invoices = list(
        Invoice.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date)
        .select_related("company", "business_partner", "business_partner__country")
        .order_by("issue_date", "invoice_number")
    )

    invoice_ids = [inv.pk for inv in invoices]
    lines = list(
        InvoiceLine.objects.filter(invoice_id__in=invoice_ids)
        .select_related("invoice")
        .order_by("invoice_id", "pk")
    )

    partner_ids = {inv.business_partner_id for inv in invoices if inv.business_partner_id}
    partners = list(
        BusinessPartner.objects.filter(pk__in=partner_ids)
        .select_related("country")
        .order_by("pk")
    )

    invoice_csv = _render_invoice_csv(invoices)
    lines_csv = _render_invoice_line_csv(lines)
    partners_csv = _render_business_partner_csv(partners)
    index_xml = _render_index_xml(start_date, end_date)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.xml", index_xml)
        zf.writestr("invoices.csv", invoice_csv)
        zf.writestr("invoice_lines.csv", lines_csv)
        zf.writestr("business_partners.csv", partners_csv)

    return buffer.getvalue()


# ---------------------------------------------------------------------------
# CSV rendering helpers
# ---------------------------------------------------------------------------


def _format_decimal(value: Decimal | float | int | None, accuracy: int) -> str:
    if value is None:
        return ""
    return f"{Decimal(value):.{accuracy}f}"


def _format_date(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()


def _write_csv(rows: Iterable[list[str]]) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(
        out,
        delimiter=_CSV_DELIMITER,
        quotechar=_CSV_QUOTECHAR,
        quoting=csv.QUOTE_MINIMAL,
        lineterminator=_CSV_RECORD_DELIMITER,
    )
    for row in rows:
        writer.writerow(row)
    return out.getvalue()


def _render_invoice_csv(invoices: Iterable[Invoice]) -> str:
    rows: list[list[str]] = []
    for inv in invoices:
        rows.append(
            [
                inv.invoice_number,
                inv.invoice_type or "",
                _format_date(inv.issue_date),
                _format_date(inv.due_date),
                _format_date(inv.delivery_date),
                inv.currency or "",
                _format_decimal(inv.subtotal, 2),
                _format_decimal(inv.tax_amount, 2),
                _format_decimal(inv.total_amount, 2),
                inv.status or "",
                (inv.company.tax_id if inv.company_id else "") or "",
                str(inv.business_partner_id) if inv.business_partner_id else "",
            ]
        )
    return _write_csv(rows)


def _render_invoice_line_csv(lines: Iterable[InvoiceLine]) -> str:
    rows: list[list[str]] = []
    line_counter: dict[int, int] = {}
    for line in lines:
        line_counter[line.invoice_id] = line_counter.get(line.invoice_id, 0) + 1
        rows.append(
            [
                line.invoice.invoice_number,
                str(line_counter[line.invoice_id]),
                line.description or "",
                line.product_code or "",
                _format_decimal(line.quantity, 3),
                _format_decimal(line.unit_price, 6),
                _format_decimal(line.tax_rate, 2),
                _format_decimal(line.tax_amount, 2),
                line.tax_category or "",
                _format_decimal(line.line_subtotal, 2),
                _format_decimal(line.line_total, 2),
            ]
        )
    return _write_csv(rows)


def _render_business_partner_csv(partners: Iterable[BusinessPartner]) -> str:
    rows: list[list[str]] = []
    for bp in partners:
        country_code = ""
        if bp.country_id:
            # Country.code is the ISO 3166-1 alpha-2 code (see countries fixture).
            country_code = getattr(bp.country, "code", "") or ""
        rows.append(
            [
                str(bp.pk),
                bp.partner_number or "",
                bp.partner_type or "",
                bp.company_name or "",
                bp.legal_name or "",
                bp.first_name or "",
                bp.last_name or "",
                bp.tax_id or "",
                bp.vat_id or "",
                bp.address_line1 or "",
                bp.postal_code or "",
                bp.city or "",
                country_code,
            ]
        )
    return _write_csv(rows)


# ---------------------------------------------------------------------------
# index.xml rendering
# ---------------------------------------------------------------------------


def _render_column(col: _Column) -> str:
    name = _xml_escape(col.name)
    desc = _xml_escape(col.description)
    if col.kind == "Numeric":
        accuracy = col.accuracy if col.accuracy is not None else 0
        return (
            f"      <VariableColumn>\n"
            f"        <Name>{name}</Name>\n"
            f"        <Description>{desc}</Description>\n"
            f"        <Numeric>\n"
            f"          <Accuracy>{accuracy}</Accuracy>\n"
            f"        </Numeric>\n"
            f"      </VariableColumn>"
        )
    max_len = col.max_length or 255
    return (
        f"      <VariableColumn>\n"
        f"        <Name>{name}</Name>\n"
        f"        <Description>{desc}</Description>\n"
        f"        <AlphaNumeric>\n"
        f"          <MaxLength>{max_len}</MaxLength>\n"
        f"        </AlphaNumeric>\n"
        f"      </VariableColumn>"
    )


def _render_table(table: _Table) -> str:
    columns_xml = "\n".join(_render_column(c) for c in table.columns)
    return (
        f"  <Table>\n"
        f"    <URL>{_xml_escape(table.url)}</URL>\n"
        f"    <Name>{_xml_escape(table.name)}</Name>\n"
        f"    <Description>{_xml_escape(table.description)}</Description>\n"
        f"    <VariableLength>\n"
        f"      <ColumnDelimiter>;</ColumnDelimiter>\n"
        f"      <RecordDelimiter>{{CR}}{{LF}}</RecordDelimiter>\n"
        f"      <TextEncapsulator>&quot;</TextEncapsulator>\n"
        f"      <DecimalSymbol>{_CSV_DECIMAL}</DecimalSymbol>\n"
        f"      <DigitGroupingSymbol></DigitGroupingSymbol>\n"
        f"{columns_xml}\n"
        f"    </VariableLength>\n"
        f"  </Table>"
    )


def _render_index_xml(start_date: date, end_date: date) -> str:
    tables = (
        _Table("invoices", "Rechnungsköpfe", "invoices.csv", _INVOICE_COLUMNS),
        _Table("invoice_lines", "Rechnungspositionen", "invoice_lines.csv", _INVOICE_LINE_COLUMNS),
        _Table(
            "business_partners",
            "Geschäftspartner (Kunden/Lieferanten)",
            "business_partners.csv",
            _BUSINESS_PARTNER_COLUMNS,
        ),
    )
    body = "\n".join(_render_table(t) for t in tables)
    created = timezone.now().strftime("%Y-%m-%d")
    period = f"{start_date.isoformat()} – {end_date.isoformat()}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!DOCTYPE DataSet SYSTEM "{_DTD_SYSTEM_ID}">\n'
        f"<DataSet>\n"
        f"  <Version>1.0</Version>\n"
        f"  <DataSupplier>\n"
        f"    <Name>eRechnung</Name>\n"
        f"    <Location>self-hosted</Location>\n"
        f"    <Comment>GDPdU/IDEA-Export für Zeitraum {_xml_escape(period)}</Comment>\n"
        f"  </DataSupplier>\n"
        f"  <Media>\n"
        f"    <Name>Rechnungsdaten {_xml_escape(period)}</Name>\n"
        f"    <Created>{created}</Created>\n"
        f"{body}\n"
        f"  </Media>\n"
        f"</DataSet>\n"
    )
