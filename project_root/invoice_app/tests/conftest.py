"""
Pytest fixtures for invoice_app tests.

Provides reusable, composable fixtures that replace duplicated setUp code.
All fixtures use factory_boy factories from invoice_app.tests.factories.

Usage in tests:
    def test_invoice_creation(db, company, business_partner):
        invoice = InvoiceFactory(company=company, business_partner=business_partner)
        assert invoice.invoice_number.startswith("INV-")

    def test_permissions(authenticated_admin_client):
        response = authenticated_admin_client.get("/api/invoices/")
        assert response.status_code == 200
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from invoice_app.tests.factories import (
    AccountantRoleFactory,
    AdminRoleFactory,
    AustriaCountryFactory,
    BusinessPartnerFactory,
    CompanyFactory,
    CountryFactory,
    EUPartnerFactory,
    FranceCountryFactory,
    IndividualPartnerFactory,
    InvoiceFactory,
    InvoiceLineFactory,
    ProductFactory,
    ReadOnlyRoleFactory,
    ReducedTaxLineFactory,
    ServiceProductFactory,
    SupplierFactory,
    SwitzerlandCountryFactory,
    ThirdCountryPartnerFactory,
    UserFactory,
    UserProfileFactory,
    UserRoleFactory,
    create_complete_invoice,
    create_eu_tax_scenario,
)


# ── Country fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def germany(db):
    """Germany (DE) — standard EU/Eurozone country."""
    return CountryFactory()


@pytest.fixture
def austria(db):
    """Austria (AT) — EU country with different VAT rates."""
    return AustriaCountryFactory()


@pytest.fixture
def france(db):
    """France (FR) — EU country for reverse charge tests."""
    return FranceCountryFactory()


@pytest.fixture
def switzerland(db):
    """Switzerland (CH) — non-EU country for export tests."""
    return SwitzerlandCountryFactory()


# ── Company fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def company(db):
    """Standard test company."""
    return CompanyFactory()


# ── BusinessPartner fixtures ────────────────────────────────────────────────


@pytest.fixture
def business_partner(germany):
    """Standard domestic business partner."""
    return BusinessPartnerFactory(country=germany)


@pytest.fixture
def individual_partner(germany):
    """Individual (non-business) partner."""
    return IndividualPartnerFactory(country=germany)


@pytest.fixture
def supplier(germany):
    """Supplier partner."""
    return SupplierFactory(country=germany)


@pytest.fixture
def eu_partner(france):
    """EU business partner (France) — for reverse charge tests."""
    return EUPartnerFactory(country=france)


@pytest.fixture
def export_partner(switzerland):
    """Non-EU partner (Switzerland) — for export/G-category tests."""
    return ThirdCountryPartnerFactory(country=switzerland)


# ── Product fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def product(db):
    """Standard physical product (19% VAT)."""
    return ProductFactory()


@pytest.fixture
def service_product(db):
    """Service product (hours-based, 19% VAT)."""
    return ServiceProductFactory()


# ── User & Auth fixtures ────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    """Basic test user (no profile or role)."""
    return UserFactory()


@pytest.fixture
def admin_role(db):
    """Admin role with all permissions."""
    return AdminRoleFactory()


@pytest.fixture
def clerk_role(db):
    """Clerk role with basic permissions."""
    return UserRoleFactory()


@pytest.fixture
def accountant_role(db):
    """Accountant role."""
    return AccountantRoleFactory()


@pytest.fixture
def readonly_role(db):
    """Read-only role with no write permissions."""
    return ReadOnlyRoleFactory()


@pytest.fixture
def admin_user(admin_role):
    """Admin user with profile and admin role."""
    user = UserFactory(is_staff=True, is_superuser=True)
    UserProfileFactory(user=user, role=admin_role)
    return user


@pytest.fixture
def clerk_user(clerk_role):
    """Clerk user with profile."""
    user = UserFactory()
    UserProfileFactory(user=user, role=clerk_role)
    return user


@pytest.fixture
def accountant_user(accountant_role):
    """Accountant user with profile."""
    user = UserFactory()
    UserProfileFactory(user=user, role=accountant_role)
    return user


@pytest.fixture
def readonly_user(readonly_role):
    """Read-only user with profile."""
    user = UserFactory()
    UserProfileFactory(user=user, role=readonly_role)
    return user


# ── API Client fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def authenticated_admin_client(admin_user):
    """APIClient authenticated as admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def authenticated_clerk_client(clerk_user):
    """APIClient authenticated as clerk."""
    client = APIClient()
    client.force_authenticate(user=clerk_user)
    return client


@pytest.fixture
def authenticated_readonly_client(readonly_user):
    """APIClient authenticated as read-only user."""
    client = APIClient()
    client.force_authenticate(user=readonly_user)
    return client


# ── Invoice fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def draft_invoice(company, business_partner):
    """DRAFT invoice with 2 lines."""
    return create_complete_invoice(
        num_lines=2,
        status="DRAFT",
        company=company,
        partner=business_partner,
    )


@pytest.fixture
def sent_invoice(company, business_partner):
    """SENT invoice (locked per GoBD)."""
    return create_complete_invoice(
        num_lines=2,
        status="SENT",
        company=company,
        partner=business_partner,
    )


@pytest.fixture
def paid_invoice(company, business_partner):
    """PAID invoice (locked per GoBD)."""
    return create_complete_invoice(
        num_lines=2,
        status="PAID",
        company=company,
        partner=business_partner,
    )


# ── Complex scenario fixtures ───────────────────────────────────────────────


@pytest.fixture
def eu_tax_scenario(db):
    """
    Complete EU tax scenario with:
    - Countries: Germany, France, Switzerland
    - Company in Germany
    - Partners: domestic, EU (France), export (Switzerland)
    """
    return create_eu_tax_scenario()


@pytest.fixture
def invoice_with_mixed_tax_lines(company, business_partner):
    """Invoice with lines at different tax rates (19%, 7%, 0%)."""
    invoice = InvoiceFactory(company=company, business_partner=business_partner)
    InvoiceLineFactory(
        invoice=invoice, description="Standard 19%", tax_rate=Decimal("19.00"), unit_price=Decimal("100.00")
    )
    ReducedTaxLineFactory(invoice=invoice, description="Reduced 7%")
    InvoiceLineFactory(
        invoice=invoice,
        description="Zero rate",
        tax_rate=Decimal("0.00"),
        tax_category="Z",
        unit_price=Decimal("50.00"),
    )
    invoice.refresh_from_db()
    return invoice
