"""
Tests for user-settings, change-password, and system-info endpoints.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from invoice_app.models import AuditLog, UserProfile, UserRole
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def role(db):
    return UserRole.objects.create(
        name="Test Clerk",
        role_type=UserRole.RoleType.CLERK,
        is_active=True,
    )


@pytest.fixture
def user_with_profile(db, role):
    user = User.objects.create_user(username="alice", password="oldpass-123!")
    UserProfile.objects.create(
        user=user,
        role=role,
        language="en",
        timezone="UTC",
        default_currency="EUR",
        default_payment_terms_days=30,
    )
    return user


@pytest.fixture
def user_without_profile(db):
    return User.objects.create_user(username="bob", password="bob-pass-123")


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# /api/user-settings/me/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserSettingsMe:
    def test_get_returns_profile_for_authenticated_user(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.get(reverse("api-user-settings-me"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "alice"
        assert response.data["language"] == "en"
        assert response.data["default_currency"] == "EUR"

    def test_get_unauthenticated_rejected(self):
        response = APIClient().get(reverse("api-user-settings-me"))
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_without_profile_returns_404(self, user_without_profile):
        client = _client(user_without_profile)
        response = client.get(reverse("api-user-settings-me"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_updates_only_provided_fields(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.patch(
            reverse("api-user-settings-me"),
            data={"language": "de", "default_payment_terms_days": 14},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        profile = UserProfile.objects.get(user=user_with_profile)
        assert profile.language == "de"
        assert profile.default_payment_terms_days == 14
        # Untouched fields keep their previous values.
        assert profile.default_currency == "EUR"

    def test_patch_creates_audit_log_entry(self, user_with_profile):
        client = _client(user_with_profile)
        before = AuditLog.objects.filter(action=AuditLog.ActionType.UPDATE).count()
        response = client.patch(
            reverse("api-user-settings-me"),
            data={"language": "de"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        after = AuditLog.objects.filter(action=AuditLog.ActionType.UPDATE).count()
        assert after == before + 1

    def test_readonly_username_email_not_writable(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.patch(
            reverse("api-user-settings-me"),
            data={"username": "hacker", "email": "x@y.z"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user_with_profile.refresh_from_db()
        assert user_with_profile.username == "alice"


# ---------------------------------------------------------------------------
# /api/auth/change-password/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.post(
            reverse("api-auth-change-password"),
            data={"current_password": "oldpass-123!", "new_password": "new-pass-456!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user_with_profile.refresh_from_db()
        assert user_with_profile.check_password("new-pass-456!")

    def test_change_password_wrong_current_rejected(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.post(
            reverse("api-auth-change-password"),
            data={"current_password": "wrong", "new_password": "new-pass-456!"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user_with_profile.refresh_from_db()
        assert user_with_profile.check_password("oldpass-123!")

    def test_change_password_too_short_rejected(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.post(
            reverse("api-auth-change-password"),
            data={"current_password": "oldpass-123!", "new_password": "x"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated_rejected(self):
        response = APIClient().post(
            reverse("api-auth-change-password"),
            data={"current_password": "a", "new_password": "bbbbbbbb"},
            format="json",
        )
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_change_password_resets_must_change_flag(self, user_with_profile):
        profile = UserProfile.objects.get(user=user_with_profile)
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
        client = _client(user_with_profile)
        response = client.post(
            reverse("api-auth-change-password"),
            data={"current_password": "oldpass-123!", "new_password": "new-pass-456!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.must_change_password is False
        assert profile.password_changed_at is not None


# ---------------------------------------------------------------------------
# /api/system/info/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSystemInfo:
    def test_authenticated_returns_metadata(self, user_with_profile):
        client = _client(user_with_profile)
        response = client.get(reverse("api-system-info"))
        assert response.status_code == status.HTTP_200_OK
        assert "app_version" in response.data
        assert "django_version" in response.data
        assert "python_version" in response.data
        assert "debug" in response.data

    def test_unauthenticated_rejected(self):
        response = APIClient().get(reverse("api-system-info"))
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
