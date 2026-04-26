"""
AuditLog model for the invoice_app application.

Comprehensive audit logging for tracking all system activities.
Essential for compliance (GoBD) and security monitoring.
"""

import hashlib
import json
import socket
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from invoice_app.models.helpers import serialize_for_audit


class AuditLog(models.Model):
    """
    Comprehensive audit log model for tracking all system activities.
    Essential for compliance (GoBD) and security monitoring.
    """

    class ActionType(models.TextChoices):
        CREATE = "CREATE", _("Create")
        READ = "READ", _("Read")
        UPDATE = "UPDATE", _("Update")
        DELETE = "DELETE", _("Delete")
        LOGIN = "LOGIN", _("Login")
        LOGOUT = "LOGOUT", _("Logout")
        LOGIN_FAILED = "LOGIN_FAILED", _("Login Failed")
        ACCESS_DENIED = "ACCESS_DENIED", _("Access Denied")
        EXPORT = "EXPORT", _("Export")
        IMPORT = "IMPORT", _("Import")
        GENERATE_PDF = "GENERATE_PDF", _("Generate PDF")
        SEND_EMAIL = "SEND_EMAIL", _("Send Email")
        BACKUP = "BACKUP", _("Backup")
        RESTORE = "RESTORE", _("Restore")
        CONFIG_CHANGE = "CONFIG_CHANGE", _("Configuration Change")
        SECURITY_EVENT = "SECURITY_EVENT", _("Security Event")

    class Severity(models.TextChoices):
        LOW = "LOW", _("Low")
        MEDIUM = "MEDIUM", _("Medium")
        HIGH = "HIGH", _("High")
        CRITICAL = "CRITICAL", _("Critical")

    # Event identification
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)
    event_id = models.UUIDField(_("Event ID"), default=uuid.uuid4, unique=True, db_index=True)

    # User and session information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("User"),
    )
    username = models.CharField(_("Username"), max_length=150, blank=True)  # Store username even if user is deleted
    session_key = models.CharField(_("Session Key"), max_length=40, blank=True)

    # Action details
    action = models.CharField(_("Action"), max_length=20, choices=ActionType.choices, db_index=True)
    severity = models.CharField(
        _("Severity"), max_length=10, choices=Severity.choices, default=Severity.LOW, db_index=True
    )

    # Target object information
    object_type = models.CharField(_("Object Type"), max_length=100, blank=True, db_index=True)
    object_id = models.CharField(_("Object ID"), max_length=100, blank=True, db_index=True)
    object_repr = models.CharField(_("Object Representation"), max_length=255, blank=True)

    # Event description and context
    description = models.TextField(_("Description"))
    details = models.JSONField(_("Details"), default=dict, blank=True)  # Additional structured data

    # Request/response information
    ip_address = models.GenericIPAddressField(_("IP Address"), null=True, blank=True, db_index=True)
    user_agent = models.TextField(_("User Agent"), blank=True)
    request_method = models.CharField(_("Request Method"), max_length=10, null=True, blank=True)
    request_path = models.TextField(_("Request Path"), null=True, blank=True)
    response_status = models.PositiveIntegerField(_("Response Status"), null=True, blank=True)

    # Data changes (for UPDATE actions)
    old_values = models.JSONField(_("Old Values"), default=dict, blank=True)
    new_values = models.JSONField(_("New Values"), default=dict, blank=True)

    # Compliance and security
    is_compliance_relevant = models.BooleanField(_("Compliance Relevant"), default=False, db_index=True)
    is_security_event = models.BooleanField(_("Security Event"), default=False, db_index=True)
    retention_until = models.DateTimeField(_("Retention Until"), null=True, blank=True, db_index=True)

    # GoBD: Kryptographische Hash-Kette
    entry_hash = models.CharField(
        _("Entry Hash"),
        max_length=64,
        blank=True,
        help_text=_("SHA-256 Hash dieses Eintrags (inkl. Vorgänger-Hash)"),
    )
    previous_entry_hash = models.CharField(
        _("Vorheriger Entry Hash"),
        max_length=64,
        blank=True,
        help_text=_("Hash des vorherigen Audit-Log-Eintrags (Kette)"),
    )

    # System information
    server_name = models.CharField(_("Server Name"), max_length=255, blank=True)
    application_version = models.CharField(_("Application Version"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "action"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["ip_address", "timestamp"]),
            models.Index(fields=["is_compliance_relevant", "timestamp"]),
            models.Index(fields=["is_security_event", "timestamp"]),
            models.Index(fields=["severity", "timestamp"]),
            models.Index(fields=["retention_until"]),
        ]
        # Prevent modifications to audit logs
        permissions = [
            ("view_audit_log", "Can view audit logs"),
            ("export_audit_log", "Can export audit logs"),
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.get_action_display()} - {self.username or 'Anonymous'}"

    @property
    def is_expired(self):
        """Check if the audit log entry has expired based on retention policy."""
        if not self.retention_until:
            return False
        return timezone.now() > self.retention_until

    @classmethod
    def log_action(
        cls,
        action,
        user=None,
        request=None,
        object_instance=None,
        description="",
        details=None,
        severity=None,
        **kwargs,
    ):
        """
        Convenience method to create audit log entries.

        Args:
            action: ActionType choice
            user: User instance or None
            request: HttpRequest instance or None
            object_instance: Model instance being acted upon
            description: Human-readable description
            details: Additional structured data (dict)
            severity: Severity choice
            **kwargs: Additional fields to set
        """
        audit_data = {
            "action": action,
            "description": description,
            "details": details or {},
            "severity": severity or cls.Severity.LOW,
        }

        # User information
        if user:
            audit_data["user"] = user
            audit_data["username"] = user.username

        # Request information
        if request:
            audit_data["ip_address"] = cls._get_client_ip(request)
            audit_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
            audit_data["request_method"] = request.method
            audit_data["request_path"] = request.get_full_path()
            audit_data["session_key"] = getattr(request.session, "session_key", "") or ""

            if not user and hasattr(request, "user") and request.user.is_authenticated:
                audit_data["user"] = request.user
                audit_data["username"] = request.user.username

        # Object information
        if object_instance:
            audit_data["object_type"] = object_instance._meta.label
            audit_data["object_id"] = str(object_instance.pk)
            audit_data["object_repr"] = str(object_instance)

        # Compliance relevance
        if action in [cls.ActionType.CREATE, cls.ActionType.UPDATE, cls.ActionType.DELETE]:
            audit_data["is_compliance_relevant"] = True

        # Security events
        if action in [cls.ActionType.LOGIN_FAILED, cls.ActionType.ACCESS_DENIED, cls.ActionType.SECURITY_EVENT]:
            audit_data["is_security_event"] = True
            audit_data["severity"] = cls.Severity.HIGH

        # Set retention period (default 10 years for compliance)
        if audit_data.get("is_compliance_relevant"):
            audit_data["retention_until"] = timezone.now() + timezone.timedelta(days=3650)  # 10 years
        else:
            audit_data["retention_until"] = timezone.now() + timezone.timedelta(days=365)  # 1 year

        # Add system information
        audit_data["server_name"] = socket.gethostname()

        # Merge any additional kwargs
        audit_data.update(kwargs)

        # GoBD: Hash-Kette — Link to previous entry and compute hash
        last_entry = cls.objects.order_by("-timestamp", "-id").first()
        if last_entry and last_entry.entry_hash:
            audit_data["previous_entry_hash"] = last_entry.entry_hash

        instance = cls(**audit_data)
        instance.entry_hash = instance.calculate_entry_hash()
        instance.save(force_insert=True)
        return instance

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def log_model_change(cls, action, instance, user=None, request=None, old_values=None, new_values=None):
        """
        Log model changes with before/after values.

        Args:
            action: CREATE, UPDATE, or DELETE
            instance: Model instance
            user: User making the change
            request: HttpRequest
            old_values: Dict of old field values (for UPDATE/DELETE)
            new_values: Dict of new field values (for CREATE/UPDATE)
        """
        description = f"{action.title()} {instance._meta.verbose_name}: {instance}"

        return cls.log_action(
            action=action,
            user=user,
            request=request,
            object_instance=instance,
            description=description,
            old_values=serialize_for_audit(old_values or {}),
            new_values=serialize_for_audit(new_values or {}),
            severity=cls.Severity.MEDIUM,
        )

    @classmethod
    def cleanup_expired(cls):
        """Remove expired audit log entries based on retention policy."""
        expired_count = cls.objects.filter(retention_until__lt=timezone.now()).count()

        if expired_count > 0:
            cls.objects.filter(retention_until__lt=timezone.now()).delete()

        return expired_count

    # ── GoBD: Kryptographische Hash-Kette ──────────────────────────────────

    def calculate_entry_hash(self):
        """Berechnet SHA-256 Hash des Audit-Log-Eintrags inkl. Vorgänger-Hash.

        Die Hash-Kette ermöglicht den Nachweis, dass keine Einträge
        manipuliert, gelöscht oder eingefügt wurden.
        """
        data = {
            "event_id": str(self.event_id),
            "action": self.action,
            "username": self.username or "",
            "object_type": self.object_type or "",
            "object_id": self.object_id or "",
            "description": self.description or "",
            "previous_hash": self.previous_entry_hash or "",
        }
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    @classmethod
    def verify_chain(cls, limit=1000):
        """Prüft Integrität der Audit-Log-Hash-Kette.

        Returns:
            list[dict]: Liste von Integritätsverletzungen (leer = alles OK).
        """
        violations = []
        entries = cls.objects.order_by("timestamp", "id")[:limit]

        for entry in entries:
            if not entry.entry_hash:
                continue  # Kein Hash vorhanden (Legacy-Eintrag)

            expected_hash = entry.calculate_entry_hash()
            if expected_hash != entry.entry_hash:
                violations.append(
                    {
                        "event_id": str(entry.event_id),
                        "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                        "expected_hash": entry.entry_hash,
                        "actual_hash": expected_hash,
                    }
                )

        return violations
