"""Fabriques de données de test (simulées) pour accounts et identity."""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Habilitation, Membership, Role, User
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity import services as identity_services

PASSWORD = "Baobia-test-2026"


def make_user(phone, name="Utilisateur test", password=PASSWORD, **extra):
    return User.objects.create_user(phone, password, full_name=name, is_simulated=True, **extra)


def role(code):
    return Role.objects.get_or_create(code=code, defaults={"label_fr": code})[0]


def give_role(user, code, starts_at=None, ends_at=None, **extra):
    starts_at = starts_at or timezone.now() - timedelta(days=1)
    return Membership.objects.create(
        user=user, role=role(code), starts_at=starts_at, ends_at=ends_at, **extra
    )


def make_habilitation(user, *, status="verified", days_from=-10, days_to=30, verifier=None,
                      kind="vet_order", ref=None):
    today = timezone.localdate()
    return Habilitation.objects.create(
        user=user,
        kind=kind,
        reference_number=ref or f"TEST-{status}-{days_from}-{days_to}",
        valid_from=today + timedelta(days=days_from),
        valid_to=today + timedelta(days=days_to),
        status=status,
        verified_by=verifier if status == "verified" else None,
        verified_at=timezone.now() if status == "verified" else None,
        is_simulated=True,
    )


def make_zone(code="TEST-Z"):
    return Zone.objects.get_or_create(code=code, defaults={"level": 0, "name": f"Zone {code}"})[0]


def make_species(code="cattle", mode="animal"):
    return Species.objects.get_or_create(code=code, defaults={"label_fr": code, "tracking_mode": mode})[0]


def make_center(holder, name="Élevage test", zone=None, created_by=None):
    return identity_services.create_center(
        name=name, zone=zone or make_zone(), center_type="farm",
        created_by=created_by or holder, holder=holder, is_simulated=True,
    )
