# Data migration to load initial country data with VAT rates

import json
import os

from django.db import migrations
from django.utils import timezone


def load_countries(apps, schema_editor):
    """Load country data from fixtures or inline data."""
    Country = apps.get_model("invoice_app", "Country")

    # Skip if countries already exist (use try/except for fresh DB)
    try:
        if Country.objects.exists():
            return
    except Exception:
        pass  # Table might not exist yet in some edge cases

    # Path to fixtures file
    fixtures_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "fixtures",
        "countries.json",
    )

    now = timezone.now()

    if os.path.exists(fixtures_path):
        # Load from fixtures file
        with open(fixtures_path, encoding="utf-8") as f:
            fixtures = json.load(f)

        for item in fixtures:
            if item.get("model") == "invoice_app.country":
                fields = item["fields"]
                Country.objects.create(
                    code=item["pk"],
                    code_alpha3=fields.get("code_alpha3", ""),
                    numeric_code=fields.get("numeric_code", ""),
                    name=fields.get("name", ""),
                    name_local=fields.get("name_local", ""),
                    currency_code=fields.get("currency_code", "EUR"),
                    currency_name=fields.get("currency_name", ""),
                    currency_symbol=fields.get("currency_symbol", ""),
                    default_language=fields.get("default_language", ""),
                    is_eu_member=fields.get("is_eu_member", False),
                    is_eurozone=fields.get("is_eurozone", False),
                    standard_vat_rate=fields.get("standard_vat_rate", 0),
                    reduced_vat_rate=fields.get("reduced_vat_rate"),
                    super_reduced_vat_rate=fields.get("super_reduced_vat_rate"),
                    date_format=fields.get("date_format", "DD.MM.YYYY"),
                    decimal_separator=fields.get("decimal_separator", ","),
                    thousands_separator=fields.get("thousands_separator", "."),
                    is_active=fields.get("is_active", True),
                    created_at=now,
                    updated_at=now,
                )
    else:
        # Fallback: insert essential countries directly
        countries_data = [
            ("DE", "DEU", "276", "Germany", "Deutschland", "EUR", "Euro", "€", "de", True, True, 19.00, 7.00),
            ("AT", "AUT", "040", "Austria", "Österreich", "EUR", "Euro", "€", "de", True, True, 20.00, 10.00),
            (
                "CH",
                "CHE",
                "756",
                "Switzerland",
                "Schweiz",
                "CHF",
                "Swiss Franc",
                "CHF",
                "de",
                False,
                False,
                8.10,
                2.60,
            ),
            ("FR", "FRA", "250", "France", "France", "EUR", "Euro", "€", "fr", True, True, 20.00, 5.50),
            ("IT", "ITA", "380", "Italy", "Italia", "EUR", "Euro", "€", "it", True, True, 22.00, 10.00),
            ("ES", "ESP", "724", "Spain", "España", "EUR", "Euro", "€", "es", True, True, 21.00, 10.00),
            ("NL", "NLD", "528", "Netherlands", "Nederland", "EUR", "Euro", "€", "nl", True, True, 21.00, 9.00),
            ("BE", "BEL", "056", "Belgium", "België", "EUR", "Euro", "€", "nl", True, True, 21.00, 6.00),
            ("PL", "POL", "616", "Poland", "Polska", "PLN", "Polish Zloty", "zł", "pl", True, False, 23.00, 8.00),
            (
                "GB",
                "GBR",
                "826",
                "United Kingdom",
                "United Kingdom",
                "GBP",
                "British Pound",
                "£",
                "en",
                False,
                False,
                20.00,
                5.00,
            ),
            (
                "US",
                "USA",
                "840",
                "United States",
                "United States",
                "USD",
                "US Dollar",
                "$",
                "en",
                False,
                False,
                0.00,
                None,
            ),
        ]
        for c in countries_data:
            Country.objects.create(
                code=c[0],
                code_alpha3=c[1],
                numeric_code=c[2],
                name=c[3],
                name_local=c[4],
                currency_code=c[5],
                currency_name=c[6],
                currency_symbol=c[7],
                default_language=c[8],
                is_eu_member=c[9],
                is_eurozone=c[10],
                standard_vat_rate=c[11],
                reduced_vat_rate=c[12],
                date_format="DD.MM.YYYY",
                decimal_separator=",",
                thousands_separator=".",
                is_active=True,
                created_at=now,
                updated_at=now,
            )


def unload_countries(apps, schema_editor):
    """Remove all countries (reverse operation)."""
    # Use raw SQL to avoid Django ORM cascade collector issues
    # with historical model states during migration rollback
    schema_editor.execute("DELETE FROM invoice_app_country")


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_countries, unload_countries),
    ]
