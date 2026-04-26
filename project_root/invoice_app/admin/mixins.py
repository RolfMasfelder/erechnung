"""RBAC permission mixin for admin classes."""

from invoice_app.models import UserProfile


class RBACPermissionMixin:
    """Mixin to add RBAC permission checks to admin classes."""

    def has_module_permission(self, request):
        """Check if user has permission to access this module."""
        if not request.user.is_authenticated:
            return False

        # Superuser has all permissions
        if request.user.is_superuser:
            return True

        # Check if user has a profile with appropriate role
        try:
            profile = request.user.profile
            return profile.role.is_active
        except UserProfile.DoesNotExist:
            return False

    def has_view_permission(self, request, obj=None):
        """Check view permission based on user role."""
        if not super().has_view_permission(request, obj):
            return False
        return self._check_rbac_permission(request, "view")

    def has_add_permission(self, request):
        """Check add permission based on user role."""
        if not super().has_add_permission(request):
            return False
        return self._check_rbac_permission(request, "add")

    def has_change_permission(self, request, obj=None):
        """Check change permission based on user role."""
        if not super().has_change_permission(request, obj):
            return False
        return self._check_rbac_permission(request, "change")

    def has_delete_permission(self, request, obj=None):
        """Check delete permission based on user role."""
        if not super().has_delete_permission(request, obj):
            return False
        return self._check_rbac_permission(request, "delete")

    def _check_rbac_permission(self, request, action):
        """Check RBAC permission for specific action."""
        if request.user.is_superuser:
            return True

        try:
            profile = request.user.profile
            role = profile.role

            # Map model to permission attributes
            model_name = self.model._meta.model_name
            permission_map = {
                "company": {
                    "view": True,  # All authenticated users can view
                    "add": role.can_edit_company,
                    "change": role.can_edit_company,
                    "delete": role.can_edit_company,
                },
                "customer": {
                    "view": True,
                    "add": role.can_create_customer,
                    "change": role.can_edit_customer,
                    "delete": role.can_delete_customer,
                },
                "product": {
                    "view": True,
                    "add": role.can_create_product,
                    "change": role.can_edit_product,
                    "delete": role.can_delete_product,
                },
                "invoice": {
                    "view": True,
                    "add": role.can_create_invoice,
                    "change": role.can_edit_invoice,
                    "delete": role.can_delete_invoice,
                },
                "auditlog": {
                    "view": role.can_view_audit_logs,
                    "add": False,  # Audit logs are system-generated
                    "change": False,
                    "delete": role.can_view_audit_logs,  # Only for expired logs
                },
                "userrole": {
                    "view": role.can_manage_roles,
                    "add": role.can_manage_roles,
                    "change": role.can_manage_roles,
                    "delete": role.can_manage_roles,
                },
                "userprofile": {
                    "view": role.can_manage_users,
                    "add": role.can_manage_users,
                    "change": role.can_manage_users,
                    "delete": role.can_manage_users,
                },
                "systemconfig": {
                    "view": role.can_change_settings,
                    "add": role.can_change_settings,
                    "change": role.can_change_settings,
                    "delete": role.can_change_settings,
                },
            }

            # Default to read-only for unlisted models
            permissions = permission_map.get(
                model_name, {"view": True, "add": False, "change": False, "delete": False}
            )
            return permissions.get(action, False)

        except (UserProfile.DoesNotExist, AttributeError):
            return False
