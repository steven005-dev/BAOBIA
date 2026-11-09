"""Reusable API permissions for module endpoints.

Other applications should import these permissions instead of duplicating
role, habilitation, or center-access checks in views.
"""

from django.utils import timezone
from django.db import models
from rest_framework.permissions import BasePermission, IsAuthenticated

from .services import user_has_role, user_has_valid_habilitation
from .models import Mandate


class DefaultIsAuthenticated(IsAuthenticated):
    """Explicit alias for the project's default authenticated policy."""


def HasRole(role_code):
    class RolePermission(BasePermission):
        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated) and user_has_role(
                request.user, role_code
            )

    RolePermission.__name__ = f"HasRole_{role_code}"
    return RolePermission


class HasValidHabilitation(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) and user_has_valid_habilitation(
            request.user
        )


class HasCenterAccess(BasePermission):
    """Allow access when the user has an active center membership or mandate."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        center_id = request.parser_context.get("kwargs", {}).get("center_id")
        if not center_id:
            center_id = request.data.get("center_id") or request.query_params.get("center_id")
        if not center_id:
            return False
        from apps.identity.models import CenterMember

        now = timezone.now()
        member = CenterMember.objects.filter(
            center_id=center_id,
            user=request.user,
            starts_at__lte=now,
        ).filter(ends_at__isnull=True) | CenterMember.objects.filter(
            center_id=center_id,
            user=request.user,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        if member.exists():
            return True
        return Mandate.objects.filter(
            agent_user=request.user,
            starts_at__lte=now,
            revoked_at__isnull=True,
        ).filter(
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now),
            mandatecenter__center_id=center_id,
        ).exists()
