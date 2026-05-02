"""
Management command: generate_test_data

Uses factory_boy factories to create realistic, consistent test datasets.
Replaces ad-hoc test data creation with deterministic, repeatable generation.

Usage:
    # Minimal dataset (quick smoke tests)
    docker compose exec web python project_root/manage.py generate_test_data --preset minimal

    # Standard dataset (development / manual testing)
    docker compose exec web python project_root/manage.py generate_test_data --preset standard

    # Large dataset (load / performance testing)
    docker compose exec web python project_root/manage.py generate_test_data --preset large

    # Clear and regenerate
    docker compose exec web python project_root/manage.py generate_test_data --clear --preset standard
"""

from argparse import ArgumentParser
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from invoice_app.models import BusinessPartner, Company, Invoice, InvoiceLine, Product
from invoice_app.models.audit import AuditLog
from invoice_app.models.user import UserProfile, UserRole
from invoice_app.tests.factories import (
    AccountantRoleFactory,
    AdminRoleFactory,
    BusinessPartnerFactory,
    CompanyFactory,
    CountryFactory,
    EUPartnerFactory,
    FranceCountryFactory,
    GovernmentPartnerFactory,
    IndividualPartnerFactory,
    InvoiceFactory,
    InvoiceLineFactory,
    ProductFactory,
    ReadOnlyRoleFactory,
    ReducedTaxProductFactory,
    ServiceProductFactory,
    SupplierFactory,
    SwitzerlandCountryFactory,
    ThirdCountryPartnerFactory,
    UserProfileFactory,
    UserRoleFactory,
)


PRESETS: dict[str, dict[str, Any]] = {
    "minimal": {
        "partners": 3,
        "products": 5,
        "invoices": 5,
        "lines_per_invoice": 2,
    },
    "standard": {
        "partners": 15,
        "products": 20,
        "invoices": 30,
        "lines_per_invoice": 3,
    },
    "stress": {
        "partners": 500,
        "products": 100,
        "invoices": 10000,
        "lines_per_invoice": 3,
    },
    "edge": {
        "partners": 20,
        "products": 15,
        "invoices": 30,
        "lines_per_invoice": 5,
        "special_characters": True,
        "max_field_lengths": True,
        "all_tax_categories": True,
        "gobd_locks": True,
    },
    "large": {
        "partners": 50,
        "products": 50,
        "invoices": 200,
        "lines_per_invoice": 5,
    },
}


class Command(BaseCommand):
    help = "Generate realistic test data using factory_boy factories"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--preset",
            choices=PRESETS.keys(),
            default="standard",
            help="Data volume preset (default: standard)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing test data before generating",
        )

    def _log(self, msg: str) -> None:
        if self.verbosity >= 1:
            self.stdout.write(msg)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        self.verbosity = options.get("verbosity", 1)
        preset = PRESETS[options["preset"]]

        if options["clear"]:
            self._clear_data()

        self._log(f"Generating test data (preset: {options['preset']})...")

        # 1. Countries (idempotent via get_or_create)
        germany = CountryFactory()
        france = FranceCountryFactory()
        switzerland = SwitzerlandCountryFactory()
        self._log(self.style.SUCCESS("  Countries: DE, FR, CH"))

        # 2. Company
        company = CompanyFactory(
            name="Musterfirma GmbH",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Musterstraße 123",
            postal_code="12345",
            city="Musterstadt",
            country="Germany",
        )
        self._log(self.style.SUCCESS(f"  Company: {company.name}"))

        # 3. Users with roles
        testuser, created = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@example.com", "first_name": "Test", "last_name": "User"},
        )
        if created:
            testuser.set_password("testpass123")
            testuser.save()

        admin_role = AdminRoleFactory()
        AccountantRoleFactory()
        UserRoleFactory()
        ReadOnlyRoleFactory()
        UserProfileFactory(user=testuser, role=admin_role)
        self._log(self.style.SUCCESS("  Users & roles created"))

        # 4. Business Partners (mix of types)
        partners: list[BusinessPartner] = []
        n = preset["partners"]
        # 60% domestic business, 15% individual, 15% EU, 10% third-country
        for _ in range(max(1, int(n * 0.6))):
            partners.append(BusinessPartnerFactory(country=germany))
        for _ in range(max(1, int(n * 0.15))):
            partners.append(IndividualPartnerFactory(country=germany))
        for _ in range(max(1, int(n * 0.15))):
            partners.append(EUPartnerFactory(country=france))
        for _ in range(max(1, int(n * 0.10))):
            partners.append(ThirdCountryPartnerFactory(country=switzerland))
        # Add one supplier
        partners.append(SupplierFactory(country=germany))
        # Add GOVERNMENT partner for B2G / XRechnung tests
        gov_partner = GovernmentPartnerFactory(country=germany)
        partners.append(gov_partner)
        self._log(self.style.SUCCESS(f"  Partners: {len(partners)}"))

        # 5. Products (mix of types)
        products: list[Product] = []
        m = preset["products"]
        for _ in range(max(1, int(m * 0.5))):
            products.append(ProductFactory())
        for _ in range(max(1, int(m * 0.25))):
            products.append(ServiceProductFactory())
        for _ in range(max(1, int(m * 0.25))):
            products.append(ReducedTaxProductFactory())
        self._log(self.style.SUCCESS(f"  Products: {len(products)}"))

        # 6. Invoices with lines
        import random

        random.seed(42)  # Deterministic for reproducibility

        statuses = ["DRAFT"] * 4 + ["SENT"] * 3 + ["PAID"] * 2 + ["CANCELLED"]
        invoices_created = 0

        for _ in range(preset["invoices"]):
            partner = random.choice([p for p in partners if p.is_customer])
            status = random.choice(statuses)

            invoice = InvoiceFactory(
                company=company,
                business_partner=partner,
                status=status,
                created_by=testuser,
            )

            # Create lines
            for _ in range(preset["lines_per_invoice"]):
                product = random.choice(products)
                qty = Decimal(str(random.randint(1, 10)))
                InvoiceLineFactory(
                    invoice=invoice,
                    description=product.name,
                    product_code=product.product_code,
                    quantity=qty,
                    unit_price=product.base_price,
                    tax_rate=product.default_tax_rate,
                )

            invoices_created += 1

        self._log(self.style.SUCCESS(f"  Invoices: {invoices_created}"))

        # 6b. B2G / XRechnung invoice (SENT so it appears in list with XR badge)
        xr_invoice = InvoiceFactory(
            company=company,
            business_partner=gov_partner,
            status="SENT",
            created_by=testuser,
        )
        for _ in range(preset["lines_per_invoice"]):
            product = random.choice(products)
            InvoiceLineFactory(
                invoice=xr_invoice,
                description=product.name,
                product_code=product.product_code,
                quantity=Decimal("1"),
                unit_price=product.base_price,
                tax_rate=product.default_tax_rate,
            )
        invoices_created += 1
        self._log(self.style.SUCCESS("  B2G (XRechnung) invoice: 1"))

        # 7. Edge-case specific data
        if preset.get("special_characters"):
            self._create_edge_data(company, testuser, partners)

        # 8. GoBD locks (for edge preset)
        if preset.get("gobd_locks"):
            locked = Invoice.objects.filter(status="SENT")[:5]
            for inv in locked:
                inv.is_locked = True
                inv.locked_at = timezone.now()
                inv.save(update_fields=["is_locked", "locked_at"])
            self._log(self.style.SUCCESS(f"  GoBD-locked invoices: {locked.count()}"))

        # 9. Audit entries (for stress preset)
        if preset.get("partners", 0) >= 500:
            self._create_audit_entries(testuser, invoices_created)

        self._log(
            self.style.SUCCESS(
                f"\nTest data generated successfully!\n"
                f"  Company: {company.name}\n"
                f"  Partners: {len(partners)}\n"
                f"  Products: {len(products)}\n"
                f"  Invoices: {invoices_created}\n"
                f"  User: testuser / testpass123"
            )
        )

    def _create_edge_data(self, company: Company, user: User, partners: list[BusinessPartner]) -> None:
        """Create data with special characters, max field lengths, etc."""
        edge_partners = [
            {
                "partner_number": "BP-EDGE-01",
                "company_name": "Müller & Söhne GmbH — Ärzte für Überweisungen",
                "address_line1": "Straße der Einheit 123/a–b",
                "city": "München",
                "country": "Germany",
            },
            {
                "partner_number": "BP-EDGE-02",
                "company_name": "A" * 200,  # Max field length
                "address_line1": "B" * 200,
                "city": "C" * 100,
                "country": "Germany",
            },
            {
                "partner_number": "BP-EDGE-03",
                "company_name": '企業名 "テスト" & <特殊>',
                "address_line1": "住所 1-2-3",
                "city": "東京",
                "country": "Japan",
            },
        ]
        for ep in edge_partners:
            BusinessPartner.objects.create(
                partner_number=ep["partner_number"],
                company_name=ep["company_name"],
                address_line1=ep["address_line1"],
                city=ep["city"],
                country=ep["country"],
                is_customer=True,
                is_supplier=False,
                partner_type="BUSINESS",
                is_active=True,
                payment_terms=30,
                preferred_currency="EUR",
            )
        self._log(self.style.SUCCESS(f"  Edge-case partners: {len(edge_partners)}"))

    def _create_audit_entries(self, user: User, invoice_count: int) -> None:
        """Create 2,000 audit log entries for stress testing."""
        import random

        random.seed(42)
        actions = list(AuditLog.ActionType.values)
        batch: list[AuditLog] = []
        for i in range(2000):
            batch.append(
                AuditLog(
                    user=user,
                    username=user.username,
                    action=random.choice(actions),
                    object_type="Invoice" if i % 2 == 0 else "BusinessPartner",
                    object_id=str(random.randint(1, max(1, invoice_count))),
                    description=f"Stress test audit entry {i}",
                    ip_address="127.0.0.1",
                    details={"stress_test": True, "entry_index": i},
                )
            )
        AuditLog.objects.bulk_create(batch, batch_size=500)
        self._log(self.style.SUCCESS("  Audit entries: 2,000"))

    def _clear_data(self):
        self._log("Clearing existing data...")
        InvoiceLine.objects.all().delete()
        Invoice.objects.all().delete()
        Product.objects.all().delete()
        BusinessPartner.objects.all().delete()
        Company.objects.all().delete()
        UserProfile.objects.all().delete()
        UserRole.objects.all().delete()
        self._log(self.style.SUCCESS("  Data cleared"))
