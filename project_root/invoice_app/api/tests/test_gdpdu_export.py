"""
Tests for the GDPdU/IDEA export endpoint and service.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from invoice_app.models import (
    AuditLog,
    BusinessPartner,
    Company,
    Country,
    Invoice,
    InvoiceLine,
)
from invoice_app.services.gdpdu_export_service import export_period
from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


@pytest.fixture
def germany(db):
    return Country.objects.get_or_create(
        code="DE",
        defaults={
            "code_alpha3": "DEU",
            "numeric_code": "276",
            "name": "Germany",
            "name_local": "Deutschland",
            "currency_code": "EUR",
            "currency_name": "Euro",
            "currency_symbol": "€",
            "default_language": "de",
            "is_eu_member": True,
            "is_eurozone": True,
            "standard_vat_rate": Decimal("19.00"),
        },
    )[0]


@pytest.fixture
def company(db):
    return Company.objects.create(
        name="Acme GmbH",
        tax_id="DE111222333",
        vat_id="DE111222333",
        address_line1="Hauptstr. 1",
        postal_code="10115",
        city="Berlin",
        country="Germany",
        email="info@acme.example",
    )


@pytest.fixture
def partner(db, germany):
    return BusinessPartner.objects.create(
        partner_type=BusinessPartner.PartnerType.BUSINESS,
        company_name="Kunde AG",
        tax_id="DE444555666",
        vat_id="DE444555666",
        address_line1="Marktplatz 5",
        postal_code="80331",
        city="München",
        country=germany,
        email="rechnung@kunde.example",
    )


@pytest.fixture
def invoices_in_range(db, company, partner):
    inv1 = Invoice.objects.create(
        invoice_number="INV-2026-0001",
        invoice_type=Invoice.InvoiceType.INVOICE,
        company=company,
        business_partner=partner,
        issue_date=date(2026, 3, 10),
        due_date=date(2026, 4, 9),
        currency="EUR",
        subtotal=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        total_amount=Decimal("119.00"),
        status=Invoice.InvoiceStatus.DRAFT,
    )
    InvoiceLine.objects.create(
        invoice=inv1,
        description="Beratung",
        product_code="SVC-001",
        quantity=Decimal("2.000"),
        unit_price=Decimal("50.000000"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("19.00"),
        tax_category="S",
        line_subtotal=Decimal("100.00"),
        line_total=Decimal("119.00"),
        unit_of_measure=1,
    )
    inv2 = Invoice.objects.create(
        invoice_number="INV-2026-0002",
        invoice_type=Invoice.InvoiceType.INVOICE,
        company=company,
        business_partner=partner,
        issue_date=date(2026, 3, 25),
        due_date=date(2026, 4, 24),
        currency="EUR",
        subtotal=Decimal("200.00"),
        tax_amount=Decimal("38.00"),
        total_amount=Decimal("238.00"),
        status=Invoice.InvoiceStatus.SENT,
    )
    InvoiceLine.objects.create(
        invoice=inv2,
        description="Lizenz",
        product_code="LIC-100",
        quantity=Decimal("1.000"),
        unit_price=Decimal("200.000000"),
        tax_rate=Decimal("19.00"),
        tax_amount=Decimal("38.00"),
        tax_category="S",
        line_subtotal=Decimal("200.00"),
        line_total=Decimal("238.00"),
        unit_of_measure=1,
    )
    return [inv1, inv2]


@pytest.fixture
def invoice_outside_range(db, company, partner):
    return Invoice.objects.create(
        invoice_number="INV-2025-0099",
        invoice_type=Invoice.InvoiceType.INVOICE,
        company=company,
        business_partner=partner,
        issue_date=date(2025, 12, 30),
        due_date=date(2026, 1, 29),
        currency="EUR",
        subtotal=Decimal("10.00"),
        tax_amount=Decimal("1.90"),
        total_amount=Decimal("11.90"),
        status=Invoice.InvoiceStatus.DRAFT,
    )


@pytest.mark.django_db
class TestExportPeriodService:
    """Service-level tests for ``export_period``."""

    def test_zip_contains_all_required_files(self, invoices_in_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            names = set(zf.namelist())
        assert {"index.xml", "invoices.csv", "invoice_lines.csv", "business_partners.csv"} <= names

    def test_index_xml_references_dtd_and_tables(self, invoices_in_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            index_xml = zf.read("index.xml").decode("utf-8")
        assert 'SYSTEM "gdpdu-01-09-2004.dtd"' in index_xml
        assert "<URL>invoices.csv</URL>" in index_xml
        assert "<URL>invoice_lines.csv</URL>" in index_xml
        assert "<URL>business_partners.csv</URL>" in index_xml
        # CSV dialect declarations must match what _write_csv produced.
        assert "<ColumnDelimiter>;</ColumnDelimiter>" in index_xml
        assert "<DecimalSymbol>.</DecimalSymbol>" in index_xml

    def test_only_invoices_in_range_are_exported(self, invoices_in_range, invoice_outside_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            invoices_csv = zf.read("invoices.csv").decode("utf-8")
        assert "INV-2026-0001" in invoices_csv
        assert "INV-2026-0002" in invoices_csv
        assert "INV-2025-0099" not in invoices_csv

    def test_csv_decimal_format_matches_index(self, invoices_in_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            invoices_csv = zf.read("invoices.csv").decode("utf-8")
        # 119.00 (decimal point, two places) must appear in the CSV.
        assert "119.00" in invoices_csv
        # German "," decimal separator must NOT be used.
        assert "119,00" not in invoices_csv

    def test_invoice_lines_reference_invoice_number(self, invoices_in_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            lines_csv = zf.read("invoice_lines.csv").decode("utf-8")
        assert "INV-2026-0001" in lines_csv
        assert "Beratung" in lines_csv
        assert "Lizenz" in lines_csv

    def test_business_partners_contains_iso_country_code(self, invoices_in_range):
        archive = export_period(date(2026, 3, 1), date(2026, 3, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            partners_csv = zf.read("business_partners.csv").decode("utf-8")
        assert "Kunde AG" in partners_csv
        # ISO 3166-1 alpha-2 country code must be present (last column).
        assert ";DE\r\n" in partners_csv or ";DE" in partners_csv.rstrip("\r\n")

    def test_empty_period_produces_valid_archive(self, db, company, partner):
        archive = export_period(date(2030, 1, 1), date(2030, 1, 31))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            assert "index.xml" in zf.namelist()
            assert zf.read("invoices.csv") == b""

    def test_invalid_range_rejected(self, db):
        with pytest.raises(ValueError):
            export_period(date(2026, 3, 31), date(2026, 3, 1))


@pytest.mark.django_db
class TestGDPdUExportEndpoint:
    """API-level tests for ``GET /api/gdpdu/export/``."""

    def _admin_client(self):
        admin = User.objects.create_user(username="gdpdu-admin", password="x", is_staff=True, is_superuser=True)
        client = APIClient()
        client.force_authenticate(user=admin)
        return client, admin

    def _user_client(self):
        user = User.objects.create_user(username="gdpdu-user", password="x")
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_non_admin_forbidden(self, invoices_in_range):
        client = self._user_client()
        url = reverse("api-gdpdu-export")
        response = client.get(url, {"start": "2026-03-01", "end": "2026-03-31"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_forbidden(self, invoices_in_range):
        client = APIClient()
        url = reverse("api-gdpdu-export")
        response = client.get(url, {"start": "2026-03-01", "end": "2026-03-31"})
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_receives_zip(self, invoices_in_range):
        client, _ = self._admin_client()
        url = reverse("api-gdpdu-export")
        response = client.get(url, {"start": "2026-03-01", "end": "2026-03-31"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/zip"
        assert "attachment" in response["Content-Disposition"]
        assert "gdpdu-export_2026-03-01_2026-03-31.zip" in response["Content-Disposition"]
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            assert "index.xml" in zf.namelist()

    def test_missing_parameters_return_400(self, invoices_in_range):
        client, _ = self._admin_client()
        url = reverse("api-gdpdu-export")
        response = client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_date_format_returns_400(self, invoices_in_range):
        client, _ = self._admin_client()
        url = reverse("api-gdpdu-export")
        response = client.get(url, {"start": "01.03.2026", "end": "31.03.2026"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_inverted_range_returns_400(self, invoices_in_range):
        client, _ = self._admin_client()
        url = reverse("api-gdpdu-export")
        response = client.get(url, {"start": "2026-03-31", "end": "2026-03-01"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_export_creates_audit_log_entry(self, invoices_in_range):
        client, admin = self._admin_client()
        url = reverse("api-gdpdu-export")
        before = AuditLog.objects.filter(action=AuditLog.ActionType.EXPORT).count()
        response = client.get(url, {"start": "2026-03-01", "end": "2026-03-31"})
        assert response.status_code == status.HTTP_200_OK
        after = AuditLog.objects.filter(action=AuditLog.ActionType.EXPORT).count()
        assert after == before + 1
        entry = AuditLog.objects.filter(action=AuditLog.ActionType.EXPORT).order_by("-id").first()
        assert entry is not None
        assert entry.user_id == admin.id
        assert entry.details.get("start") == "2026-03-01"
        assert entry.details.get("end") == "2026-03-31"
