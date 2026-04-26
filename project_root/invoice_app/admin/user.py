"""Admin configuration for User-related models (UserRole, UserProfile)."""

from django.contrib import admin

from invoice_app.admin.mixins import RBACPermissionMixin
from invoice_app.models import UserProfile, UserRole


@admin.register(UserRole)
class UserRoleAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for UserRole model with comprehensive RBAC management."""

    list_display = ("name", "role_type", "is_active", "is_system_role", "permission_summary", "user_count")
    list_filter = ("role_type", "is_active", "is_system_role")
    search_fields = ("name", "description")
    readonly_fields = ("user_count", "permission_summary")

    fieldsets = (
        ("Role Information", {"fields": ("name", "role_type", "description", "is_active", "is_system_role")}),
        (
            "Invoice Permissions",
            {
                "fields": (
                    "can_create_invoice",
                    "can_edit_invoice",
                    "can_delete_invoice",
                    "can_send_invoice",
                    "can_mark_paid",
                    "can_generate_pdf",
                )
            },
        ),
        ("Customer Permissions", {"fields": ("can_create_customer", "can_edit_customer", "can_delete_customer")}),
        (
            "Product Permissions",
            {"fields": ("can_create_product", "can_edit_product", "can_delete_product", "can_manage_inventory")},
        ),
        ("Company Permissions", {"fields": ("can_edit_company",)}),
        (
            "System Permissions",
            {
                "fields": (
                    "can_view_reports",
                    "can_export_data",
                    "can_view_audit_logs",
                    "can_backup_data",
                    "can_manage_users",
                    "can_manage_roles",
                    "can_change_settings",
                )
            },
        ),
        ("Statistics", {"fields": ("user_count", "permission_summary"), "classes": ("collapse",)}),
    )

    def permission_summary(self, obj):
        """Display a summary of key permissions."""
        permissions = []
        if obj.can_create_invoice:
            permissions.append("Create Invoices")
        if obj.can_edit_invoice:
            permissions.append("Edit Invoices")
        if obj.can_delete_invoice:
            permissions.append("Delete Invoices")
        if obj.can_manage_users:
            permissions.append("Manage Users")
        if obj.can_manage_roles:
            permissions.append("Manage Roles")
        if obj.can_change_settings:
            permissions.append("System Settings")

        if not permissions:
            return "No special permissions"
        return ", ".join(permissions[:3]) + ("..." if len(permissions) > 3 else "")

    permission_summary.short_description = "Key Permissions"

    def user_count(self, obj):
        """Display number of users with this role."""
        return obj.users.count()

    user_count.short_description = "Users Count"

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of system roles."""
        if obj and obj.is_system_role:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(UserProfile)
class UserProfileAdmin(RBACPermissionMixin, admin.ModelAdmin):
    """Admin interface for UserProfile model with security features."""

    list_display = (
        "username",
        "role_name",
        "employee_id",
        "department",
        "is_user_active",
        "mfa_status",
        "last_login_display",
        "security_status",
    )
    list_filter = (
        "role__role_type",
        "department",
        "language",
        "mfa_enabled",
        "user__is_active",
        "must_change_password",
    )
    search_fields = (
        "user__username",
        "user__email",
        "employee_id",
        "department",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "username",
        "last_login_ip",
        "failed_login_attempts",
        "account_locked_until",
        "password_changed_at",
        "last_login_display",
        "security_status",
    )

    fieldsets = (
        ("User Information", {"fields": ("user", "username", "role")}),
        ("Employee Details", {"fields": ("employee_id", "department", "phone", "mobile")}),
        ("Preferences", {"fields": ("language", "timezone", "date_format")}),
        (
            "Security Settings",
            {
                "fields": (
                    "last_login_ip",
                    "failed_login_attempts",
                    "account_locked_until",
                    "password_changed_at",
                    "must_change_password",
                )
            },
        ),
        (
            "Multi-Factor Authentication",
            {"fields": ("mfa_enabled", "mfa_secret", "backup_codes"), "classes": ("collapse",)},
        ),
        ("Status Summary", {"fields": ("last_login_display", "security_status"), "classes": ("collapse",)}),
    )

    def username(self, obj):
        """Display username from related User model."""
        return obj.user.username

    username.short_description = "Username"

    def role_name(self, obj):
        """Display role name."""
        return obj.role.name

    role_name.short_description = "Role"

    def is_user_active(self, obj):
        """Display if user account is active."""
        return obj.user.is_active

    is_user_active.short_description = "Active"
    is_user_active.boolean = True

    def mfa_status(self, obj):
        """Display MFA status."""
        return "✓ Enabled" if obj.mfa_enabled else "✗ Disabled"

    mfa_status.short_description = "MFA"

    def last_login_display(self, obj):
        """Display last login information."""
        if obj.user.last_login:
            login_info = obj.user.last_login.strftime("%Y-%m-%d %H:%M")
            if obj.last_login_ip:
                login_info += f" from {obj.last_login_ip}"
            return login_info
        return "Never"

    last_login_display.short_description = "Last Login"

    def security_status(self, obj):
        """Display security status summary."""
        issues = []
        if obj.failed_login_attempts > 0:
            issues.append(f"{obj.failed_login_attempts} failed attempts")
        if obj.account_locked_until:
            issues.append("Account locked")
        if obj.must_change_password:
            issues.append("Password change required")
        if not obj.mfa_enabled:
            issues.append("MFA disabled")

        if not issues:
            return "✓ Secure"
        return "⚠ " + ", ".join(issues)

    security_status.short_description = "Security Status"
