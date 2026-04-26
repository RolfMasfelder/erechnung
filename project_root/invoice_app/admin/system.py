"""Admin configuration for system models (AuditLog, SystemConfig)."""

from django.contrib import admin

from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import AuditLog, SystemConfig, UserProfile


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model with read-only access."""

    list_display = (
        "timestamp",
        "action",
        "username",
        "object_type",
        "object_repr",
        "ip_address",
        "severity",
        "is_compliance_relevant",
        "is_security_event",
    )
    list_filter = ("action", "severity", "is_compliance_relevant", "is_security_event", "object_type", "timestamp")
    search_fields = ("username", "description", "object_repr", "ip_address")
    readonly_fields = (
        "timestamp",
        "event_id",
        "user",
        "username",
        "session_key",
        "action",
        "severity",
        "object_type",
        "object_id",
        "object_repr",
        "description",
        "details",
        "ip_address",
        "user_agent",
        "request_method",
        "request_path",
        "response_status",
        "old_values",
        "new_values",
        "is_compliance_relevant",
        "is_security_event",
        "retention_until",
        "server_name",
        "application_version",
    )
    date_hierarchy = "timestamp"

    fieldsets = (
        ("Event Information", {"fields": ("timestamp", "event_id", "action", "severity", "description")}),
        ("User & Session", {"fields": ("user", "username", "session_key", "ip_address")}),
        ("Target Object", {"fields": ("object_type", "object_id", "object_repr")}),
        (
            "Request Information",
            {"fields": ("request_method", "request_path", "user_agent", "response_status"), "classes": ("collapse",)},
        ),
        ("Data Changes", {"fields": ("old_values", "new_values"), "classes": ("collapse",)}),
        ("Compliance & Security", {"fields": ("is_compliance_relevant", "is_security_event", "retention_until")}),
        (
            "System Information",
            {"fields": ("server_name", "application_version", "details"), "classes": ("collapse",)},
        ),
    )

    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only allow deletion for expired logs."""
        if obj and obj.is_expired:
            return request.user.has_perm("invoice_app.delete_auditlog")
        return False

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("user")


@admin.register(SystemConfig)
class SystemConfigAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for SystemConfig model with configuration management."""

    list_display = ("key", "value_type", "value_preview", "is_sensitive", "is_required", "category", "updated_at")
    list_filter = ("value_type", "category", "is_sensitive", "is_required")
    search_fields = ("key", "description", "category")
    readonly_fields = ("created_at", "updated_at", "value_preview")

    fieldsets = (
        ("Configuration Item", {"fields": ("key", "value_type", "category", "is_required")}),
        ("Value", {"fields": ("value", "default_value")}),
        ("Security & Metadata", {"fields": ("is_sensitive", "name", "description")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def value_preview(self, obj):
        """Display a preview of the configuration value."""
        if obj.is_sensitive:
            return "*** (sensitive)"

        value = obj.get_value()
        if value is None:
            return "(not set)"

        # Truncate long values
        str_value = str(value)
        if len(str_value) > 50:
            return str_value[:47] + "..."
        return str_value

    value_preview.short_description = "Current Value"

    def get_readonly_fields(self, request, obj=None):
        """Make sensitive fields read-only for non-superusers."""
        readonly = list(self.readonly_fields)

        if not request.user.is_superuser:
            try:
                profile = request.user.profile
                if not profile.role.can_change_settings:
                    readonly.extend(["key", "value_type", "category", "value"])
            except UserProfile.DoesNotExist:
                readonly.extend(["key", "value_type", "category", "value"])

        return readonly
