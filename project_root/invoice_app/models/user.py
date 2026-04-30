"""
User and role-based access control models for the invoice_app application.
This module defines models for user management, authentication, and RBAC.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRole(models.Model):
    """
    Role-based access control model for managing user permissions.
    Implements comprehensive RBAC for the invoice system.
    """

    class RoleType(models.TextChoices):
        ADMIN = "ADMIN", _("Administrator")
        MANAGER = "MANAGER", _("Manager")
        ACCOUNTANT = "ACCOUNTANT", _("Accountant")
        CLERK = "CLERK", _("Clerk")
        AUDITOR = "AUDITOR", _("Auditor")
        READ_ONLY = "READ_ONLY", _("Read Only")

    # Basic role information
    name = models.CharField(_("Role Name"), max_length=100, unique=True)
    role_type = models.CharField(_("Role Type"), max_length=20, choices=RoleType.choices)
    description = models.TextField(_("Description"), blank=True)

    # Role status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_system_role = models.BooleanField(_("Is System Role"), default=False)  # Cannot be deleted

    # Permission flags for fine-grained control
    # Invoice permissions
    can_create_invoice = models.BooleanField(_("Can Create Invoices"), default=False)
    can_edit_invoice = models.BooleanField(_("Can Edit Invoices"), default=False)
    can_delete_invoice = models.BooleanField(_("Can Delete Invoices"), default=False)
    can_send_invoice = models.BooleanField(_("Can Send Invoices"), default=False)
    can_mark_paid = models.BooleanField(_("Can Mark as Paid"), default=False)
    can_generate_pdf = models.BooleanField(_("Can Generate PDF"), default=False)

    # Customer permissions
    can_create_customer = models.BooleanField(_("Can Create Customers"), default=False)
    can_edit_customer = models.BooleanField(_("Can Edit Customers"), default=False)
    can_delete_customer = models.BooleanField(_("Can Delete Customers"), default=False)

    # Product permissions
    can_create_product = models.BooleanField(_("Can Create Products"), default=False)
    can_edit_product = models.BooleanField(_("Can Edit Products"), default=False)
    can_delete_product = models.BooleanField(_("Can Delete Products"), default=False)
    can_manage_inventory = models.BooleanField(_("Can Manage Inventory"), default=False)

    # Company permissions
    can_edit_company = models.BooleanField(_("Can Edit Company"), default=False)

    # Reporting and audit permissions
    can_view_reports = models.BooleanField(_("Can View Reports"), default=False)
    can_export_data = models.BooleanField(_("Can Export Data"), default=False)
    can_view_audit_logs = models.BooleanField(_("Can View Audit Logs"), default=False)
    can_backup_data = models.BooleanField(_("Can Backup Data"), default=False)

    # System administration permissions
    can_manage_users = models.BooleanField(_("Can Manage Users"), default=False)
    can_manage_roles = models.BooleanField(_("Can Manage Roles"), default=False)
    can_change_settings = models.BooleanField(_("Can Change Settings"), default=False)

    # Financial limits
    max_invoice_amount = models.DecimalField(
        _("Max Invoice Amount"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum invoice amount this role can create/approve"),
    )

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_roles",
        verbose_name=_("Created By"),
    )

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def create_system_roles(cls):
        """Create default system roles with predefined permissions."""
        roles_config = {
            cls.RoleType.ADMIN: {
                "name": "Administrator",
                "description": "Full system access with all permissions",
                "permissions": {
                    "can_create_invoice": True,
                    "can_edit_invoice": True,
                    "can_delete_invoice": True,
                    "can_send_invoice": True,
                    "can_mark_paid": True,
                    "can_generate_pdf": True,
                    "can_create_customer": True,
                    "can_edit_customer": True,
                    "can_delete_customer": True,
                    "can_create_product": True,
                    "can_edit_product": True,
                    "can_delete_product": True,
                    "can_manage_inventory": True,
                    "can_edit_company": True,
                    "can_view_reports": True,
                    "can_export_data": True,
                    "can_view_audit_logs": True,
                    "can_backup_data": True,
                    "can_manage_users": True,
                    "can_manage_roles": True,
                    "can_change_settings": True,
                },
            },
            cls.RoleType.MANAGER: {
                "name": "Manager",
                "description": "Management level access with oversight capabilities",
                "permissions": {
                    "can_create_invoice": True,
                    "can_edit_invoice": True,
                    "can_delete_invoice": True,
                    "can_send_invoice": True,
                    "can_mark_paid": True,
                    "can_generate_pdf": True,
                    "can_create_customer": True,
                    "can_edit_customer": True,
                    "can_delete_customer": False,
                    "can_create_product": True,
                    "can_edit_product": True,
                    "can_delete_product": False,
                    "can_manage_inventory": True,
                    "can_edit_company": False,
                    "can_view_reports": True,
                    "can_export_data": True,
                    "can_view_audit_logs": True,
                    "can_backup_data": False,
                    "can_manage_users": False,
                    "can_manage_roles": False,
                    "can_change_settings": False,
                },
            },
            cls.RoleType.ACCOUNTANT: {
                "name": "Accountant",
                "description": "Financial operations and invoice management",
                "permissions": {
                    "can_create_invoice": True,
                    "can_edit_invoice": True,
                    "can_delete_invoice": False,
                    "can_send_invoice": True,
                    "can_mark_paid": True,
                    "can_generate_pdf": True,
                    "can_create_customer": True,
                    "can_edit_customer": True,
                    "can_delete_customer": False,
                    "can_create_product": False,
                    "can_edit_product": False,
                    "can_delete_product": False,
                    "can_manage_inventory": False,
                    "can_edit_company": False,
                    "can_view_reports": True,
                    "can_export_data": True,
                    "can_view_audit_logs": False,
                    "can_backup_data": False,
                    "can_manage_users": False,
                    "can_manage_roles": False,
                    "can_change_settings": False,
                },
            },
            cls.RoleType.CLERK: {
                "name": "Clerk",
                "description": "Basic invoice and customer operations",
                "permissions": {
                    "can_create_invoice": True,
                    "can_edit_invoice": True,
                    "can_delete_invoice": False,
                    "can_send_invoice": False,
                    "can_mark_paid": False,
                    "can_generate_pdf": True,
                    "can_create_customer": True,
                    "can_edit_customer": True,
                    "can_delete_customer": False,
                    "can_create_product": False,
                    "can_edit_product": False,
                    "can_delete_product": False,
                    "can_manage_inventory": False,
                    "can_edit_company": False,
                    "can_view_reports": False,
                    "can_export_data": False,
                    "can_view_audit_logs": False,
                    "can_backup_data": False,
                    "can_manage_users": False,
                    "can_manage_roles": False,
                    "can_change_settings": False,
                },
                "max_invoice_amount": 10000.00,
            },
            cls.RoleType.AUDITOR: {
                "name": "Auditor",
                "description": "Read-only access with audit capabilities",
                "permissions": {
                    "can_create_invoice": False,
                    "can_edit_invoice": False,
                    "can_delete_invoice": False,
                    "can_send_invoice": False,
                    "can_mark_paid": False,
                    "can_generate_pdf": False,
                    "can_create_customer": False,
                    "can_edit_customer": False,
                    "can_delete_customer": False,
                    "can_create_product": False,
                    "can_edit_product": False,
                    "can_delete_product": False,
                    "can_manage_inventory": False,
                    "can_edit_company": False,
                    "can_view_reports": True,
                    "can_export_data": True,
                    "can_view_audit_logs": True,
                    "can_backup_data": False,
                    "can_manage_users": False,
                    "can_manage_roles": False,
                    "can_change_settings": False,
                },
            },
            cls.RoleType.READ_ONLY: {
                "name": "Read Only",
                "description": "View-only access to all data",
                "permissions": {
                    "can_create_invoice": False,
                    "can_edit_invoice": False,
                    "can_delete_invoice": False,
                    "can_send_invoice": False,
                    "can_mark_paid": False,
                    "can_generate_pdf": False,
                    "can_create_customer": False,
                    "can_edit_customer": False,
                    "can_delete_customer": False,
                    "can_create_product": False,
                    "can_edit_product": False,
                    "can_delete_product": False,
                    "can_manage_inventory": False,
                    "can_edit_company": False,
                    "can_view_reports": True,
                    "can_export_data": False,
                    "can_view_audit_logs": False,
                    "can_backup_data": False,
                    "can_manage_users": False,
                    "can_manage_roles": False,
                    "can_change_settings": False,
                },
            },
        }

        created_roles = []
        for role_type, config in roles_config.items():
            role, created = cls.objects.get_or_create(
                role_type=role_type,
                defaults={
                    "name": config["name"],
                    "description": config["description"],
                    "is_system_role": True,
                    **config["permissions"],
                    "max_invoice_amount": config.get("max_invoice_amount"),
                },
            )
            if created:
                created_roles.append(role)

        return created_roles

    def has_permission(self, permission_name):
        """Check if this role has a specific permission."""
        return getattr(self, permission_name, False)

    def can_approve_invoice_amount(self, amount):
        """Check if role can approve an invoice of given amount."""
        if not self.max_invoice_amount:
            return True  # No limit
        return amount <= self.max_invoice_amount


class UserProfile(models.Model):
    """
    Extended user profile with role assignment and additional user information.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile", verbose_name=_("User")
    )

    # Role assignment
    role = models.ForeignKey(UserRole, on_delete=models.PROTECT, related_name="users", verbose_name=_("Role"))

    # Additional user information
    employee_id = models.CharField(_("Employee ID"), max_length=50, blank=True)
    department = models.CharField(_("Department"), max_length=100, blank=True)
    phone = models.CharField(_("Phone"), max_length=50, blank=True)
    mobile = models.CharField(_("Mobile"), max_length=50, blank=True)

    # Settings and preferences
    language = models.CharField(
        _("Language"),
        max_length=10,
        default="en",
        choices=[
            ("en", _("English")),
            ("de", _("German")),
            ("fr", _("French")),
            ("es", _("Spanish")),
        ],
    )
    timezone = models.CharField(_("Timezone"), max_length=50, default="UTC")
    date_format = models.CharField(
        _("Date Format"),
        max_length=20,
        default="%Y-%m-%d",
        choices=[
            ("%Y-%m-%d", "YYYY-MM-DD"),
            ("%d.%m.%Y", "DD.MM.YYYY"),
            ("%m/%d/%Y", "MM/DD/YYYY"),
            ("%d/%m/%Y", "DD/MM/YYYY"),
        ],
    )

    # Notification preferences
    email_notifications = models.BooleanField(_("Email Notifications"), default=True)
    notify_invoice_paid = models.BooleanField(_("Notify on Invoice Paid"), default=True)
    notify_invoice_overdue = models.BooleanField(_("Notify on Invoice Overdue"), default=True)

    # Default values for new invoices
    default_currency = models.CharField(_("Default Currency"), max_length=3, default="EUR")
    default_payment_terms_days = models.PositiveIntegerField(_("Default Payment Terms (days)"), default=30)

    # Security settings
    last_login_ip = models.GenericIPAddressField(_("Last Login IP"), null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(_("Failed Login Attempts"), default=0)
    account_locked_until = models.DateTimeField(_("Account Locked Until"), null=True, blank=True)
    password_changed_at = models.DateTimeField(_("Password Changed At"), null=True, blank=True)
    must_change_password = models.BooleanField(_("Must Change Password"), default=False)

    # Multi-factor authentication
    mfa_enabled = models.BooleanField(_("MFA Enabled"), default=False)
    mfa_secret = models.CharField(_("MFA Secret"), max_length=32, blank=True)
    backup_codes = models.JSONField(_("Backup Codes"), default=list, blank=True)

    # Session management
    concurrent_sessions_limit = models.PositiveIntegerField(_("Concurrent Sessions Limit"), default=3)

    # Audit fields
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    @property
    def is_account_locked(self):
        """Check if account is currently locked."""
        if not self.account_locked_until:
            return False
        return timezone.now() < self.account_locked_until

    def lock_account(self, duration_minutes=30):
        """Lock the account for specified duration."""
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save()

    def unlock_account(self):
        """Unlock the account and reset failed attempts."""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save()

    def record_failed_login(self):
        """Record a failed login attempt."""
        self.failed_login_attempts += 1

        # Auto-lock after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)

        self.save()

    def record_successful_login(self, ip_address=None):
        """Record a successful login."""
        self.failed_login_attempts = 0
        self.last_login_ip = ip_address
        self.save()

    def has_permission(self, permission_name):
        """Check if user has a specific permission through their role."""
        return self.role.has_permission(permission_name)

    def can_approve_invoice_amount(self, amount):
        """Check if user can approve an invoice of given amount."""
        return self.role.can_approve_invoice_amount(amount)
