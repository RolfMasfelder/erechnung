"""
Tests for API permissions with RBAC integration.
"""

from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from invoice_app.api.permissions import (
    CanApproveInvoice,
    CanCreateInvoice,
    CanDeleteInvoice,
    CanEditInvoice,
    CanManageUsers,
    HasApprovalAmount,
    IsAuthenticatedWithRBAC,
    IsOwnerOrReadOnly,
)
from invoice_app.models import UserProfile, UserRole
from invoice_app.tests.factories import UserFactory


User = get_user_model()


class BasePermissionTestCase(TestCase):
    """Base class for permission tests with common setup."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.superuser = UserFactory(is_staff=True, is_superuser=True)
        self.regular_user = UserFactory()
        self.regular_user_no_profile = UserFactory()

        # Create test roles (uses get_or_create via factory)
        UserRole.create_system_roles()
        self.admin_role, _ = UserRole.objects.get_or_create(
            name="Admin",
            defaults={
                "role_type": UserRole.RoleType.ADMIN,
                "can_create_invoice": True,
                "can_edit_invoice": True,
                "can_delete_invoice": True,
                "can_manage_users": True,
                "max_invoice_amount": 100000.00,
                "is_system_role": True,
            },
        )
        self.manager_role, _ = UserRole.objects.get_or_create(
            name="Manager",
            defaults={
                "role_type": UserRole.RoleType.MANAGER,
                "can_create_invoice": True,
                "can_edit_invoice": True,
                "can_delete_invoice": False,
                "can_manage_users": False,
                "max_invoice_amount": 50000.00,
                "is_system_role": True,
            },
        )
        self.clerk_role, _ = UserRole.objects.get_or_create(
            name="Clerk",
            defaults={
                "role_type": UserRole.RoleType.CLERK,
                "can_create_invoice": True,
                "can_edit_invoice": False,
                "can_delete_invoice": False,
                "can_manage_users": False,
                "max_invoice_amount": 1000.00,
                "is_system_role": True,
            },
        )
        self.readonly_role, _ = UserRole.objects.get_or_create(
            name="ReadOnly",
            defaults={
                "role_type": UserRole.RoleType.READ_ONLY,
                "can_create_invoice": False,
                "can_edit_invoice": False,
                "can_delete_invoice": False,
                "can_manage_users": False,
                "max_invoice_amount": 0.00,
                "is_system_role": True,
            },
        )

        # Create user profiles
        self.admin_profile = UserProfile.objects.create(user=self.regular_user, role=self.admin_role)
        self.locked_user = UserFactory()
        self.locked_profile = UserProfile.objects.create(
            user=self.locked_user,
            role=self.clerk_role,
            account_locked_until=timezone.now() + timezone.timedelta(hours=1),
        )

    def create_mock_request(self, user=None, method="GET"):
        """Create a mock request with specified user."""
        request = self.factory.get("/")
        request.method = method
        request.user = user or self.regular_user
        return request

    def create_mock_view(self):
        """Create a mock view."""
        return Mock()


class IsAuthenticatedWithRBACTestCase(BasePermissionTestCase):
    """Test IsAuthenticatedWithRBAC permission."""

    def setUp(self):
        super().setUp()
        self.permission = IsAuthenticatedWithRBAC()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_anonymous_user_denied(self):
        """Test that anonymous users are denied."""
        from django.contrib.auth.models import AnonymousUser

        request = self.create_mock_request(user=AnonymousUser())
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_profile_allowed(self):
        """Test that authenticated user with profile is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_locked_user_denied(self):
        """Test that locked users are denied."""
        request = self.create_mock_request(user=self.locked_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_user_without_profile_allowed(self):
        """Test that user without profile is allowed (but logged)."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)


class CanCreateInvoiceTestCase(BasePermissionTestCase):
    """Test CanCreateInvoice permission."""

    def setUp(self):
        super().setUp()
        self.permission = CanCreateInvoice()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_create_permission_allowed(self):
        """Test that user with create permission is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # Admin role can create invoices

    def test_user_without_create_permission_denied(self):
        """Test that user without create permission is denied."""
        # Change to readonly role
        self.admin_profile.role = self.readonly_role
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_user_without_profile_denied(self):
        """Test that user without profile is denied."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)


class CanApproveInvoiceTestCase(BasePermissionTestCase):
    """Test CanApproveInvoice permission."""

    def setUp(self):
        super().setUp()
        self.permission = CanApproveInvoice()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_approval_limit_allowed(self):
        """Test that user with approval limit is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # Admin role has approval limits

    def test_user_without_approval_limit_denied(self):
        """Test that user without approval limit is denied."""
        # Create role without approval limit
        no_approval_role = UserRole.objects.create(
            name="NoApproval", max_invoice_amount=Decimal("0.00"), can_create_invoice=True
        )
        self.admin_profile.role = no_approval_role
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_object_permission(self):
        """Test that superuser has object permission."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()
        mock_invoice = Mock()
        mock_invoice.total_amount = Decimal("1000.00")

        result = self.permission.has_object_permission(request, view, mock_invoice)
        self.assertTrue(result)

    def test_user_object_permission_within_limit(self):
        """Test user object permission within approval limit."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()
        mock_invoice = Mock()
        mock_invoice.total_amount = Decimal("1000.00")  # Admin role has high limit

        result = self.permission.has_object_permission(request, view, mock_invoice)
        self.assertTrue(result)

    def test_user_object_permission_exceeds_limit(self):
        """Test user object permission exceeding approval limit."""
        # Create role with low limit
        low_limit_role = UserRole.objects.create(
            name="LowLimit", max_invoice_amount=Decimal("100.00"), can_create_invoice=True
        )
        self.admin_profile.role = low_limit_role
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()
        mock_invoice = Mock()
        mock_invoice.total_amount = Decimal("1000.00")

        result = self.permission.has_object_permission(request, view, mock_invoice)
        self.assertFalse(result)

    def test_user_without_profile_object_permission_denied(self):
        """Test that user without profile is denied object permission."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()
        mock_invoice = Mock()
        mock_invoice.total_amount = Decimal("100.00")

        result = self.permission.has_object_permission(request, view, mock_invoice)
        self.assertFalse(result)


class CanEditInvoiceTestCase(BasePermissionTestCase):
    """Test CanEditInvoice permission."""

    def setUp(self):
        super().setUp()
        self.permission = CanEditInvoice()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_edit_permission_allowed(self):
        """Test that user with edit permission is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # Admin role can edit invoices

    def test_user_without_edit_permission_denied(self):
        """Test that user without edit permission is denied."""
        self.admin_profile.role = self.readonly_role
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_user_without_profile_denied(self):
        """Test that user without profile is denied."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)


class CanDeleteInvoiceTestCase(BasePermissionTestCase):
    """Test CanDeleteInvoice permission."""

    def setUp(self):
        super().setUp()
        self.permission = CanDeleteInvoice()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_delete_permission_allowed(self):
        """Test that user with delete permission is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # Admin role can delete invoices

    def test_user_without_delete_permission_denied(self):
        """Test that user without delete permission is denied."""
        self.admin_profile.role = self.clerk_role  # Clerk cannot delete
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_user_without_profile_denied(self):
        """Test that user without profile is denied."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)


class CanManageUsersTestCase(BasePermissionTestCase):
    """Test CanManageUsers permission."""

    def setUp(self):
        super().setUp()
        self.permission = CanManageUsers()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_user_with_manage_permission_allowed(self):
        """Test that user with manage permission is allowed."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # Admin role can manage users

    def test_user_without_manage_permission_denied(self):
        """Test that user without manage permission is denied."""
        self.admin_profile.role = self.clerk_role  # Clerk cannot manage users
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_user_without_profile_denied(self):
        """Test that user without profile is denied."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)


class HasApprovalAmountTestCase(BasePermissionTestCase):
    """Test HasApprovalAmount permission."""

    def setUp(self):
        super().setUp()
        self.permission = HasApprovalAmount()

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied."""
        request = self.create_mock_request(user=None)
        request.user = None
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertFalse(result)

    def test_superuser_allowed(self):
        """Test that superusers are always allowed."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)

    def test_authenticated_user_allowed_general_permission(self):
        """Test that authenticated user is allowed general permission."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()

        result = self.permission.has_permission(request, view)
        self.assertTrue(result)  # General permission is True for authenticated users

    def test_superuser_object_permission(self):
        """Test that superuser has object permission."""
        request = self.create_mock_request(user=self.superuser)
        view = self.create_mock_view()
        mock_obj = Mock()
        mock_obj.total_amount = Decimal("1000.00")

        result = self.permission.has_object_permission(request, view, mock_obj)
        self.assertTrue(result)

    def test_user_object_permission_within_limit(self):
        """Test user object permission within approval limit."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()
        mock_obj = Mock()
        mock_obj.total_amount = Decimal("1000.00")  # Admin role has high limit

        result = self.permission.has_object_permission(request, view, mock_obj)
        self.assertTrue(result)

    def test_user_object_permission_exceeds_limit(self):
        """Test user object permission exceeding approval limit."""
        # Create role with low limit
        low_limit_role = UserRole.objects.create(
            name="LowLimit2", max_invoice_amount=Decimal("100.00"), can_create_invoice=True
        )
        self.admin_profile.role = low_limit_role
        self.admin_profile.save()

        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()
        mock_obj = Mock()
        mock_obj.total_amount = Decimal("1000.00")

        result = self.permission.has_object_permission(request, view, mock_obj)
        self.assertFalse(result)

    def test_object_without_total_amount_denied(self):
        """Test that object without total_amount attribute is denied."""
        request = self.create_mock_request(user=self.regular_user)
        view = self.create_mock_view()
        mock_obj = Mock()
        # No total_amount attribute
        if hasattr(mock_obj, "total_amount"):
            delattr(mock_obj, "total_amount")

        result = self.permission.has_object_permission(request, view, mock_obj)
        self.assertFalse(result)

    def test_user_without_profile_object_permission_denied(self):
        """Test that user without profile is denied object permission."""
        request = self.create_mock_request(user=self.regular_user_no_profile)
        view = self.create_mock_view()
        mock_obj = Mock()
        mock_obj.total_amount = Decimal("100.00")

        result = self.permission.has_object_permission(request, view, mock_obj)
        self.assertFalse(result)


class IsOwnerOrReadOnlyTestCase(BasePermissionTestCase):
    """Test IsOwnerOrReadOnly permission."""

    def setUp(self):
        super().setUp()
        self.permission = IsOwnerOrReadOnly()

    def test_read_methods_allowed(self):
        """Test that read methods are always allowed."""
        for method in ["GET", "HEAD", "OPTIONS"]:
            request = self.create_mock_request(user=self.regular_user, method=method)
            view = self.create_mock_view()
            mock_obj = Mock()
            mock_obj.created_by = self.superuser  # Different user

            result = self.permission.has_object_permission(request, view, mock_obj)
            self.assertTrue(result, f"Method {method} should be allowed")

    def test_owner_write_methods_allowed(self):
        """Test that owner can use write methods."""
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            request = self.create_mock_request(user=self.regular_user, method=method)
            view = self.create_mock_view()
            mock_obj = Mock()
            mock_obj.created_by = self.regular_user  # Same user

            result = self.permission.has_object_permission(request, view, mock_obj)
            self.assertTrue(result, f"Owner should be allowed to {method}")

    def test_non_owner_write_methods_denied(self):
        """Test that non-owner cannot use write methods."""
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            request = self.create_mock_request(user=self.regular_user, method=method)
            view = self.create_mock_view()
            mock_obj = Mock()
            mock_obj.created_by = self.superuser  # Different user

            result = self.permission.has_object_permission(request, view, mock_obj)
            self.assertFalse(result, f"Non-owner should not be allowed to {method}")
