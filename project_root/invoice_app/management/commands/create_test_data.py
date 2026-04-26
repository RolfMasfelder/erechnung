"""
Django management command to create comprehensive test data.
Creates: Company, Customers, Products, Invoices with lines
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from invoice_app.models import BusinessPartner, Company, Country, Invoice, InvoiceLine, Product


class Command(BaseCommand):
    help = "Create comprehensive test data for frontend testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before creating new test data",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=25,
            help="Number of entities to create (default: 25)",
        )

    def _log(self, msg):
        """Write to stdout only when verbosity >= 1."""
        if self.verbosity >= 1:
            self.stdout.write(msg)

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        count = options.get("count", 25)

        if options["clear"]:
            self._log("🗑️  Clearing existing data...")
            InvoiceLine.objects.all().delete()
            Invoice.objects.all().delete()
            Product.objects.all().delete()
            BusinessPartner.objects.all().delete()
            Company.objects.all().delete()
            # Don't delete users - they're not test data
            self._log(self.style.SUCCESS("✅ Data cleared"))

        # Create test user for E2E tests if not exists
        self._log("👤 Creating test user...")
        testuser, created = User.objects.get_or_create(
            username="testuser",
            defaults={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
            },
        )
        if created:
            testuser.set_password("testpass123")
            testuser.save()
            self._log(self.style.SUCCESS("✅ Test user created: testuser / testpass123"))
        else:
            self._log(self.style.WARNING("ℹ️  Test user already exists"))

        self._log("🏢 Creating company...")
        company = self.create_company()

        self._log(f"👥 Creating {count} business partners...")
        partners = self.create_business_partners(count)

        self._log(f"📦 Creating {count} products...")
        products = self.create_products(count)

        self._log(f"🧾 Creating {count * 2} invoices...")
        invoices = self.create_invoices(company, partners, products, count * 2)

        self._log(
            self.style.SUCCESS(
                f"\n✅ Test data created successfully!\n"
                f"   - Company: {company.name}\n"
                f"   - Business Partners: {len(partners)}\n"
                f"   - Products: {len(products)}\n"
                f"   - Invoices: {len(invoices)}\n"
            )
        )

    def create_company(self):
        """Create or get company data"""
        company, created = Company.objects.get_or_create(
            name="Musterfirma GmbH",
            defaults={
                "legal_name": "Musterfirma Gesellschaft mit beschränkter Haftung",
                "address_line1": "Musterstraße 123",
                "address_line2": "",
                "postal_code": "12345",
                "city": "Musterstadt",
                "country": "Deutschland",
                "tax_id": "DE123456789",
                "vat_id": "DE123456789",
                "commercial_register": "HRB 12345",
                "email": "info@musterfirma.de",
                "phone": "+49 123 456789",
                "fax": "+49 123 456790",
                "website": "https://www.musterfirma.de",
                "bank_name": "Musterbank",
                "bank_account": "1234567890",
                "iban": "DE89370400440532013000",
                "bic": "COBADEFFXXX",
                "default_currency": "EUR",
                "default_payment_terms": 30,
                "is_active": True,
            },
        )
        if created:
            self._log(self.style.SUCCESS(f"   ✓ Created: {company.name}"))
        else:
            self._log(self.style.WARNING(f"   ⚠ Already exists: {company.name}"))
        return company

    def create_business_partners(self, count=25):
        """Create sample business partners"""
        # Get Germany country object
        try:
            germany = Country.objects.get(code="DE")
        except Country.DoesNotExist:
            self._log(self.style.ERROR("   ❌ Country 'DE' not found. Run migrations first!"))
            return []

        # Base data for first 5 partners
        base_partners = [
            {
                "partner_number": "K-001",
                "partner_type": "BUSINESS",
                "company_name": "Acme Corporation",
                "legal_name": "Acme Corporation GmbH",
                "address_line1": "Hauptstraße 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country": germany,
                "email": "contact@acme.de",
                "phone": "+49 30 123456",
                "vat_id": "DE987654321",
                "is_active": True,
            },
            {
                "partner_number": "K-002",
                "partner_type": "BUSINESS",
                "company_name": "TechStart GmbH",
                "address_line1": "Innovationsweg 42",
                "postal_code": "80331",
                "city": "München",
                "country": germany,
                "email": "info@techstart.de",
                "phone": "+49 89 987654",
                "vat_id": "DE111222333",
                "is_active": True,
            },
            {
                "partner_number": "K-003",
                "partner_type": "INDIVIDUAL",
                "first_name": "Max",
                "last_name": "Mustermann",
                "address_line1": "Gartenstraße 7",
                "postal_code": "20095",
                "city": "Hamburg",
                "country": germany,
                "email": "max@mustermann.de",
                "phone": "+49 40 555666",
                "is_active": True,
            },
            {
                "partner_number": "K-004",
                "partner_type": "BUSINESS",
                "company_name": "Global Solutions AG",
                "address_line1": "Europaplatz 3",
                "postal_code": "60311",
                "city": "Frankfurt",
                "country": germany,
                "email": "contact@globalsolutions.de",
                "phone": "+49 69 123789",
                "vat_id": "DE444555666",
                "is_active": True,
            },
            {
                "partner_number": "K-005",
                "partner_type": "INDIVIDUAL",
                "first_name": "Erika",
                "last_name": "Musterfrau",
                "address_line1": "Blumenweg 15",
                "postal_code": "50667",
                "city": "Köln",
                "country": germany,
                "email": "erika@musterfrau.de",
                "phone": "+49 221 999888",
                "is_active": True,
            },
        ]

        cities = [
            "Berlin",
            "München",
            "Hamburg",
            "Frankfurt",
            "Köln",
            "Stuttgart",
            "Düsseldorf",
            "Dortmund",
            "Leipzig",
            "Dresden",
        ]
        company_types = ["GmbH", "AG", "UG", "KG", "OHG"]
        business_names = [
            "Tech",
            "Digital",
            "Global",
            "Smart",
            "Innovate",
            "Future",
            "Cloud",
            "Cyber",
            "Data",
            "Analytics",
        ]

        partners = []

        # Create base partners first
        for data in base_partners[: min(len(base_partners), count)]:
            partner, created = BusinessPartner.objects.get_or_create(
                partner_number=data["partner_number"], defaults=data
            )
            partners.append(partner)
            status = "✓ Created" if created else "⚠ Already exists"
            self._log(f"   {status}: {partner.display_name}")

        # Generate additional partners if count > 5
        for i in range(len(base_partners), count):
            partner_num = f"K-{i + 1:03d}"
            is_business = i % 3 != 0  # 2/3 business, 1/3 individual

            if is_business:
                data = {
                    "partner_number": partner_num,
                    "partner_type": "BUSINESS",
                    "company_name": f"{business_names[i % len(business_names)]} {company_types[i % len(company_types)]}",
                    "address_line1": f"Teststraße {i}",
                    "postal_code": f"{10000 + i * 100}",
                    "city": cities[i % len(cities)],
                    "country": germany,
                    "email": f"info-{i}@test.de",
                    "phone": f"+49 {i:03d} {i:06d}",
                    "vat_id": f"DE{i:09d}",
                    "is_active": True,
                }
            else:
                first_names = ["Anna", "Ben", "Clara", "David", "Emma", "Felix", "Greta", "Hans", "Ida", "Jonas"]
                last_names = [
                    "Schmidt",
                    "Müller",
                    "Schneider",
                    "Fischer",
                    "Weber",
                    "Meyer",
                    "Wagner",
                    "Becker",
                    "Schulz",
                    "Hoffmann",
                ]
                data = {
                    "partner_number": partner_num,
                    "partner_type": "INDIVIDUAL",
                    "first_name": first_names[i % len(first_names)],
                    "last_name": last_names[i % len(last_names)],
                    "address_line1": f"Privatweg {i}",
                    "postal_code": f"{20000 + i * 50}",
                    "city": cities[i % len(cities)],
                    "country": germany,
                    "email": f"person-{i}@test.de",
                    "phone": f"+49 {i:03d} {i:06d}",
                    "is_active": True,
                }

            partner, created = BusinessPartner.objects.get_or_create(
                partner_number=data["partner_number"], defaults=data
            )
            partners.append(partner)
            if created and i < 10:  # Show first 10 creations
                self._log(f"   ✓ Created: {partner.display_name}")

        if count > 10:
            self._log(f"   ... and {count - 10} more partners")

        return partners

    def create_products(self, count=25):
        """Create sample products"""
        base_products = [
            {
                "product_code": "SW-001",
                "name": "Software Development (hourly)",
                "description": "Custom software development services",
                "product_type": "SERVICE",
                "category": "IT Services",
                "base_price": Decimal("150.00"),
                "unit_of_measure": Product.UnitOfMeasure.HUR,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "LIC-001",
                "name": "Professional License (annual)",
                "description": "Annual software license",
                "product_type": "DIGITAL",
                "category": "Software",
                "base_price": Decimal("999.00"),
                "unit_of_measure": Product.UnitOfMeasure.PCE,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "CONS-001",
                "name": "IT Consulting",
                "description": "Professional IT consulting",
                "product_type": "SERVICE",
                "category": "Consulting",
                "base_price": Decimal("200.00"),
                "unit_of_measure": Product.UnitOfMeasure.HUR,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "SUP-001",
                "name": "Support Package (monthly)",
                "description": "Monthly support and maintenance",
                "product_type": "SERVICE",
                "category": "Support",
                "base_price": Decimal("499.00"),
                "unit_of_measure": Product.UnitOfMeasure.MON,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "TRAIN-001",
                "name": "Training Session",
                "description": "On-site training session",
                "product_type": "SERVICE",
                "category": "Training",
                "base_price": Decimal("800.00"),
                "unit_of_measure": Product.UnitOfMeasure.DAY,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
        ]

        categories = ["IT Services", "Software", "Consulting", "Support", "Training", "Hardware", "Cloud Services"]
        product_types_list = ["SERVICE", "DIGITAL", "PHYSICAL"]
        units = [
            Product.UnitOfMeasure.HUR,
            Product.UnitOfMeasure.DAY,
            Product.UnitOfMeasure.MON,
            Product.UnitOfMeasure.PCE,
            Product.UnitOfMeasure.PCE,
        ]

        products = []

        # Create base products first
        for data in base_products[: min(len(base_products), count)]:
            product, created = Product.objects.get_or_create(product_code=data["product_code"], defaults=data)
            products.append(product)
            status = "✓ Created" if created else "⚠ Already exists"
            self._log(f"   {status}: {product.name}")

        # Generate additional products if count > 5
        for i in range(len(base_products), count):
            code_prefix = ["SW", "LIC", "CONS", "SUP", "TRAIN", "HW", "CLOUD"][i % 7]
            product_code = f"{code_prefix}-{i + 1:03d}"

            data = {
                "product_code": product_code,
                "name": f"Product {i + 1} - {categories[i % len(categories)]}",
                "description": f"Test product {i + 1} for {categories[i % len(categories)]}",
                "product_type": product_types_list[i % len(product_types_list)],
                "category": categories[i % len(categories)],
                "base_price": Decimal(str(50 + (i * 23.5) % 1000)),  # Varied prices
                "unit_of_measure": units[i % len(units)],
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            }

            product, created = Product.objects.get_or_create(product_code=data["product_code"], defaults=data)
            products.append(product)
            if created and i < 10:  # Show first 10 creations
                self._log(f"   ✓ Created: {product.name}")

        if count > 10:
            self._log(f"   ... and {count - 10} more products")

        return products

    def create_invoices(self, company, partners, products, count=50):
        """Create sample invoices with different statuses"""
        invoices = []
        today = timezone.now().date()

        statuses = ["DRAFT", "SENT", "PAID", "CANCELLED"]

        # Create diverse invoices
        for i in range(count):
            partner = partners[i % len(partners)]
            status = statuses[i % len(statuses)]

            # Vary dates
            days_back = (i * 3) % 60  # 0-60 days back
            issue_date = today - timedelta(days=days_back)

            # Calculate due date based on status
            if status == "PAID":
                due_date = issue_date + timedelta(days=14)
            elif status == "DRAFT":
                due_date = today + timedelta(days=14)
            elif status == "CANCELLED":
                due_date = issue_date + timedelta(days=30)
            else:  # SENT - some overdue, some not
                payment_days = 30 if i % 2 == 0 else 14
                due_date = issue_date + timedelta(days=payment_days)

            seq = i + 1
            invoice_number = f"INV-2025-{seq:04d}"

            # Select 1-3 random products for invoice lines
            num_lines = (i % 3) + 1
            lines = []
            for j in range(num_lines):
                product = products[(i + j) % len(products)]
                quantity = Decimal(str((j + 1) * (i % 5 + 1)))
                unit_price = product.base_price
                lines.append((product, quantity, unit_price))

            invoice = self._create_invoice(
                company=company,
                business_partner=partner,
                invoice_number=invoice_number,
                status=status,
                issue_date=issue_date,
                due_date=due_date,
                lines=lines,
            )
            invoices.append(invoice)

            # Only show first 10 invoices in output
            if i >= 10:
                continue

        if count > 10:
            self._log(f"   ... and {count - 10} more invoices")

        return invoices

    def _create_invoice(
        self,
        company,
        business_partner,
        invoice_number,
        status,
        issue_date,
        due_date,
        lines,
    ):
        """Helper to create invoice with lines"""
        # GoBD: Always create as DRAFT first, add lines, then set final status.
        # This avoids auto-lock before lines are added.
        # Extract sequence number from invoice_number (e.g. INV-2025-0042 → 42)
        seq = int(invoice_number.rsplit("-", 1)[-1])
        invoice, created = Invoice.objects.get_or_create(
            invoice_number=invoice_number,
            defaults={
                "company": company,
                "business_partner": business_partner,
                "status": Invoice.InvoiceStatus.DRAFT,
                "issue_date": issue_date,
                "due_date": due_date,
                "currency": "EUR",
                "notes": f"Test invoice for {business_partner.display_name}",
                "sequence_number": seq,
            },
        )

        if created:
            # Create invoice lines (triggers recalculate_totals via InvoiceLine.save)
            for product, quantity, unit_price in lines:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    product=product,
                    description=product.description,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_rate=product.default_tax_rate,
                )

            # Refresh to pick up totals calculated by InvoiceLine.save()
            invoice.refresh_from_db()

            # Now set final status (triggers auto-lock for SENT/PAID/CANCELLED)
            if status != Invoice.InvoiceStatus.DRAFT:
                invoice.status = status
                invoice.save()

            self._log(self.style.SUCCESS(f"   ✓ Created: {invoice_number} ({status}) - {invoice.total_amount}€"))
        else:
            self._log(self.style.WARNING(f"   ⚠ Already exists: {invoice_number}"))

        return invoice
