from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0017_add_billing_period_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceline",
            name="billing_period_start",
            field=models.DateField(
                blank=True,
                help_text="Start of line-specific billing/service period (EN16931 BT-134)",
                null=True,
                verbose_name="Line Billing Period Start",
            ),
        ),
        migrations.AddField(
            model_name="invoiceline",
            name="billing_period_end",
            field=models.DateField(
                blank=True,
                help_text="End of line-specific billing/service period (EN16931 BT-135)",
                null=True,
                verbose_name="Line Billing Period End",
            ),
        ),
    ]
