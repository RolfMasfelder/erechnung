from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0018_invoiceline_billing_period_bt134_bt135"),
    ]

    operations = [
        # BG-15: Delivery Address (BT-75 / BT-76 / BT-77 / BT-78 / BT-80)
        migrations.AddField(
            model_name="invoice",
            name="delivery_address_line1",
            field=models.CharField(
                blank=True,
                help_text="Street and house number of delivery address (EN16931 BT-75)",
                max_length=200,
                verbose_name="Delivery Address Line 1",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="delivery_address_line2",
            field=models.CharField(
                blank=True,
                help_text="Additional delivery address information (EN16931 BT-76)",
                max_length=200,
                verbose_name="Delivery Address Line 2",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="delivery_city",
            field=models.CharField(
                blank=True,
                help_text="City of delivery address (EN16931 BT-77)",
                max_length=100,
                verbose_name="Delivery City",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="delivery_postal_code",
            field=models.CharField(
                blank=True,
                help_text="Postal code of delivery address (EN16931 BT-78)",
                max_length=20,
                verbose_name="Delivery Postal Code",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="delivery_country",
            field=models.CharField(
                blank=True,
                help_text="ISO 3166-1 alpha-2 country code of delivery address (EN16931 BT-80)",
                max_length=2,
                verbose_name="Delivery Country",
            ),
        ),
        # BG-22: PrepaidAmount (BT-113) + RoundingAmount (BT-114)
        migrations.AddField(
            model_name="invoice",
            name="prepaid_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Amount already paid / advance payment (EN16931 BT-113)",
                max_digits=15,
                verbose_name="Prepaid Amount",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="rounding_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Rounding adjustment for the due amount (EN16931 BT-114)",
                max_digits=15,
                verbose_name="Rounding Amount",
            ),
        ),
    ]
