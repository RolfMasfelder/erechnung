"""
User settings, password change, and system info API views.
"""

from __future__ import annotations

import platform

import django
from django.conf import settings as django_settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from invoice_app.models import AuditLog, UserProfile


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


class UserSettingsSerializer(serializers.ModelSerializer):
    """User-editable preferences. Excludes security fields (mfa, lock, etc.)."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "username",
            "email",
            "language",
            "timezone",
            "date_format",
            "email_notifications",
            "notify_invoice_paid",
            "notify_invoice_overdue",
            "default_currency",
            "default_payment_terms_days",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class UserSettingsMeView(APIView):
    """
    GET/PUT/PATCH /api/user-settings/me/

    Returns and updates the authenticated user's preferences (UserProfile).
    """

    permission_classes = [IsAuthenticated]

    def _get_profile(self, user) -> UserProfile | None:
        return UserProfile.objects.filter(user=user).select_related("user").first()

    @extend_schema(
        description="Get the authenticated user's preferences.",
        responses={
            200: UserSettingsSerializer,
            404: OpenApiResponse(description="No profile assigned to this user"),
        },
    )
    def get(self, request):
        profile = self._get_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No profile assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserSettingsSerializer(profile).data)

    @extend_schema(
        description="Replace all preference fields of the authenticated user.",
        request=UserSettingsSerializer,
        responses={200: UserSettingsSerializer},
    )
    def put(self, request):
        return self._update(request, partial=False)

    @extend_schema(
        description="Update individual preference fields of the authenticated user.",
        request=UserSettingsSerializer,
        responses={200: UserSettingsSerializer},
    )
    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, *, partial: bool) -> Response:
        profile = self._get_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "No profile assigned to this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserSettingsSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        AuditLog.log_action(
            action=AuditLog.ActionType.UPDATE,
            user=request.user,
            request=request,
            description="User settings updated",
            details={"fields": list(serializer.validated_data.keys())},
            severity=AuditLog.Severity.LOW,
        )
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/

    Allows the authenticated user to change their own password.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Change the authenticated user's password.",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed"),
            400: OpenApiResponse(description="Invalid current password or weak new password"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Reset must_change_password / update password_changed_at if profile exists.
        profile = UserProfile.objects.filter(user=user).first()
        if profile is not None:
            from django.utils import timezone as dj_timezone

            profile.password_changed_at = dj_timezone.now()
            profile.must_change_password = False
            profile.save(update_fields=["password_changed_at", "must_change_password"])

        AuditLog.log_action(
            action=AuditLog.ActionType.UPDATE,
            user=user,
            request=request,
            description="Password changed by user",
            severity=AuditLog.Severity.MEDIUM,
        )
        return Response({"detail": "Password changed."}, status=status.HTTP_200_OK)


class SystemInfoView(APIView):
    """
    GET /api/system/info/

    Public, low-detail metadata about the running backend.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Return non-sensitive system info (version, runtime).",
        responses={200: OpenApiResponse(description="System info object")},
    )
    def get(self, request):
        try:
            from importlib.metadata import version as _pkg_version

            app_version = _pkg_version("erechnung")
        except Exception:
            app_version = getattr(django_settings, "APP_VERSION", "unknown")

        return Response(
            {
                "app_version": app_version,
                "django_version": django.get_version(),
                "python_version": platform.python_version(),
                "debug": bool(django_settings.DEBUG),
            },
            status=status.HTTP_200_OK,
        )
