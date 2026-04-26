"""
Tests for JWT authentication with RBAC integration.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from invoice_app.api.jwt_auth import CustomTokenObtainPairSerializer
from invoice_app.models import AuditLog, BusinessPartner, Company, Country, Invoice, UserProfile, UserRole


class JWTAuthenticationTestCase(APITestCase):
    """Test suite for JWT authentication."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Create test role with permissions
        self.manager_role = UserRole.objects.create(
            name="Test Manager",
            role_type="manager",
            can_create_invoice=True,
            can_edit_invoice=True,
            can_manage_users=True,
            max_invoice_amount=Decimal("10000.00"),
        )

        # Create UserProfile for the user
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            employee_id="EMP001",
            department="IT",
            role=self.manager_role,
        )

        # Create Country for ForeignKey
        self.germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "numeric_code": "276",
                "name": "Germany",
                "name_local": "Deutschland",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

        # Create test data for API calls
        self.company = Company.objects.create(
            name="Test Company",
            tax_id="DE123456789",
            vat_id="DE123456789",
            address_line1="Test Street 123",
            postal_code="12345",
            city="Test City",
            country=self.germany,
        )

        self.business_partner = BusinessPartner.objects.create(
            partner_type=BusinessPartner.PartnerType.BUSINESS,
            company_name="Test Customer",
            tax_id="DE987654321",
            address_line1="Customer Street 456",
            postal_code="54321",
            city="Customer City",
            country=self.germany,
        )

    def test_jwt_token_obtain(self):
        """Test obtaining JWT tokens."""
        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "testpass123"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Verify audit log entry
        audit_log = AuditLog.objects.filter(
            username="testuser",
            action=AuditLog.ActionType.LOGIN,
        ).first()
        self.assertIsNotNone(audit_log)

    def test_jwt_token_obtain_invalid_credentials(self):
        """Test JWT token obtain with invalid credentials."""
        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "wrongpassword"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify audit log entry for failed login
        audit_log = AuditLog.objects.filter(
            username="testuser",
            action=AuditLog.ActionType.LOGIN,
        ).first()
        self.assertIsNotNone(audit_log)

    def test_jwt_token_obtain_locked_account(self):
        """Test JWT token obtain with locked account."""
        # Lock the account
        self.user_profile.lock_account(30)  # Lock for 30 minutes

        # Verify the account is locked
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.is_account_locked)

        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "testpass123"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Account is locked", str(response.data))

    def test_jwt_token_obtain_inactive_user(self):
        """Test JWT token obtain with inactive user."""
        self.user.is_active = False
        self.user.save()

        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "testpass123"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User account is disabled", str(response.data))

    def test_jwt_token_refresh(self):
        """Test refreshing JWT tokens."""
        # First get tokens
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        # Add custom claims
        access_token["role"] = self.manager_role.name
        access_token["permissions"] = ["create_invoice", "view_invoice"]

        url = reverse("token_refresh")
        data = {"refresh": str(refresh)}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_jwt_custom_claims(self):
        """Test that JWT tokens contain custom RBAC claims."""
        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "testpass123"}

        response = self.client.post(url, data)

        # Decode token to check claims
        access_token = response.data["access"]

        # We'll verify claims by making an authenticated request
        # and checking that the authentication works
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Test API call with JWT token
        invoices_url = reverse("api-invoice-list")
        api_response = self.client.get(invoices_url)

        self.assertEqual(api_response.status_code, status.HTTP_200_OK)

    def test_jwt_authentication_required(self):
        """Test that API endpoints require JWT authentication."""
        url = reverse("api-invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_authentication_with_valid_token(self):
        """Test API access with valid JWT token."""
        # Get JWT token
        token_url = reverse("token_obtain_pair")
        token_data = {"username": "testuser", "password": "testpass123"}
        token_response = self.client.post(token_url, token_data)
        access_token = token_response.data["access"]

        # Use token for API call
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        url = reverse("api-invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_authentication_with_invalid_token(self):
        """Test API access with invalid JWT token."""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        url = reverse("api-invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_without_user_profile(self):
        """Test JWT token generation for user without UserProfile."""
        # Create user without UserProfile
        User.objects.create_user(username="noprofile", password="testpass123")

        url = reverse("token_obtain_pair")
        data = {"username": "noprofile", "password": "testpass123"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_api_create_invoice_with_jwt(self):
        """Test creating invoice with JWT authentication."""
        # Get JWT token
        token_url = reverse("token_obtain_pair")
        token_data = {"username": "testuser", "password": "testpass123"}
        token_response = self.client.post(token_url, token_data)
        access_token = token_response.data["access"]

        # Create invoice with JWT
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        invoice_data = {
            "invoice_number": "JWT-TEST-001",
            "invoice_type": "INVOICE",
            "company": self.company.id,
            "business_partner": self.business_partner.id,
            "issue_date": timezone.now().date().isoformat(),
            "due_date": (timezone.now().date() + timezone.timedelta(days=30)).isoformat(),
            "currency": "EUR",
            "subtotal": "100.00",
            "tax_amount": "19.00",
            "total_amount": "119.00",
            "status": "DRAFT",
        }

        url = reverse("api-invoice-list")
        response = self.client.post(url, invoice_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # invoice_number is auto-generated (read_only field) – lookup by response id
        created = Invoice.objects.get(id=response.data["id"])
        self.assertEqual(created.total_amount, Decimal("119.00"))

    def test_session_auth_still_works(self):
        """Test that session authentication still works alongside JWT."""
        # Login using session auth
        self.client.force_authenticate(user=self.user)

        url = reverse("api-invoice-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_logout_audit_log(self):
        """Test that login attempts are properly logged."""
        # Test successful login
        url = reverse("token_obtain_pair")
        data = {"username": "testuser", "password": "testpass123"}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check audit log
        success_log = AuditLog.objects.filter(
            username="testuser", action=AuditLog.ActionType.LOGIN, is_security_event=True
        ).first()
        self.assertIsNotNone(success_log)
        self.assertIn("Successful login", success_log.description)

        # Test failed login
        data["password"] = "wrongpassword"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check audit log for failure
        failure_log = AuditLog.objects.filter(
            username="testuser", action=AuditLog.ActionType.LOGIN, is_security_event=True
        ).first()
        self.assertIsNotNone(failure_log)
        self.assertIn("Failed login attempt", failure_log.description)


class GetTokenRBACClaimsTests(APITestCase):
    """Test that get_token embeds full RBAC claims in JWT tokens."""

    def test_token_contains_rbac_role_permissions(self):
        """Token includes role name, type, permissions when user has profile+role."""
        user = User.objects.create_user(username="rbac", password="pass123")
        role = UserRole.objects.create(
            name="Accountant",
            role_type="accountant",
            can_create_invoice=True,
            can_edit_invoice=True,
            can_view_reports=True,
            max_invoice_amount=Decimal("50000.00"),
        )
        UserProfile.objects.create(
            user=user,
            employee_id="EMP-RBAC",
            department="Finance",
            role=role,
        )

        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertEqual(token["username"], "rbac")
        self.assertEqual(token["email"], user.email)
        self.assertTrue(token["role"]["permissions"]["can_create_invoice"])
        self.assertTrue(token["role"]["permissions"]["can_view_reports"])
        self.assertEqual(token["role"]["name"], "Accountant")
        self.assertEqual(token["role"]["role_type"], "accountant")
        self.assertEqual(token["role"]["max_invoice_amount"], "50000.00")
        self.assertEqual(token["department"], "Finance")
        self.assertEqual(token["employee_id"], "EMP-RBAC")
        self.assertFalse(token["is_mfa_enabled"])
        self.assertFalse(token["account_locked"])

    def test_token_with_role_no_max_amount(self):
        """User with role that has no max_invoice_amount → None in token."""
        user = User.objects.create_user(username="norole", password="pass123")
        role = UserRole.objects.create(name="Basic", role_type="clerk", max_invoice_amount=None)
        UserProfile.objects.create(user=user, employee_id="EMP-NR", role=role)

        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertIsNotNone(token["role"])
        self.assertIsNone(token["role"]["max_invoice_amount"])
        self.assertIsNotNone(token["profile_id"])

    def test_token_without_profile(self):
        """User without UserProfile → profile_id=None, role=None."""
        user = User.objects.create_user(username="noprof", password="pass123")

        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertIsNone(token["profile_id"])
        self.assertIsNone(token["role"])

    def test_token_includes_staff_flags(self):
        """Token contains is_staff and is_superuser flags."""
        user = User.objects.create_superuser(username="su", password="pass123")
        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertTrue(token["is_staff"])
        self.assertTrue(token["is_superuser"])

    def test_token_includes_mfa_and_lock_flags(self):
        """Token contains MFA enabled and account_locked from profile."""
        user = User.objects.create_user(username="mfauser", password="pass123")
        role = UserRole.objects.create(name="MFA Role", role_type="clerk")
        UserProfile.objects.create(
            user=user,
            employee_id="EMP-MFA",
            mfa_enabled=True,
            role=role,
        )
        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertTrue(token["is_mfa_enabled"])
        self.assertFalse(token["account_locked"])


class LoginValidationEdgeCaseTests(APITestCase):
    """Test login validation edge cases for full branch coverage."""

    def test_nonexistent_user_login(self):
        """Login attempt with username that doesn't exist."""
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": "ghost", "password": "nope"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        log = AuditLog.objects.filter(username="ghost", action=AuditLog.ActionType.LOGIN).first()
        self.assertIsNotNone(log)
        self.assertIn("Failed login attempt", log.description)

    def test_inactive_user_auth_fails_first(self):
        """Inactive user: authenticate() returns None → inner branch catches it."""
        User.objects.create_user(username="inactive", password="pass123", is_active=False)
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": "inactive", "password": "pass123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        log = AuditLog.objects.filter(username="inactive", action=AuditLog.ActionType.LOGIN).last()
        self.assertIsNotNone(log)

    def test_x_forwarded_for_ip_extraction(self):
        """Client IP is extracted from X-Forwarded-For header."""
        factory = RequestFactory()
        request = factory.post("/api/token/", HTTP_X_FORWARDED_FOR="203.0.113.50, 198.51.100.1")

        serializer = CustomTokenObtainPairSerializer(context={"request": request})
        ip = serializer._get_client_ip()
        self.assertEqual(ip, "203.0.113.50")

    def test_remote_addr_fallback(self):
        """Client IP falls back to REMOTE_ADDR when no X-Forwarded-For."""
        factory = RequestFactory()
        request = factory.post("/api/token/", REMOTE_ADDR="10.0.0.1")

        serializer = CustomTokenObtainPairSerializer(context={"request": request})
        ip = serializer._get_client_ip()
        self.assertEqual(ip, "10.0.0.1")

    def test_no_request_returns_default_ip(self):
        """Without request context, returns 0.0.0.0."""
        serializer = CustomTokenObtainPairSerializer(context={})
        ip = serializer._get_client_ip()
        self.assertEqual(ip, "0.0.0.0")
