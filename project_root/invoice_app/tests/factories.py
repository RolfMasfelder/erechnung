"""
Factory classes for test data generation using factory_boy.

Provides consistent, realistic test data for all invoice_app models.
Eliminates duplicated setUp code and ensures unique constraint compliance.

Usage:
    from invoice_app.tests.factories import InvoiceFactory, CompanyFactory

    # Simple creation
    invoice = InvoiceFactory()

    # With custom fields
    invoice = InvoiceFactory(status="PAID", currency="USD")

    # With related objects
    invoice = InvoiceFactory.create(
        lines=3,  # creates 3 InvoiceLines via post_generation
    )

    # Build without saving (no DB hit)
    invoice_data = InvoiceFactory.build()
"""

from decimal import Decimal

import factory
from django.contrib.auth.models import User
from django.utils import timezone

from invoice_app.models import (
    AuditLog,
    BusinessPartner,
    Company,
    Country,
    CountryTaxRate,
    Invoice,
    InvoiceAllowanceCharge,
    InvoiceAttachment,
    InvoiceLine,
    Product,
    SystemConfig,
    UserProfile,
    UserRole,
)


# ── Country & Tax Rates ────────────────────────────────────────────────────


class CountryFactory(factory.django.DjangoModelFactory):
    """Factory for Country model. Uses get_or_create to avoid duplicate PK errors."""

    class Meta:
        model = Country
        django_get_or_create = ("code",)

    code = "DE"
    code_alpha3 = "DEU"
    numeric_code = "276"
    name = "Germany"
    name_local = "Deutschland"
    currency_code = "EUR"
    currency_name = "Euro"
    currency_symbol = "€"
    default_language = "de"
    is_eu_member = True
    is_eurozone = True
    standard_vat_rate = Decimal("19.00")
    reduced_vat_rate = Decimal("7.00")
    super_reduced_vat_rate = None
    date_format = "DD.MM.YYYY"
    decimal_separator = ","
    thousands_separator = "."
    is_active = True


class AustriaCountryFactory(CountryFactory):
    code = "AT"
    code_alpha3 = "AUT"
    numeric_code = "040"
    name = "Austria"
    name_local = "Österreich"
    standard_vat_rate = Decimal("20.00")
    reduced_vat_rate = Decimal("10.00")
    super_reduced_vat_rate = Decimal("13.00")


class FranceCountryFactory(CountryFactory):
    code = "FR"
    code_alpha3 = "FRA"
    numeric_code = "250"
    name = "France"
    name_local = "France"
    default_language = "fr"
    standard_vat_rate = Decimal("20.00")
    reduced_vat_rate = Decimal("5.50")
    super_reduced_vat_rate = Decimal("2.10")


class SwitzerlandCountryFactory(CountryFactory):
    """Non-EU country for third-country export tests."""

    code = "CH"
    code_alpha3 = "CHE"
    numeric_code = "756"
    name = "Switzerland"
    name_local = "Schweiz"
    currency_code = "CHF"
    currency_name = "Swiss Franc"
    currency_symbol = "CHF"
    default_language = "de"
    is_eu_member = False
    is_eurozone = False
    standard_vat_rate = Decimal("8.10")
    reduced_vat_rate = Decimal("2.60")
    super_reduced_vat_rate = None


class USACountryFactory(CountryFactory):
    """Non-EU, non-Euro country for international tests."""

    code = "US"
    code_alpha3 = "USA"
    numeric_code = "840"
    name = "United States"
    name_local = "United States"
    currency_code = "USD"
    currency_name = "US Dollar"
    currency_symbol = "$"
    default_language = "en"
    is_eu_member = False
    is_eurozone = False
    standard_vat_rate = Decimal("0.00")
    reduced_vat_rate = None
    super_reduced_vat_rate = None


class CountryTaxRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CountryTaxRate

    country = factory.SubFactory(CountryFactory)
    rate_type = CountryTaxRate.RateType.STANDARD
    rate = Decimal("19.00")
    valid_from = factory.LazyFunction(lambda: timezone.now().date().replace(month=1, day=1))
    is_active = True


# ── Company ─────────────────────────────────────────────────────────────────


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Test GmbH {n}")
    legal_name = factory.LazyAttribute(lambda o: f"{o.name} - Gesellschaft mit beschränkter Haftung")
    tax_id = factory.Sequence(lambda n: f"DE{100000000 + n}")
    vat_id = factory.Sequence(lambda n: f"DE{200000000 + n}")
    commercial_register = factory.Sequence(lambda n: f"HRB {10000 + n}")
    address_line1 = factory.Faker("street_address", locale="de_DE")
    postal_code = factory.Faker("postcode", locale="de_DE")
    city = factory.Faker("city", locale="de_DE")
    country = "Germany"
    phone = factory.Faker("phone_number", locale="de_DE")
    email = factory.Sequence(lambda n: f"company{n}@example.com")
    iban = factory.Sequence(lambda n: f"DE89370400440532013{n:03d}")
    bic = "COBADEFFXXX"
    bank_name = "Commerzbank"
    default_currency = "EUR"
    default_payment_terms = 30
    is_active = True


# ── BusinessPartner ─────────────────────────────────────────────────────────


class BusinessPartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BusinessPartner

    partner_type = BusinessPartner.PartnerType.BUSINESS
    partner_number = factory.Sequence(lambda n: f"BP-{n:05d}")
    company_name = factory.Sequence(lambda n: f"Kunde AG {n}")
    legal_name = factory.LazyAttribute(lambda o: f"{o.company_name} - Aktiengesellschaft")
    tax_id = factory.Sequence(lambda n: f"DE{300000000 + n}")
    vat_id = factory.Sequence(lambda n: f"DE{400000000 + n}")
    address_line1 = factory.Faker("street_address", locale="de_DE")
    postal_code = factory.Faker("postcode", locale="de_DE")
    city = factory.Faker("city", locale="de_DE")
    country = factory.SubFactory(CountryFactory)
    email = factory.Sequence(lambda n: f"partner{n}@example.com")
    payment_terms = 30
    preferred_currency = "EUR"
    is_customer = True
    is_supplier = False
    is_active = True


class IndividualPartnerFactory(BusinessPartnerFactory):
    """Individual (non-business) partner."""

    partner_type = BusinessPartner.PartnerType.INDIVIDUAL
    company_name = ""
    legal_name = ""
    first_name = factory.Faker("first_name", locale="de_DE")
    last_name = factory.Faker("last_name", locale="de_DE")
    tax_id = ""
    vat_id = ""


class SupplierFactory(BusinessPartnerFactory):
    """Supplier who sends invoices to us."""

    partner_number = factory.Sequence(lambda n: f"SUP-{n:05d}")
    company_name = factory.Sequence(lambda n: f"Lieferant GmbH {n}")
    is_customer = False
    is_supplier = True


class EUPartnerFactory(BusinessPartnerFactory):
    """EU business partner for reverse charge tests."""

    partner_number = factory.Sequence(lambda n: f"EU-{n:05d}")
    company_name = factory.Sequence(lambda n: f"EU Partner S.A. {n}")
    country = factory.SubFactory(FranceCountryFactory)
    vat_id = factory.Sequence(lambda n: f"FR{50000000000 + n}")
    tax_id = factory.Sequence(lambda n: f"FR{60000000000 + n}")
    preferred_currency = "EUR"


class GovernmentPartnerFactory(BusinessPartnerFactory):
    """Government (B2G) partner for XRechnung tests."""

    partner_type = BusinessPartner.PartnerType.GOVERNMENT
    partner_number = factory.Sequence(lambda n: f"GOV-{n:05d}")
    company_name = factory.Sequence(lambda n: f"Bundesamt {n}")
    leitweg_id = "04011000-12345-34"  # Valid check digit: 98 - (401100012345 % 97) = 34


class ThirdCountryPartnerFactory(BusinessPartnerFactory):
    """Non-EU partner for export/G-category tests."""

    partner_number = factory.Sequence(lambda n: f"EX-{n:05d}")
    company_name = factory.Sequence(lambda n: f"Export Corp {n}")
    country = factory.SubFactory(SwitzerlandCountryFactory)
    vat_id = ""
    tax_id = factory.Sequence(lambda n: f"CHE{100000000 + n}")
    preferred_currency = "CHF"


# ── Product ─────────────────────────────────────────────────────────────────


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    product_code = factory.Sequence(lambda n: f"PROD-{n:04d}")
    name = factory.Sequence(lambda n: f"Test Product {n}")
    description = factory.LazyAttribute(lambda o: f"Description for {o.name}")
    product_type = Product.ProductType.PHYSICAL
    category = "General"
    base_price = Decimal("100.00")
    currency = "EUR"
    unit_of_measure = Product.UnitOfMeasure.PCE
    tax_category = Product.TaxCategory.STANDARD
    default_tax_rate = Decimal("19.00")
    is_active = True


class ServiceProductFactory(ProductFactory):
    """Service product (hours-based)."""

    product_code = factory.Sequence(lambda n: f"SVC-{n:04d}")
    name = factory.Sequence(lambda n: f"Consulting Service {n}")
    product_type = Product.ProductType.SERVICE
    category = "Services"
    base_price = Decimal("150.00")
    unit_of_measure = Product.UnitOfMeasure.HUR


class DigitalProductFactory(ProductFactory):
    """Digital product."""

    product_code = factory.Sequence(lambda n: f"DIG-{n:04d}")
    name = factory.Sequence(lambda n: f"Software License {n}")
    product_type = Product.ProductType.DIGITAL
    category = "Software"
    base_price = Decimal("49.99")


class ReducedTaxProductFactory(ProductFactory):
    """Product with reduced VAT rate (e.g., books, food)."""

    product_code = factory.Sequence(lambda n: f"RED-{n:04d}")
    name = factory.Sequence(lambda n: f"Book {n}")
    category = "Books"
    tax_category = Product.TaxCategory.REDUCED
    default_tax_rate = Decimal("7.00")
    base_price = Decimal("29.99")


class ZeroTaxProductFactory(ProductFactory):
    """Product with zero VAT rate."""

    product_code = factory.Sequence(lambda n: f"ZERO-{n:04d}")
    name = factory.Sequence(lambda n: f"Export Product {n}")
    tax_category = Product.TaxCategory.ZERO
    default_tax_rate = Decimal("0.00")


# ── User & RBAC ─────────────────────────────────────────────────────────────


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name", locale="de_DE")
    last_name = factory.Faker("last_name", locale="de_DE")
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "testpass123!")


class AdminUserFactory(UserFactory):
    """Django superuser."""

    username = factory.Sequence(lambda n: f"admin{n}")
    is_staff = True
    is_superuser = True


class UserRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRole
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Test Role {n}")
    role_type = UserRole.RoleType.CLERK
    description = factory.LazyAttribute(lambda o: f"Role: {o.name}")
    is_active = True

    # Default: basic permissions
    can_create_invoice = True
    can_edit_invoice = True
    can_generate_pdf = True
    can_create_customer = True
    can_edit_customer = True


class AdminRoleFactory(UserRoleFactory):
    """Admin role with all permissions."""

    name = factory.Sequence(lambda n: f"Admin Role {n}")
    role_type = UserRole.RoleType.ADMIN
    can_delete_invoice = True
    can_send_invoice = True
    can_mark_paid = True
    can_delete_customer = True
    can_create_product = True
    can_edit_product = True
    can_delete_product = True
    can_manage_inventory = True
    can_edit_company = True
    can_view_reports = True
    can_export_data = True
    can_view_audit_logs = True
    can_backup_data = True
    can_manage_users = True
    can_manage_roles = True
    can_change_settings = True


class AccountantRoleFactory(UserRoleFactory):
    """Accountant role."""

    name = factory.Sequence(lambda n: f"Accountant Role {n}")
    role_type = UserRole.RoleType.ACCOUNTANT
    can_send_invoice = True
    can_mark_paid = True
    can_view_reports = True
    can_export_data = True


class ReadOnlyRoleFactory(UserRoleFactory):
    """Read-only role with no write permissions."""

    name = factory.Sequence(lambda n: f"ReadOnly Role {n}")
    role_type = UserRole.RoleType.READ_ONLY
    can_create_invoice = False
    can_edit_invoice = False
    can_generate_pdf = False
    can_create_customer = False
    can_edit_customer = False


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(UserRoleFactory)
    employee_id = factory.Sequence(lambda n: f"EMP-{n:04d}")
    department = "Buchhaltung"
    language = "de"
    timezone = "Europe/Berlin"


class AdminProfileFactory(UserProfileFactory):
    """Admin user with admin role."""

    user = factory.SubFactory(AdminUserFactory)
    role = factory.SubFactory(AdminRoleFactory)


# ── Invoice ─────────────────────────────────────────────────────────────────


class InvoiceFactory(factory.django.DjangoModelFactory):
    """
    Factory for Invoice model.

    By default creates a DRAFT invoice with company and business partner.
    Use the `lines` parameter to auto-create InvoiceLines:

        invoice = InvoiceFactory(lines=3)  # creates 3 lines
    """

    class Meta:
        model = Invoice
        skip_postgeneration_save = True

    invoice_type = Invoice.InvoiceType.INVOICE
    company = factory.SubFactory(CompanyFactory)
    business_partner = factory.SubFactory(BusinessPartnerFactory)
    issue_date = factory.LazyFunction(timezone.now)
    due_date = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=30))
    currency = "EUR"
    status = Invoice.InvoiceStatus.DRAFT
    payment_terms = 30

    # Totals start at 0 — will be recalculated when lines are added
    subtotal = Decimal("0")
    tax_amount = Decimal("0")
    total_amount = Decimal("0")

    @factory.post_generation
    def lines(self, create, count, **kwargs):
        """Create N invoice lines if count is provided."""
        if not create or not count:
            return
        for _ in range(count):
            InvoiceLineFactory(invoice=self, **kwargs)


class PaidInvoiceFactory(InvoiceFactory):
    """Invoice that is already paid and locked (GoBD)."""

    status = Invoice.InvoiceStatus.PAID
    is_locked = True
    locked_at = factory.LazyFunction(timezone.now)
    lock_reason = "PAID"


class SentInvoiceFactory(InvoiceFactory):
    """Invoice that has been sent and locked."""

    status = Invoice.InvoiceStatus.SENT
    is_locked = True
    locked_at = factory.LazyFunction(timezone.now)
    lock_reason = "SENT"


class CreditNoteFactory(InvoiceFactory):
    """Credit note invoice."""

    invoice_type = Invoice.InvoiceType.CREDIT_NOTE


# ── InvoiceLine ─────────────────────────────────────────────────────────────


class InvoiceLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceLine

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Sequence(lambda n: f"Line Item {n}")
    quantity = Decimal("1.000")
    unit_price = Decimal("100.00")
    tax_rate = Decimal("19.00")
    tax_category = "S"
    unit_of_measure = Product.UnitOfMeasure.PCE


class ReducedTaxLineFactory(InvoiceLineFactory):
    """Invoice line with reduced VAT (7%)."""

    description = factory.Sequence(lambda n: f"Reduced Tax Item {n}")
    tax_rate = Decimal("7.00")
    unit_price = Decimal("29.99")


class ZeroTaxLineFactory(InvoiceLineFactory):
    """Invoice line with zero VAT (export / reverse charge)."""

    description = factory.Sequence(lambda n: f"Export Item {n}")
    tax_rate = Decimal("0.00")
    tax_category = "Z"


class HighValueLineFactory(InvoiceLineFactory):
    """High-value line for financial limit tests."""

    description = factory.Sequence(lambda n: f"Premium Item {n}")
    quantity = Decimal("10.000")
    unit_price = Decimal("1000.00")


class ProductLineFactory(InvoiceLineFactory):
    """Invoice line linked to a Product."""

    product = factory.SubFactory(ProductFactory)
    description = factory.LazyAttribute(lambda o: o.product.name)
    product_code = factory.LazyAttribute(lambda o: o.product.product_code)
    unit_price = factory.LazyAttribute(lambda o: o.product.base_price)
    tax_rate = factory.LazyAttribute(lambda o: o.product.default_tax_rate)


# ── InvoiceAttachment ───────────────────────────────────────────────────────


class InvoiceAttachmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceAttachment

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Sequence(lambda n: f"Attachment {n}")
    file = factory.django.FileField(filename="test_attachment.pdf", data=b"%PDF-1.4 test")
    attachment_type = "supporting_document"


# ── InvoiceAllowanceCharge ──────────────────────────────────────────────────


class InvoiceAllowanceFactory(factory.django.DjangoModelFactory):
    """Header-level allowance (discount)."""

    class Meta:
        model = InvoiceAllowanceCharge

    invoice = factory.SubFactory(InvoiceFactory)
    invoice_line = None  # header-level
    is_charge = False
    actual_amount = Decimal("10.00")
    reason = "Treuerabatt"
    reason_code = "95"


class InvoiceChargeFactory(InvoiceAllowanceFactory):
    """Header-level charge (surcharge)."""

    is_charge = True
    actual_amount = Decimal("5.00")
    reason = "Expressversand"
    reason_code = "FC"


# ── AuditLog ────────────────────────────────────────────────────────────────


class AuditLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditLog

    user = factory.SubFactory(UserFactory)
    username = factory.LazyAttribute(lambda o: o.user.username)
    action = AuditLog.ActionType.CREATE
    severity = AuditLog.Severity.LOW
    object_type = "Invoice"
    object_id = factory.Sequence(str)
    description = factory.Sequence(lambda n: f"Test audit event {n}")


# ── SystemConfig ────────────────────────────────────────────────────────────


class SystemConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SystemConfig
        django_get_or_create = ("key",)

    key = factory.Sequence(lambda n: f"test.config.{n}")
    category = SystemConfig.ConfigCategory.GENERAL
    value = "test_value"
    value_type = SystemConfig.ConfigType.STRING
    name = factory.LazyAttribute(lambda o: f"Test Config {o.key}")
    is_required = False
    is_sensitive = False
    is_system = False


# ── Convenience helpers ─────────────────────────────────────────────────────


def create_complete_invoice(
    num_lines=2,
    status="DRAFT",
    company=None,
    partner=None,
    line_kwargs=None,
):
    """
    Create a complete invoice with company, partner, and lines.

    Args:
        num_lines: Number of invoice lines to create.
        status: Invoice status (DRAFT, SENT, PAID, CANCELLED).
        company: Existing Company or None to create one.
        partner: Existing BusinessPartner or None to create one.
        line_kwargs: Dict of extra kwargs for each InvoiceLine.

    Returns:
        Invoice instance with all related objects.
    """
    if company is None:
        company = CompanyFactory()
    if partner is None:
        partner = BusinessPartnerFactory()

    invoice = InvoiceFactory(
        company=company,
        business_partner=partner,
        status=status,
    )

    line_defaults = line_kwargs or {}
    for i in range(num_lines):
        InvoiceLineFactory(
            invoice=invoice,
            description=f"Position {i + 1}",
            quantity=Decimal(str(i + 1)),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("19.00"),
            **line_defaults,
        )

    invoice.refresh_from_db()
    return invoice


def create_user_with_profile(role_type="CLERK", **user_kwargs):
    """
    Create a User + UserProfile + UserRole in one call.

    Args:
        role_type: One of ADMIN, MANAGER, ACCOUNTANT, CLERK, AUDITOR, READ_ONLY
        **user_kwargs: Extra kwargs for UserFactory (e.g. username, password)

    Returns:
        tuple: (user, profile)
    """
    role_factory_map = {
        "ADMIN": AdminRoleFactory,
        "CLERK": UserRoleFactory,
        "ACCOUNTANT": AccountantRoleFactory,
        "READ_ONLY": ReadOnlyRoleFactory,
    }
    role_factory = role_factory_map.get(role_type, UserRoleFactory)
    role = role_factory()

    user = UserFactory(**user_kwargs)
    profile = UserProfileFactory(user=user, role=role)
    return user, profile


def create_authenticated_client(api_client, role_type="ADMIN"):
    """
    Create a user with profile and authenticate the DRF APIClient.

    Args:
        api_client: DRF APIClient instance
        role_type: Role type string

    Returns:
        tuple: (user, profile)
    """
    user, profile = create_user_with_profile(role_type=role_type)
    api_client.force_authenticate(user=user)
    return user, profile


def create_eu_tax_scenario():
    """
    Set up a complete EU tax scenario with Germany, France, and Switzerland.

    Returns:
        dict with keys: germany, france, switzerland, company,
                       domestic_partner, eu_partner, export_partner
    """
    germany = CountryFactory()
    france = FranceCountryFactory()
    switzerland = SwitzerlandCountryFactory()

    company = CompanyFactory()

    domestic_partner = BusinessPartnerFactory(country=germany)
    eu_partner = EUPartnerFactory(country=france)
    export_partner = ThirdCountryPartnerFactory(country=switzerland)

    return {
        "germany": germany,
        "france": france,
        "switzerland": switzerland,
        "company": company,
        "domestic_partner": domestic_partner,
        "eu_partner": eu_partner,
        "export_partner": export_partner,
    }
