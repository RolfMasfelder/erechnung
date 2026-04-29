"""Add email tracking fields to Invoice model (3.5 E-Mail-Versand)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0012_user_settings_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="last_emailed_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="Zuletzt per E-Mail versendet am",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_email_recipient",
            field=models.EmailField(
                blank=True,
                max_length=254,
                verbose_name="Letzter E-Mail-Empfänger",
            ),
        ),
    ]
