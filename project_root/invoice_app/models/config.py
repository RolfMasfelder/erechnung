"""
System configuration models for the invoice_app application.
This module defines models for managing application settings and configuration.
"""

import json

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SystemConfig(models.Model):
    """
    System configuration model for application settings.
    Provides a flexible way to manage application configuration.
    """

    class ConfigType(models.TextChoices):
        STRING = "STRING", _("String")
        INTEGER = "INTEGER", _("Integer")
        FLOAT = "FLOAT", _("Float")
        BOOLEAN = "BOOLEAN", _("Boolean")
        JSON = "JSON", _("JSON")

    class ConfigCategory(models.TextChoices):
        GENERAL = "GENERAL", _("General")
        SECURITY = "SECURITY", _("Security")
        EMAIL = "EMAIL", _("Email")
        PDF = "PDF", _("PDF Generation")
        XML = "XML", _("XML/ZUGFeRD")
        INTEGRATION = "INTEGRATION", _("Integration")
        BACKUP = "BACKUP", _("Backup")

    # Configuration identification
    key = models.CharField(_("Configuration Key"), max_length=100, unique=True)
    category = models.CharField(_("Category"), max_length=20, choices=ConfigCategory.choices)

    # Configuration value and metadata
    value = models.TextField(_("Value"))
    value_type = models.CharField(
        _("Value Type"), max_length=10, choices=ConfigType.choices, default=ConfigType.STRING
    )
    default_value = models.TextField(_("Default Value"), blank=True)

    # Configuration description and validation
    name = models.CharField(_("Display Name"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    validation_regex = models.CharField(_("Validation Regex"), max_length=500, blank=True)
    choices = models.JSONField(_("Choices"), default=list, blank=True, help_text=_("List of valid choices"))

    # Configuration behavior
    is_required = models.BooleanField(_("Is Required"), default=True)
    is_sensitive = models.BooleanField(_("Is Sensitive"), default=False)  # Hide in logs/UI
    is_system = models.BooleanField(_("Is System Setting"), default=False)  # Cannot be deleted
    requires_restart = models.BooleanField(_("Requires Restart"), default=False)

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_configs",
        verbose_name=_("Updated By"),
    )

    class Meta:
        verbose_name = _("System Configuration")
        verbose_name_plural = _("System Configurations")
        ordering = ["category", "key"]

    def __str__(self):
        return f"{self.category}: {self.name}"

    def get_value(self):
        """Get the typed value of the configuration."""
        if self.value_type == self.ConfigType.BOOLEAN:
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == self.ConfigType.INTEGER:
            return int(self.value)
        elif self.value_type == self.ConfigType.FLOAT:
            return float(self.value)
        elif self.value_type == self.ConfigType.JSON:
            return json.loads(self.value)
        else:
            return self.value

    def set_value(self, value):
        """Set the value with proper type conversion."""
        if self.value_type == self.ConfigType.BOOLEAN:
            self.value = str(bool(value)).lower()
        elif self.value_type == self.ConfigType.JSON:
            self.value = json.dumps(value)
        else:
            self.value = str(value)

    @classmethod
    def get_config(cls, key, default=None):
        """Get configuration value by key."""
        try:
            config = cls.objects.get(key=key)
            return config.get_value()
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_config(cls, key, value, user=None):
        """Set configuration value by key."""
        try:
            config = cls.objects.get(key=key)
            config.set_value(value)
            config.updated_by = user
            config.save()
            return config
        except cls.DoesNotExist as exc:
            raise ValueError(f"Configuration key '{key}' does not exist") from exc

    @classmethod
    def create_default_configs(cls):
        """Create default system configurations."""
        default_configs = [
            # General settings
            {
                "key": "company_name",
                "category": cls.ConfigCategory.GENERAL,
                "name": "Company Name",
                "description": "Name of the company issuing invoices",
                "value": "Your Company Name",
                "value_type": cls.ConfigType.STRING,
                "is_required": True,
            },
            {
                "key": "default_currency",
                "category": cls.ConfigCategory.GENERAL,
                "name": "Default Currency",
                "description": "Default currency for new invoices",
                "value": "EUR",
                "value_type": cls.ConfigType.STRING,
                "choices": ["EUR", "USD", "GBP", "CHF"],
                "is_required": True,
            },
            {
                "key": "default_payment_terms",
                "category": cls.ConfigCategory.GENERAL,
                "name": "Default Payment Terms",
                "description": "Default payment terms in days",
                "value": "30",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": True,
            },
            # Security settings
            {
                "key": "session_timeout_minutes",
                "category": cls.ConfigCategory.SECURITY,
                "name": "Session Timeout",
                "description": "Session timeout in minutes",
                "value": "480",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": True,
            },
            {
                "key": "max_failed_logins",
                "category": cls.ConfigCategory.SECURITY,
                "name": "Max Failed Login Attempts",
                "description": "Maximum failed login attempts before account lock",
                "value": "5",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": True,
            },
            {
                "key": "account_lockout_minutes",
                "category": cls.ConfigCategory.SECURITY,
                "name": "Account Lockout Duration",
                "description": "Account lockout duration in minutes",
                "value": "30",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": True,
            },
            # Email settings
            {
                "key": "smtp_host",
                "category": cls.ConfigCategory.EMAIL,
                "name": "SMTP Host",
                "description": "SMTP server hostname",
                "value": "localhost",
                "value_type": cls.ConfigType.STRING,
                "is_required": False,
            },
            {
                "key": "smtp_port",
                "category": cls.ConfigCategory.EMAIL,
                "name": "SMTP Port",
                "description": "SMTP server port",
                "value": "587",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": False,
            },
            # PDF settings
            {
                "key": "pdf_generation_timeout",
                "category": cls.ConfigCategory.PDF,
                "name": "PDF Generation Timeout",
                "description": "PDF generation timeout in seconds",
                "value": "60",
                "value_type": cls.ConfigType.INTEGER,
                "is_required": True,
            },
            # ZUGFeRD settings
            {
                "key": "default_zugferd_profile",
                "category": cls.ConfigCategory.XML,
                "name": "Default ZUGFeRD Profile",
                "description": "Default ZUGFeRD profile for new invoices",
                "value": "BASIC",
                "value_type": cls.ConfigType.STRING,
                "choices": ["MINIMUM", "BASIC", "COMFORT", "EXTENDED"],
                "is_required": True,
            },
        ]

        created_configs = []
        for config_data in default_configs:
            config, created = cls.objects.get_or_create(
                key=config_data["key"],
                defaults={
                    **config_data,
                    "is_system": True,
                },
            )
            if created:
                created_configs.append(config)

        return created_configs
