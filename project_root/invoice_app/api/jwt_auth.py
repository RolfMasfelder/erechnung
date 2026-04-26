"""
Custom JWT authentication integration with RBAC system.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from invoice_app.models import AuditLog, UserProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that includes RBAC information in tokens.
    """

    @classmethod
    def get_token(cls, user):
        """Generate JWT token with custom RBAC claims."""
        token = super().get_token(user)

        # Add basic user information
        token["username"] = user.username
        token["email"] = user.email
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser

        # Add RBAC information if user has a profile
        try:
            user_profile = getattr(user, "profile", None)
            if user_profile:
                token["profile_id"] = user_profile.id
                token["employee_id"] = user_profile.employee_id
                token["department"] = user_profile.department
                token["is_mfa_enabled"] = user_profile.mfa_enabled
                token["account_locked"] = user_profile.is_account_locked

                # Add role information
                if user_profile.role:
                    role = user_profile.role
                    token["role"] = {
                        "id": role.id,
                        "name": role.name,
                        "role_type": role.role_type,
                        "description": role.description,
                        "max_invoice_amount": str(role.max_invoice_amount) if role.max_invoice_amount else None,
                        "permissions": {
                            # Invoice permissions
                            "can_create_invoice": role.can_create_invoice,
                            "can_edit_invoice": role.can_edit_invoice,
                            "can_delete_invoice": role.can_delete_invoice,
                            "can_send_invoice": role.can_send_invoice,
                            "can_mark_paid": role.can_mark_paid,
                            "can_generate_pdf": role.can_generate_pdf,
                            # Customer permissions
                            "can_create_customer": role.can_create_customer,
                            "can_edit_customer": role.can_edit_customer,
                            "can_delete_customer": role.can_delete_customer,
                            # Product permissions
                            "can_create_product": role.can_create_product,
                            "can_edit_product": role.can_edit_product,
                            "can_delete_product": role.can_delete_product,
                            "can_manage_inventory": role.can_manage_inventory,
                            # Company permissions
                            "can_edit_company": role.can_edit_company,
                            # Reporting and audit permissions
                            "can_view_reports": role.can_view_reports,
                            "can_export_data": role.can_export_data,
                            "can_view_audit_logs": role.can_view_audit_logs,
                            "can_backup_data": role.can_backup_data,
                            # System administration permissions
                            "can_manage_users": role.can_manage_users,
                            "can_manage_roles": role.can_manage_roles,
                            "can_change_settings": role.can_change_settings,
                        },
                    }
                else:
                    token["role"] = None
            else:
                token["profile_id"] = None
                token["role"] = None
        except (UserProfile.DoesNotExist, AttributeError):
            token["profile_id"] = None
            token["role"] = None

        return token

    def validate(self, attrs):
        """Custom validation with audit logging."""
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(request=self.context.get("request"), username=username, password=password)

            if not user:
                # Check if user exists but is inactive
                try:
                    from django.contrib.auth import get_user_model

                    user_model = get_user_model()
                    user_exists = user_model.objects.get(username=username)
                    if not user_exists.is_active:
                        # Log inactive user login attempt
                        AuditLog.objects.create(
                            action=AuditLog.ActionType.LOGIN,
                            severity=AuditLog.Severity.HIGH,
                            username=username,
                            description=f"Login attempt by inactive user: {username}",
                            ip_address=self._get_client_ip(),
                            is_security_event=True,
                        )
                        raise serializers.ValidationError("User account is disabled")
                except user_model.DoesNotExist:
                    pass

                # Log failed login attempt
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN,
                    severity=AuditLog.Severity.MEDIUM,
                    username=username,
                    description=f"Failed login attempt for user: {username}",
                    ip_address=self._get_client_ip(),
                    is_security_event=True,
                )
                raise serializers.ValidationError("Invalid credentials")

            if not user.is_active:
                # Log inactive user login attempt (fallback case)
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN,
                    severity=AuditLog.Severity.HIGH,
                    username=username,
                    description=f"Login attempt by inactive user: {username}",
                    ip_address=self._get_client_ip(),
                    is_security_event=True,
                )
                raise serializers.ValidationError("User account is disabled")

            # Check if account is locked (if UserProfile exists)
            try:
                user_profile = UserProfile.objects.get(user=user)
                if user_profile.is_account_locked:
                    AuditLog.objects.create(
                        action=AuditLog.ActionType.LOGIN,
                        severity=AuditLog.Severity.HIGH,
                        username=username,
                        description=f"Login attempt by locked account: {username}",
                        ip_address=self._get_client_ip(),
                        is_security_event=True,
                    )
                    raise serializers.ValidationError("Account is locked")
            except UserProfile.DoesNotExist:
                pass  # No UserProfile, continue with login

        # Proceed with normal validation
        data = super().validate(attrs)

        # Log successful login
        AuditLog.objects.create(
            action=AuditLog.ActionType.LOGIN,
            severity=AuditLog.Severity.LOW,
            username=username,
            description=f"Successful login for user: {username}",
            ip_address=self._get_client_ip(),
            is_security_event=True,
        )

        return data

    def _get_client_ip(self):
        """Extract client IP address from request."""
        request = self.context.get("request")
        if not request:
            return "0.0.0.0"

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
        return ip


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token view that uses our RBAC-enhanced serializer.
    """

    serializer_class = CustomTokenObtainPairSerializer
