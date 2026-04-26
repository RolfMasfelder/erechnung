from decimal import Decimal

from django.core.management.base import BaseCommand

from invoice_app.models import Product


class Command(BaseCommand):
    help = "Create sample products for testing"

    def handle(self, *args, **options):
        products = [
            {
                "product_code": "SERV-001",
                "name": "Software Development Service",
                "description": "Custom software development services per hour",
                "product_type": "SERVICE",
                "category": "Software Services",
                "base_price": Decimal("150.00"),
                "unit_of_measure": Product.UnitOfMeasure.HUR,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "PROD-001",
                "name": "Professional Software License",
                "description": "Annual license for professional software package",
                "product_type": "DIGITAL",
                "category": "Software",
                "subcategory": "Licenses",
                "base_price": Decimal("299.99"),
                "unit_of_measure": Product.UnitOfMeasure.PCE,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "CONS-001",
                "name": "IT Consulting",
                "description": "Professional IT consulting services",
                "product_type": "SERVICE",
                "category": "Consulting",
                "base_price": Decimal("200.00"),
                "unit_of_measure": Product.UnitOfMeasure.HUR,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
            {
                "product_code": "TRAIN-001",
                "name": "Technical Training Session",
                "description": "Professional technical training and workshops",
                "product_type": "SERVICE",
                "category": "Training",
                "base_price": Decimal("350.00"),
                "unit_of_measure": Product.UnitOfMeasure.DAY,
                "default_tax_rate": Decimal("19.00"),
                "is_active": True,
                "is_sellable": True,
            },
        ]

        created_count = 0
        for product_data in products:
            product, created = Product.objects.get_or_create(
                product_code=product_data["product_code"], defaults=product_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created product: {product.product_code} - {product.name} (€{product.base_price})"
                    )
                )
                created_count += 1
            else:
                self.stdout.write(f"Product already exists: {product.product_code} - {product.name}")

        self.stdout.write(f"\nTotal products created: {created_count}")
        self.stdout.write(f"Total products in database: {Product.objects.count()}")
