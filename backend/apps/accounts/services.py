"""Fonctions publiques du module accounts.

Les autres modules lisent les rôles et les habilitations UNIQUEMENT par ces
fonctions (jamais de requête directe sur membership / habilitation).

Fonctions de lecture :
- active_roles(user, at=None) -> list[Role]
- active_memberships(user, at=None) -> QuerySet[Membership]
- user_has_role(user, role_code, at=None) -> bool
- get_valid_habilitation(user, at=None, kinds=...) -> Habilitation | None
- user_has_valid_habilitation(user, at=None, kinds=...) -> bool
- zone_and_ancestor_ids(zone_id) -> list[uuid]
- users_with_role_in_zone(role_code, zone_id, at=None, include_ancestors=True) -> list[User]
- vets_for_zone(zone_id, at=None, include_ancestors=True) -> list[User] (habilitation valide)
- authorities_for_zone(zone_id, at=None, include_ancestors=True) -> list[User]

Fonctions d'écriture (journalisées dans audit_log) :
- grant_role, verify_habilitation, create_mandate
- authenticate_by_phone, issue_tokens, refresh_access, logout
"""

from datetime import date, datetime

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import record_event

from .models import Habilitation, Mandate, Membership, Role
from .validators import normalize_phone

# Habilitations qui permettent une décision sanitaire (validation niveau 3).
VET_HABILITATION_KINDS = ("vet_order",)


class AccountsError(Exception):
    """Erreur métier du module accounts ; le message est lisible par l'utilisateur."""


# ---------------------------------------------------------------------------
# Lecture : rôles et habilitations
# ---------------------------------------------------------------------------

def _as_datetime(at):
    return at or timezone.now()


def _as_date(at):
    """Accepte une date, un datetime (aware) ou None (= maintenant)."""
    if at is None:
        return timezone.localdate()
    if isinstance(at, datetime):
        return timezone.localdate(at) if timezone.is_aware(at) else at.date()
    if isinstance(at, date):
        return at
    raise TypeError("at doit être une date ou un datetime.")


def active_memberships(user, at=None):
    """Appartenances (rôle, organisation, zone) actives à l'instant `at`."""
    at = _as_datetime(at)
    return (
        Membership.objects.filter(user=user, starts_at__lte=at)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
        .select_related("role", "organization", "zone")
    )


def active_roles(user, at=None):
    """Rôles actifs de l'utilisateur à l'instant `at` (liste de Role, sans doublon)."""
    if not getattr(user, "is_active", False):
        return []
    roles = {m.role_id: m.role for m in active_memberships(user, at)}
    return sorted(roles.values(), key=lambda role: role.code)


def user_has_role(user, role_code, at=None):
    """Vrai si l'utilisateur a le rôle `role_code` (ex. "veterinarian") à l'instant `at`."""
    return any(role.code == role_code for role in active_roles(user, at))


def get_valid_habilitation(user, at=None, kinds=VET_HABILITATION_KINDS):
    """Habilitation valide à la date `at`, ou None.

    Valide = statut "verified" ET valid_from <= date <= valid_to ET compte actif.
    "pending", "revoked", "expired" ou hors dates : refusé.
    Utiliser l'objet retourné pour remplir `habilitation_id` (évaluation, alerte niveau 3).
    """
    if not getattr(user, "is_active", False):
        return None
    day = _as_date(at)
    return (
        Habilitation.objects.filter(
            user=user,
            kind__in=kinds,
            status="verified",
            valid_from__lte=day,
            valid_to__gte=day,
        )
        .order_by("-valid_to")
        .first()
    )


def user_has_valid_habilitation(user, at=None, kinds=VET_HABILITATION_KINDS):
    """Vrai si l'utilisateur a une habilitation valide à la date `at` (défaut : aujourd'hui)."""
    return get_valid_habilitation(user, at, kinds) is not None


# ---------------------------------------------------------------------------
# Écriture : rôles, habilitations, mandats
# ---------------------------------------------------------------------------

def grant_role(user, role_code, *, organization=None, zone=None, starts_at=None, granted_by=None):
    """Donne un rôle actif. Idempotent : retourne l'appartenance active si elle existe."""
    role = Role.objects.filter(code=role_code).first()
    if role is None:
        raise AccountsError(f"Rôle inconnu : {role_code}. Lancez manage.py seed.")
    existing = Membership.objects.filter(
        user=user, role=role, organization=organization, ends_at__isnull=True
    ).first()
    if existing:
        return existing
    membership = Membership.objects.create(
        user=user,
        role=role,
        organization=organization,
        zone=zone,
        starts_at=starts_at or timezone.now(),
    )
    record_event(
        "role.grant",
        actor_user=granted_by,
        entity_table="membership",
        entity_id=membership.id,
        details={"user_id": str(user.id), "role": role_code},
    )
    return membership


@transaction.atomic
def verify_habilitation(habilitation, verifier, at=None):
    """Passe une habilitation en "verified". Le vérificateur ne peut pas être l'intéressé."""
    habilitation = Habilitation.objects.select_for_update().get(pk=habilitation.pk)
    if verifier.pk == habilitation.user_id:
        raise AccountsError("On ne peut pas vérifier sa propre habilitation.")
    if habilitation.status == "verified":
        return habilitation
    if habilitation.status != "pending":
        raise AccountsError("Cette habilitation ne peut plus être vérifiée.")
    habilitation.status = "verified"
    habilitation.verified_by = verifier
    habilitation.verified_at = _as_datetime(at)
    habilitation.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    record_event(
        "habilitation.verify",
        actor_user=verifier,
        entity_table="habilitation",
        entity_id=habilitation.id,
        details={
            "user_id": str(habilitation.user_id),
            "kind": habilitation.kind,
            "valid_to": habilitation.valid_to.isoformat(),
        },
    )
    return habilitation


def create_mandate(agent, granted_by, scope, *, starts_at=None, ends_at=None, mandate_id=None):
    """Crée un mandat (sans centres). Utiliser identity.services.grant_mandate pour lier les centres."""
    kwargs = {"id": mandate_id} if mandate_id else {}
    mandate = Mandate.objects.create(
        agent_user=agent,
        granted_by=granted_by,
        scope=scope,
        starts_at=starts_at or timezone.now(),
        ends_at=ends_at,
        **kwargs,
    )
    record_event(
        "mandate.create",
        actor_user=granted_by,
        entity_table="mandate",
        entity_id=mandate.id,
        details={"agent_user_id": str(agent.id), "scope": scope},
    )
    return mandate


# ---------------------------------------------------------------------------
# Authentification (appelée par les vues /api/auth/)
# ---------------------------------------------------------------------------

def authenticate_by_phone(phone, password, *, ip=None):
    """Retourne l'utilisateur si numéro + mot de passe sont bons et le compte actif, sinon None.

    Journalise "auth.login" ou "auth.login_failed". Le mot de passe n'est jamais journalisé.
    """
    try:
        phone = normalize_phone(phone)
    except ValidationError:
        phone = str(phone or "")[:20]
    user = authenticate(phone=phone, password=password)
    if user is None:
        known = get_user_model().objects.filter(phone=phone).only("id", "is_active").first()
        reason = "inactive" if known and not known.is_active else "bad_credentials"
        record_event(
            "auth.login_failed",
            actor_user=None,
            entity_id=known.id if known else None,
            details={"phone": phone, "ip": ip, "reason": reason},
        )
        return None
    update_last_login(None, user)
    record_event("auth.login", actor_user=user, entity_id=user.id, details={"ip": ip})
    return user


def issue_tokens(user):
    """Crée une paire de jetons JWT : {"access": ..., "refresh": ...}."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _user_from_refresh(token):
    user_id = token.payload.get(jwt_settings.USER_ID_CLAIM)
    return get_user_model().objects.filter(**{jwt_settings.USER_ID_FIELD: user_id}).first()


def refresh_access(raw_refresh):
    """Retourne un nouveau jeton d'accès, ou None si le refresh est invalide, en liste noire
    ou si le compte est désactivé."""
    try:
        token = RefreshToken(raw_refresh)
    except TokenError:
        return None
    user = _user_from_refresh(token)
    if user is None or not user.is_active:
        return None
    return {"access": str(token.access_token)}


def logout(user, raw_refresh):
    """Met le refresh en liste noire. Vrai si c'est fait (ou déjà fait), faux si le jeton
    est invalide ou appartient à un autre utilisateur."""
    try:
        token = RefreshToken(raw_refresh)  # signature, expiration et liste noire vérifiées
    except TokenError:
        # Déjà en liste noire = déjà déconnecté : on accepte (opération rejouable hors ligne).
        try:
            payload = token_backend.decode(raw_refresh, verify=True)
        except TokenBackendError:
            return False
        if str(payload.get(jwt_settings.USER_ID_CLAIM)) != str(user.pk):
            return False
        return BlacklistedToken.objects.filter(token__jti=payload.get("jti")).exists()
    if str(token.payload.get(jwt_settings.USER_ID_CLAIM)) != str(user.pk):
        return False
    token.blacklist()
    record_event("auth.logout", actor_user=user, entity_id=user.pk)
    return True


# ---------------------------------------------------------------------------
# Destinataires par zone (alertes de zone, notifications)
# ---------------------------------------------------------------------------

MAX_ZONE_DEPTH = 7  # zone.level va de 0 (pays) à 6


def zone_and_ancestor_ids(zone_id):
    """La zone puis ses zones parentes, de la plus petite au pays (lecture des ids de geo)."""
    from apps.geo.models import Zone

    ids, current = [], zone_id
    while current and current not in ids and len(ids) <= MAX_ZONE_DEPTH:
        ids.append(current)
        current = Zone.objects.filter(pk=current).values_list("parent_id", flat=True).first()
    return ids


def users_with_role_in_zone(role_code, zone_id, at=None, *, include_ancestors=True):
    """Utilisateurs actifs ayant le rôle `role_code` actif sur la zone (et, par défaut,
    sur une de ses zones parentes). Un rôle sans zone ne compte pas : pas de périmètre."""
    if not zone_id:
        return []
    zones = zone_and_ancestor_ids(zone_id) if include_ancestors else [zone_id]
    at = _as_datetime(at)
    user_ids = (
        Membership.objects.filter(role__code=role_code, zone_id__in=zones, starts_at__lte=at)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=at))
        .values_list("user_id", flat=True)
    )
    return list(get_user_model().objects.filter(pk__in=user_ids, is_active=True).order_by("full_name"))


def vets_for_zone(zone_id, at=None, *, include_ancestors=True):
    """Vétérinaires à prévenir pour une zone : rôle "veterinarian" actif sur la zone
    (ou une zone parente) ET habilitation valide à la date `at`.

    Relance vers le niveau au-dessus : appeler avec l'id de la zone parente.
    Exemple : vets_for_zone(alert.zone_id) puis vets_for_zone(zone.parent_id).
    """
    return [
        user for user in users_with_role_in_zone("veterinarian", zone_id, at,
                                                 include_ancestors=include_ancestors)
        if user_has_valid_habilitation(user, at)
    ]


def authorities_for_zone(zone_id, at=None, *, include_ancestors=True):
    """Autorités dont le périmètre couvre la zone (dernier recours d'une relance)."""
    return users_with_role_in_zone("authority", zone_id, at, include_ancestors=include_ancestors)
