"""Add user notification + invoice-default preferences to UserProfile."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice_app", "0011_add_edit_lock_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="email_notifications",
            field=models.BooleanField(default=True, verbose_name="Email Notifications"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="notify_invoice_paid",
            field=models.BooleanField(default=True, verbose_name="Notify on Invoice Paid"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="notify_invoice_overdue",
            field=models.BooleanField(default=True, verbose_name="Notify on Invoice Overdue"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="default_currency",
            field=models.CharField(default="EUR", max_length=3, verbose_name="Default Currency"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="default_payment_terms_days",
            field=models.PositiveIntegerField(default=30, verbose_name="Default Payment Terms (days)"),
        ),
    ]
