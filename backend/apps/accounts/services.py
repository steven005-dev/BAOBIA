from django.utils import timezone
from django.db.models import Q

from .models import Habilitation, Membership, Role


def active_roles(user, at=None):
    at = at or timezone.now()
    memberships = Membership.objects.filter(
        Q(user=user),
        starts_at__lte=at,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
    return list(Role.objects.filter(membership__in=memberships).distinct())


def user_has_role(user, role_code, at=None):
    return any(role.code == role_code for role in active_roles(user, at))


def user_has_valid_habilitation(user, at=None):
    at = (at or timezone.now()).date()
    return Habilitation.objects.filter(
        user=user,
        kind="vet_order",
        status="verified",
        valid_from__lte=at,
        valid_to__gte=at,
    ).exists()
