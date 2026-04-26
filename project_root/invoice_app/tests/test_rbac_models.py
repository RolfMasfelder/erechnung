"""
Test cases for RBAC models (UserRole, UserProfile, SystemConfig).
Tests the role-based access control system and configuration management.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from invoice_app.models import SystemConfig, UserProfile, UserRole


User = get_user_model()


class UserRoleModelTest(TestCase):
    """Test cases for the UserRole model."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            username="admin_user", email="admin@test.com", password="testpass123"
        )

    def test_create_user_role(self):
        """Test creating a basic user role."""
        role = UserRole.objects.create(
            name="Test Role",
            role_type=UserRole.RoleType.CLERK,
            description="A test role for testing",
            can_create_invoice=True,
            can_edit_invoice=True,
            max_invoice_amount=Decimal("5000.00"),
            created_by=self.admin_user,
        )

        self.assertEqual(role.name, "Test Role")
        self.assertEqual(role.role_type, UserRole.RoleType.CLERK)
        self.assertTrue(role.can_create_invoice)
        self.assertTrue(role.can_edit_invoice)
        self.assertFalse(role.can_delete_invoice)  # Default should be False
        self.assertEqual(role.max_invoice_amount, Decimal("5000.00"))
        self.assertEqual(role.created_by, self.admin_user)
        self.assertTrue(role.is_active)
        self.assertFalse(role.is_system_role)

    def test_role_string_representation(self):
        """Test the string representation of a role."""
        role = UserRole.objects.create(name="Manager Role", role_type=UserRole.RoleType.MANAGER)
        self.assertEqual(str(role), "Manager Role")

    def test_has_permission_method(self):
        """Test the has_permission method."""
        role = UserRole.objects.create(
            name="Test Role", role_type=UserRole.RoleType.ACCOUNTANT, can_create_invoice=True, can_delete_invoice=False
        )

        self.assertTrue(role.has_permission("can_create_invoice"))
        self.assertFalse(role.has_permission("can_delete_invoice"))
        self.assertFalse(role.has_permission("nonexistent_permission"))

    def test_can_approve_invoice_amount_method(self):
        """Test the can_approve_invoice_amount method."""
        # Role with limit
        limited_role = UserRole.objects.create(
            name="Limited Role", role_type=UserRole.RoleType.CLERK, max_invoice_amount=Decimal("1000.00")
        )

        # Role without limit
        unlimited_role = UserRole.objects.create(
            name="Unlimited Role", role_type=UserRole.RoleType.ADMIN, max_invoice_amount=None
        )

        # Test limited role
        self.assertTrue(limited_role.can_approve_invoice_amount(Decimal("500.00")))
        self.assertTrue(limited_role.can_approve_invoice_amount(Decimal("1000.00")))
        self.assertFalse(limited_role.can_approve_invoice_amount(Decimal("1500.00")))

        # Test unlimited role
        self.assertTrue(unlimited_role.can_approve_invoice_amount(Decimal("1000000.00")))

    def test_create_system_roles_method(self):
        """Test the create_system_roles class method."""
        # Initially no roles
        self.assertEqual(UserRole.objects.count(), 0)

        # Create system roles
        created_roles = UserRole.create_system_roles()

        # Should create 6 predefined roles
        self.assertEqual(UserRole.objects.count(), 6)
        self.assertEqual(len(created_roles), 6)

        # Check specific roles exist
        admin_role = UserRole.objects.get(role_type=UserRole.RoleType.ADMIN)
        self.assertEqual(admin_role.name, "Administrator")
        self.assertTrue(admin_role.is_system_role)
        self.assertTrue(admin_role.can_manage_users)
        self.assertTrue(admin_role.can_delete_invoice)

        clerk_role = UserRole.objects.get(role_type=UserRole.RoleType.CLERK)
        self.assertEqual(clerk_role.name, "Clerk")
        self.assertTrue(clerk_role.is_system_role)
        self.assertFalse(clerk_role.can_manage_users)
        self.assertFalse(clerk_role.can_delete_invoice)
        self.assertEqual(clerk_role.max_invoice_amount, Decimal("10000.00"))

        read_only_role = UserRole.objects.get(role_type=UserRole.RoleType.READ_ONLY)
        self.assertEqual(read_only_role.name, "Read Only")
        self.assertFalse(read_only_role.can_create_invoice)
        self.assertFalse(read_only_role.can_edit_invoice)
        self.assertTrue(read_only_role.can_view_reports)

    def test_create_system_roles_idempotent(self):
        """Test that create_system_roles is idempotent."""
        # Create roles first time
        first_creation = UserRole.create_system_roles()
        self.assertEqual(len(first_creation), 6)

        # Create roles second time
        second_creation = UserRole.create_system_roles()
        self.assertEqual(len(second_creation), 0)  # No new roles created

        # Still only 6 roles total
        self.assertEqual(UserRole.objects.count(), 6)

    def test_role_permissions_consistency(self):
        """Test that role permissions are logically consistent."""
        UserRole.create_system_roles()

        # Admin should have all permissions
        admin = UserRole.objects.get(role_type=UserRole.RoleType.ADMIN)
        self.assertTrue(admin.can_create_invoice)
        self.assertTrue(admin.can_edit_invoice)
        self.assertTrue(admin.can_delete_invoice)
        self.assertTrue(admin.can_manage_users)
        self.assertTrue(admin.can_manage_roles)

        # Auditor should have read permissions but no write permissions
        auditor = UserRole.objects.get(role_type=UserRole.RoleType.AUDITOR)
        self.assertFalse(auditor.can_create_invoice)
        self.assertFalse(auditor.can_edit_invoice)
        self.assertFalse(auditor.can_delete_invoice)
        self.assertTrue(auditor.can_view_reports)
        self.assertTrue(auditor.can_view_audit_logs)


class UserProfileModelTest(TestCase):
    """Test cases for the UserProfile model."""

    def setUp(self):
        """Set up test data."""
        UserRole.create_system_roles()
        self.clerk_role = UserRole.objects.get(role_type=UserRole.RoleType.CLERK)
        self.admin_role = UserRole.objects.get(role_type=UserRole.RoleType.ADMIN)

        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_create_user_profile(self):
        """Test creating a user profile."""
        profile = UserProfile.objects.create(
            user=self.user,
            role=self.clerk_role,
            employee_id="EMP001",
            department="Accounting",
            phone="+1234567890",
            language="de",
            timezone="Europe/Berlin",
        )

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.role, self.clerk_role)
        self.assertEqual(profile.employee_id, "EMP001")
        self.assertEqual(profile.department, "Accounting")
        self.assertEqual(profile.language, "de")
        self.assertEqual(profile.timezone, "Europe/Berlin")
        self.assertEqual(profile.failed_login_attempts, 0)
        self.assertFalse(profile.mfa_enabled)
        self.assertEqual(profile.concurrent_sessions_limit, 3)

    def test_profile_string_representation(self):
        """Test the string representation of a profile."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)
        expected = f"{self.user.username} - {self.clerk_role.name}"
        self.assertEqual(str(profile), expected)

    def test_account_locking_functionality(self):
        """Test account locking and unlocking."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)

        # Initially not locked
        self.assertFalse(profile.is_account_locked)

        # Lock account
        profile.lock_account(duration_minutes=30)
        self.assertTrue(profile.is_account_locked)
        self.assertIsNotNone(profile.account_locked_until)

        # Unlock account
        profile.unlock_account()
        self.assertFalse(profile.is_account_locked)
        self.assertIsNone(profile.account_locked_until)
        self.assertEqual(profile.failed_login_attempts, 0)

    def test_failed_login_tracking(self):
        """Test failed login attempt tracking and auto-locking."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)

        # Record failed attempts
        for i in range(4):
            profile.record_failed_login()
            self.assertEqual(profile.failed_login_attempts, i + 1)
            self.assertFalse(profile.is_account_locked)

        # 5th attempt should trigger auto-lock
        profile.record_failed_login()
        self.assertEqual(profile.failed_login_attempts, 5)
        self.assertTrue(profile.is_account_locked)

    def test_successful_login_resets_failed_attempts(self):
        """Test that successful login resets failed attempts."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)

        # Record some failed attempts
        profile.record_failed_login()
        profile.record_failed_login()
        self.assertEqual(profile.failed_login_attempts, 2)

        # Successful login should reset
        profile.record_successful_login(ip_address="192.168.1.1")
        self.assertEqual(profile.failed_login_attempts, 0)
        self.assertEqual(profile.last_login_ip, "192.168.1.1")

    def test_permission_delegation_to_role(self):
        """Test that profile delegates permissions to role."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)

        # Test permission delegation
        self.assertTrue(profile.has_permission("can_create_invoice"))
        self.assertFalse(profile.has_permission("can_delete_invoice"))

        # Test invoice amount approval delegation
        self.assertTrue(profile.can_approve_invoice_amount(Decimal("5000.00")))
        self.assertFalse(profile.can_approve_invoice_amount(Decimal("15000.00")))

    def test_account_expiry_check(self):
        """Test account expiry functionality."""
        profile = UserProfile.objects.create(user=self.user, role=self.clerk_role)

        # Set account to expire in the past
        past_time = timezone.now() - timedelta(hours=1)
        profile.account_locked_until = past_time
        profile.save()

        # Should not be locked (expired lock)
        self.assertFalse(profile.is_account_locked)

        # Set account to expire in the future
        future_time = timezone.now() + timedelta(hours=1)
        profile.account_locked_until = future_time
        profile.save()

        # Should be locked
        self.assertTrue(profile.is_account_locked)


class SystemConfigModelTest(TestCase):
    """Test cases for the SystemConfig model."""

    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(username="admin", email="admin@test.com", password="testpass123")

    def test_create_system_config(self):
        """Test creating a system configuration."""
        config = SystemConfig.objects.create(
            key="test_setting",
            category=SystemConfig.ConfigCategory.GENERAL,
            name="Test Setting",
            description="A test configuration setting",
            value="test_value",
            value_type=SystemConfig.ConfigType.STRING,
            updated_by=self.admin_user,
        )

        self.assertEqual(config.key, "test_setting")
        self.assertEqual(config.category, SystemConfig.ConfigCategory.GENERAL)
        self.assertEqual(config.name, "Test Setting")
        self.assertEqual(config.value, "test_value")
        self.assertEqual(config.value_type, SystemConfig.ConfigType.STRING)
        self.assertEqual(config.updated_by, self.admin_user)
        self.assertTrue(config.is_required)
        self.assertFalse(config.is_sensitive)
        self.assertFalse(config.is_system)

    def test_config_string_representation(self):
        """Test the string representation of a config."""
        config = SystemConfig.objects.create(
            key="test_key", category=SystemConfig.ConfigCategory.SECURITY, name="Test Config"
        )
        expected = f"{config.category}: {config.name}"
        self.assertEqual(str(config), expected)

    def test_typed_value_methods(self):
        """Test get_value and set_value methods for different types."""
        # String value
        string_config = SystemConfig.objects.create(
            key="string_test",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="hello world",
            value_type=SystemConfig.ConfigType.STRING,
        )
        self.assertEqual(string_config.get_value(), "hello world")

        # Integer value
        int_config = SystemConfig.objects.create(
            key="int_test",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="42",
            value_type=SystemConfig.ConfigType.INTEGER,
        )
        self.assertEqual(int_config.get_value(), 42)
        self.assertIsInstance(int_config.get_value(), int)

        # Float value
        float_config = SystemConfig.objects.create(
            key="float_test",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="3.14",
            value_type=SystemConfig.ConfigType.FLOAT,
        )
        self.assertEqual(float_config.get_value(), 3.14)
        self.assertIsInstance(float_config.get_value(), float)

        # Boolean values
        bool_config = SystemConfig.objects.create(
            key="bool_test",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="true",
            value_type=SystemConfig.ConfigType.BOOLEAN,
        )
        self.assertTrue(bool_config.get_value())

        # Test different boolean representations
        bool_config.value = "false"
        self.assertFalse(bool_config.get_value())

        bool_config.value = "1"
        self.assertTrue(bool_config.get_value())

        bool_config.value = "0"
        self.assertFalse(bool_config.get_value())

        # JSON value
        json_config = SystemConfig.objects.create(
            key="json_test",
            category=SystemConfig.ConfigCategory.GENERAL,
            value='{"key": "value", "number": 123}',
            value_type=SystemConfig.ConfigType.JSON,
        )
        expected_json = {"key": "value", "number": 123}
        self.assertEqual(json_config.get_value(), expected_json)

    def test_set_value_type_conversion(self):
        """Test set_value method with type conversion."""
        config = SystemConfig.objects.create(
            key="test_config", category=SystemConfig.ConfigCategory.GENERAL, value_type=SystemConfig.ConfigType.BOOLEAN
        )

        # Set boolean value
        config.set_value(True)
        self.assertEqual(config.value, "true")

        config.set_value(False)
        self.assertEqual(config.value, "false")

        # Change to JSON type
        config.value_type = SystemConfig.ConfigType.JSON
        test_dict = {"test": "data", "numbers": [1, 2, 3]}
        config.set_value(test_dict)
        self.assertEqual(config.value, json.dumps(test_dict))

    def test_get_config_class_method(self):
        """Test the get_config class method."""
        # Create a config
        SystemConfig.objects.create(
            key="test_key",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="test_value",
            value_type=SystemConfig.ConfigType.STRING,
        )

        # Test getting existing config
        value = SystemConfig.get_config("test_key")
        self.assertEqual(value, "test_value")

        # Test getting non-existent config with default
        value = SystemConfig.get_config("nonexistent", "default_value")
        self.assertEqual(value, "default_value")

        # Test getting non-existent config without default
        value = SystemConfig.get_config("nonexistent")
        self.assertIsNone(value)

    def test_set_config_class_method(self):
        """Test the set_config class method."""
        # Create a config
        config = SystemConfig.objects.create(
            key="test_key",
            category=SystemConfig.ConfigCategory.GENERAL,
            value="original_value",
            value_type=SystemConfig.ConfigType.STRING,
        )

        # Verify the config was created correctly
        self.assertEqual(config.value, "original_value")

        # Update the config
        updated_config = SystemConfig.set_config("test_key", "new_value", self.admin_user)
        self.assertEqual(updated_config.value, "new_value")
        self.assertEqual(updated_config.updated_by, self.admin_user)

        # Test setting non-existent config (should raise error)
        with self.assertRaises(ValueError) as context:
            SystemConfig.set_config("nonexistent", "value")

        self.assertIn("does not exist", str(context.exception))

    def test_create_default_configs(self):
        """Test the create_default_configs class method."""
        # Initially no configs
        self.assertEqual(SystemConfig.objects.count(), 0)

        # Create default configs
        created_configs = SystemConfig.create_default_configs()

        # Should create multiple default configs
        self.assertGreater(len(created_configs), 0)
        self.assertEqual(SystemConfig.objects.count(), len(created_configs))

        # Check some specific configs
        company_name = SystemConfig.objects.get(key="company_name")
        self.assertEqual(company_name.category, SystemConfig.ConfigCategory.GENERAL)
        self.assertEqual(company_name.value_type, SystemConfig.ConfigType.STRING)
        self.assertTrue(company_name.is_system)

        session_timeout = SystemConfig.objects.get(key="session_timeout_minutes")
        self.assertEqual(session_timeout.category, SystemConfig.ConfigCategory.SECURITY)
        self.assertEqual(session_timeout.value_type, SystemConfig.ConfigType.INTEGER)

        # Test idempotency
        second_creation = SystemConfig.create_default_configs()
        self.assertEqual(len(second_creation), 0)  # No new configs created


class RBACIntegrationTest(TestCase):
    """Integration tests for the RBAC system."""

    def setUp(self):
        """Set up test data for integration tests."""
        # Create system roles and configs
        UserRole.create_system_roles()
        SystemConfig.create_default_configs()

        # Create test users
        self.admin_user = User.objects.create_user(username="admin", email="admin@test.com", password="adminpass123")

        self.clerk_user = User.objects.create_user(username="clerk", email="clerk@test.com", password="clerkpass123")

        # Create profiles with different roles
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user, role=UserRole.objects.get(role_type=UserRole.RoleType.ADMIN), employee_id="ADMIN001"
        )

        self.clerk_profile = UserProfile.objects.create(
            user=self.clerk_user, role=UserRole.objects.get(role_type=UserRole.RoleType.CLERK), employee_id="CLERK001"
        )

    def test_permission_hierarchy(self):
        """Test that permission hierarchy works correctly."""
        # Admin should have all permissions
        self.assertTrue(self.admin_profile.has_permission("can_create_invoice"))
        self.assertTrue(self.admin_profile.has_permission("can_delete_invoice"))
        self.assertTrue(self.admin_profile.has_permission("can_manage_users"))
        self.assertTrue(self.admin_profile.has_permission("can_view_audit_logs"))

        # Clerk should have limited permissions
        self.assertTrue(self.clerk_profile.has_permission("can_create_invoice"))
        self.assertFalse(self.clerk_profile.has_permission("can_delete_invoice"))
        self.assertFalse(self.clerk_profile.has_permission("can_manage_users"))
        self.assertFalse(self.clerk_profile.has_permission("can_view_audit_logs"))

    def test_financial_limits_integration(self):
        """Test financial limits across the system."""
        # Admin should have no limits
        self.assertTrue(self.admin_profile.can_approve_invoice_amount(Decimal("1000000.00")))

        # Clerk should have the default limit
        self.assertTrue(self.clerk_profile.can_approve_invoice_amount(Decimal("5000.00")))
        self.assertFalse(self.clerk_profile.can_approve_invoice_amount(Decimal("15000.00")))

    def test_config_system_integration(self):
        """Test that config system integrates properly."""
        # Test getting a security config
        timeout = SystemConfig.get_config("session_timeout_minutes")
        self.assertEqual(timeout, 480)  # Default value

        # Test updating config
        SystemConfig.set_config("session_timeout_minutes", 300, self.admin_user)
        updated_timeout = SystemConfig.get_config("session_timeout_minutes")
        self.assertEqual(updated_timeout, 300)

        # Verify the update was tracked
        config = SystemConfig.objects.get(key="session_timeout_minutes")
        self.assertEqual(config.updated_by, self.admin_user)

    def test_account_security_workflow(self):
        """Test complete account security workflow."""
        # Simulate multiple failed logins
        for _ in range(3):
            self.clerk_profile.record_failed_login()

        self.assertEqual(self.clerk_profile.failed_login_attempts, 3)
        self.assertFalse(self.clerk_profile.is_account_locked)

        # Two more failed attempts should lock the account
        self.clerk_profile.record_failed_login()
        self.clerk_profile.record_failed_login()

        self.assertTrue(self.clerk_profile.is_account_locked)

        # Successful login should unlock and reset
        self.clerk_profile.record_successful_login("192.168.1.100")
        self.assertEqual(self.clerk_profile.failed_login_attempts, 0)
        self.assertEqual(self.clerk_profile.last_login_ip, "192.168.1.100")
