"""
Custom permission classes for JWT authentication with RBAC integration.
"""

import logging

from rest_framework import permissions

from invoice_app.models import UserProfile


logger = logging.getLogger(__name__)


class IsAuthenticatedWithRBAC(permissions.BasePermission):
    """
    Custom permission that checks JWT authentication and RBAC permissions.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated and has required permissions."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers always have permission
        if request.user.is_superuser:
            return True

        # Check if account is locked
        try:
            user_profile = request.user.profile
            if user_profile.is_account_locked:
                return False
        except UserProfile.DoesNotExist:
            # No UserProfile exists - allow access for authenticated users without profile
            # This is expected for users who haven't been assigned a profile yet
            logger.info(
                "User %s (id=%s) has no UserProfile - granting basic access",
                request.user.username,
                request.user.id,
            )

        return True


class CanCreateInvoice(permissions.BasePermission):
    """Permission to create invoices."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and user_profile.role.can_create_invoice:
                return True
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanCreateInvoice denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class CanApproveInvoice(permissions.BasePermission):
    """Permission to approve invoices based on amount."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            # For general approval permission, check if user has any invoice amount limit
            if user_profile.role and user_profile.role.max_invoice_amount and user_profile.role.max_invoice_amount > 0:
                return True
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanApproveInvoice denied: User %s has no UserProfile",
                request.user.username,
            )

        return False

    def has_object_permission(self, request, view, obj):
        """Check approval amount against specific invoice object."""
        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and hasattr(obj, "total_amount"):
                return user_profile.role.can_approve_invoice_amount(obj.total_amount)
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanApproveInvoice object permission denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class CanEditInvoice(permissions.BasePermission):
    """Permission to edit invoices."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and user_profile.role.can_edit_invoice:
                return True
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanEditInvoice denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class CanDeleteInvoice(permissions.BasePermission):
    """Permission to delete invoices."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and user_profile.role.can_delete_invoice:
                return True
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanDeleteInvoice denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class CanManageUsers(permissions.BasePermission):
    """Permission to manage users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and user_profile.role.can_manage_users:
                return True
        except UserProfile.DoesNotExist:
            logger.debug(
                "CanManageUsers denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class HasApprovalAmount(permissions.BasePermission):
    """
    Permission that checks if user can approve amounts up to a certain limit.
    Use this permission with a custom check in the view.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        # This permission requires additional context from the view
        # The view should override has_object_permission or implement custom logic
        return True

    def has_object_permission(self, request, view, obj):
        """Check approval amount against object's amount."""
        if request.user.is_superuser:
            return True

        try:
            user_profile = request.user.profile
            if user_profile.role and user_profile.role.max_invoice_amount:
                # Assuming obj has a total_amount field (like Invoice)
                if hasattr(obj, "total_amount"):
                    return obj.total_amount <= user_profile.role.max_invoice_amount
        except UserProfile.DoesNotExist:
            logger.debug(
                "HasApprovalAmount object permission denied: User %s has no UserProfile",
                request.user.username,
            )

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has a `created_by` field.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to the owner of the object
        return obj.created_by == request.user
