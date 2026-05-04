"""Add XRechnung B2G email tracking fields to Invoice model (Iteration 9)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0013_add_email_tracking_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="xrechnung_sent_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="XRechnung versendet am",
                help_text="Zeitpunkt der B2G-Zustellung per E-Mail.",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="xrechnung_sent_to",
            field=models.EmailField(
                blank=True,
                max_length=254,
                verbose_name="XRechnung versendet an",
                help_text="E-Mail-Adresse, an die die XRechnung zugestellt wurde.",
            ),
        ),
    ]
