"""Fonctions publiques du module identity.

Les autres modules n'écrivent JAMAIS directement dans les tables d'identity :
ils appellent ces fonctions. Les colonnes CALCULÉ (tracked_unit.current_center,
lot.current_size, life_status) ne sont écrites qu'ici.

Codes courts :
- make_short_code(body8), is_valid_short_code(code), normalize_short_code(text)
Accès aux centres (utilisé par accounts.permissions.HasCenterAccess) :
- accessible_centers(user, at=None, scope=None), user_can_access_center(...)
Écriture :
- create_center, add_center_member, grant_mandate
- register_animal, register_lot, create_label_batch, bind_label, replace_label
- set_current_center (appelée par traceability à la double confirmation)
Lecture (API) :
- user_covers_zone, user_can_view_unit, active_label, scan_label, label_for_registration
"""

import secrets

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.services import create_mandate
from apps.audit.services import record_event

from .models import (
    Animal,
    Center,
    CenterMember,
    CenterSpecies,
    IdentitySupport,
    Label,
    LabelBatch,
    Lot,
    MandateCenter,
    TrackedUnit,
)

# 32 caractères : chiffres 2-9 et lettres sans I ni O (pas de confusion avec 1 et 0).
SHORT_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
SHORT_CODE_BODY_LENGTH = 8


class IdentityError(Exception):
    """Erreur métier du module identity ; le message est lisible par l'utilisateur."""


# ---------------------------------------------------------------------------
# Codes courts (étiquettes QR)
# ---------------------------------------------------------------------------

def _luhn_sum(chars, start_factor):
    n = len(SHORT_CODE_ALPHABET)
    factor, total = start_factor, 0
    for char in reversed(chars):
        addend = factor * SHORT_CODE_ALPHABET.index(char)
        total += addend // n + addend % n
        factor = 1 if factor == 2 else 2
    return total


def compute_check_char(body):
    """Caractère de contrôle (algorithme de Luhn mod 32) : détecte une faute de frappe
    sur un caractère et la plupart des inversions de deux caractères voisins."""
    if len(body) != SHORT_CODE_BODY_LENGTH or any(c not in SHORT_CODE_ALPHABET for c in body):
        raise IdentityError("Code invalide.")
    n = len(SHORT_CODE_ALPHABET)
    return SHORT_CODE_ALPHABET[(n - _luhn_sum(body, 2) % n) % n]


def make_short_code(body):
    """Code complet de 9 caractères : 8 caractères + 1 caractère de contrôle."""
    return body + compute_check_char(body)


def random_short_code():
    body = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_BODY_LENGTH))
    return make_short_code(body)


def normalize_short_code(text):
    """Code saisi ou dicté -> forme canonique (majuscules, sans espace ni tiret)."""
    return "".join(str(text or "").upper().split()).replace("-", "")


def is_valid_short_code(code):
    """Vrai si le code a le bon format ET un caractère de contrôle correct."""
    code = normalize_short_code(code)
    if len(code) != SHORT_CODE_BODY_LENGTH + 1 or any(c not in SHORT_CODE_ALPHABET for c in code):
        return False
    return _luhn_sum(code, 1) % len(SHORT_CODE_ALPHABET) == 0


# ---------------------------------------------------------------------------
# Accès aux centres
# ---------------------------------------------------------------------------

def _active(qs, at, start="starts_at", end="ends_at"):
    return qs.filter(**{f"{start}__lte": at}).filter(
        Q(**{f"{end}__isnull": True}) | Q(**{f"{end}__gt": at})
    )


def _mandate_links(user, at, scope=None):
    links = MandateCenter.objects.filter(
        mandate__agent_user=user,
        mandate__starts_at__lte=at,
        mandate__revoked_at__isnull=True,
    ).filter(Q(mandate__ends_at__isnull=True) | Q(mandate__ends_at__gt=at))
    if scope:
        links = links.filter(mandate__scope__in=(scope, "all"))
    return links


def accessible_centers(user, at=None, scope=None):
    """Centres auxquels l'utilisateur a accès à l'instant `at`, avec la raison.

    Accès = membre actif du centre (holder, co_holder, worker) OU mandat actif
    (non révoqué) qui couvre ce centre. `scope` ("declare", "move") limite les
    mandats à ceux qui donnent ce droit (ou "all").
    Retourne une liste de dicts : id, name, center_type, zone_id, access, mandate_scope.
    """
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return []
    at = at or timezone.now()
    result = {}
    for member in _active(CenterMember.objects.filter(user=user), at).select_related("center"):
        result[member.center_id] = {
            "id": member.center_id,
            "name": member.center.name,
            "center_type": member.center.center_type,
            "zone_id": member.center.zone_id,
            "access": member.member_role,
            "mandate_scope": None,
        }
    for link in _mandate_links(user, at, scope).select_related("center", "mandate"):
        result.setdefault(
            link.center_id,
            {
                "id": link.center_id,
                "name": link.center.name,
                "center_type": link.center.center_type,
                "zone_id": link.center.zone_id,
                "access": "mandate",
                "mandate_scope": link.mandate.scope,
            },
        )
    return sorted(result.values(), key=lambda c: c["name"])


def user_can_access_center(user, center_id, at=None, scope=None):
    """Vrai si l'utilisateur est membre actif du centre ou a un mandat actif dessus."""
    if not center_id or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    at = at or timezone.now()
    if _active(CenterMember.objects.filter(user=user, center_id=center_id), at).exists():
        return True
    return _mandate_links(user, at, scope).filter(center_id=center_id).exists()


# ---------------------------------------------------------------------------
# Centres et mandats
# ---------------------------------------------------------------------------

@transaction.atomic
def create_center(
    *, name, zone, center_type, created_by, holder, species=(), organization=None,
    center_id=None, is_simulated=False, starts_at=None,
):
    """Crée un centre et son détenteur (holder) dans la même transaction."""
    kwargs = {"id": center_id} if center_id else {}
    center = Center.objects.create(
        name=name,
        zone=zone,
        center_type=center_type,
        organization=organization,
        location_source="none",
        created_by=created_by,
        is_simulated=is_simulated,
        **kwargs,
    )
    add_center_member(center, holder, "holder", starts_at=starts_at, added_by=created_by)
    for sp in species:
        CenterSpecies.objects.get_or_create(center=center, species=sp)
    record_event(
        "center.create", actor_user=created_by, entity_table="center", entity_id=center.id
    )
    return center


def add_center_member(center, user, member_role, *, starts_at=None, added_by=None):
    """Ajoute un membre actif. Idempotent : retourne l'appartenance active existante."""
    existing = CenterMember.objects.filter(center=center, user=user, ends_at__isnull=True).first()
    if existing:
        return existing
    return CenterMember.objects.create(
        center=center, user=user, member_role=member_role, starts_at=starts_at or timezone.now()
    )


@transaction.atomic
def grant_mandate(agent, granted_by, centers, scope, *, starts_at=None, ends_at=None, mandate_id=None):
    """Crée un mandat (accounts) et le lie aux centres donnés."""
    mandate = create_mandate(
        agent, granted_by, scope, starts_at=starts_at, ends_at=ends_at, mandate_id=mandate_id
    )
    for center in centers:
        MandateCenter.objects.create(mandate=mandate, center=center)
    return mandate


# ---------------------------------------------------------------------------
# Unités suivies (animaux, lots)
# ---------------------------------------------------------------------------

def _create_unit(kind, *, species, center, created_by, unit_id, local_name, device, is_simulated):
    if kind == "animal" and species.tracking_mode not in ("animal", "both"):
        raise IdentityError("Cette espèce se suit par lot.")
    if kind == "lot" and species.tracking_mode not in ("lot", "both"):
        raise IdentityError("Cette espèce se suit animal par animal.")
    kwargs = {"id": unit_id} if unit_id else {}
    return TrackedUnit.objects.create(
        kind=kind,
        species=species,
        current_center=center,
        local_name=local_name,
        created_by=created_by,
        device=device,
        is_simulated=is_simulated,
        **kwargs,
    )


@transaction.atomic
def register_animal(
    *, species, center, created_by, unit_id=None, local_name=None, sex="unknown",
    birth_date=None, birth_date_precision=None, breed=None, marks=None, label=None,
    device=None, is_simulated=False,
):
    """Enregistre un animal dans un centre ; pose l'étiquette `label` si donnée."""
    unit = _create_unit(
        "animal", species=species, center=center, created_by=created_by, unit_id=unit_id,
        local_name=local_name, device=device, is_simulated=is_simulated,
    )
    Animal.objects.create(
        unit=unit, sex=sex, birth_date=birth_date, birth_date_precision=birth_date_precision,
        breed=breed, marks=marks,
    )
    record_event("unit.register", actor_user=created_by, entity_table="tracked_unit",
                 entity_id=unit.id, details={"kind": "animal"})
    if label is not None:
        bind_label(unit, label, created_by)
    return unit


@transaction.atomic
def register_lot(
    *, species, center, size, created_by, unit_id=None, local_name=None, description=None,
    label=None, device=None, is_simulated=False,
):
    """Enregistre un lot (volaille, petits ruminants en groupe) de `size` têtes."""
    if size <= 0:
        raise IdentityError("L'effectif doit être supérieur à zéro.")
    unit = _create_unit(
        "lot", species=species, center=center, created_by=created_by, unit_id=unit_id,
        local_name=local_name, device=device, is_simulated=is_simulated,
    )
    Lot.objects.create(unit=unit, current_size=size, description=description)
    record_event("unit.register", actor_user=created_by, entity_table="tracked_unit",
                 entity_id=unit.id, details={"kind": "lot", "size": size})
    if label is not None:
        bind_label(unit, label, created_by)
    return unit


def set_current_center(unit, center):
    """Met à jour le centre courant (CALCULÉ). Réservé à traceability.services, à appeler
    dans la transaction de la double confirmation, unités déjà verrouillées."""
    TrackedUnit.objects.filter(pk=unit.pk).update(current_center=center, updated_at=timezone.now())


# ---------------------------------------------------------------------------
# Étiquettes
# ---------------------------------------------------------------------------

@transaction.atomic
def create_label_batch(*, quantity, created_by, note=None, codes=None, batch_id=None):
    """Crée un lot d'impression et ses étiquettes (codes aléatoires si `codes` absent)."""
    if codes is not None and len(codes) != quantity:
        raise IdentityError("Le nombre de codes ne correspond pas à la quantité.")
    for code in codes or ():
        if not is_valid_short_code(code):
            raise IdentityError("Code invalide.")
    kwargs = {"id": batch_id} if batch_id else {}
    batch = LabelBatch.objects.create(quantity=quantity, created_by=created_by, note=note, **kwargs)
    pending = list(codes) if codes is not None else []
    while len(pending) < quantity:
        code = random_short_code()
        if code not in pending and not Label.objects.filter(short_code=code).exists():
            pending.append(code)
    Label.objects.bulk_create(Label(batch=batch, short_code=code) for code in pending)
    record_event("label_batch.create", actor_user=created_by, entity_table="label_batch",
                 entity_id=batch.id, details={"quantity": quantity})
    return batch


@transaction.atomic
def issue_labels(labels, center, *, issued_by):
    """Remet des étiquettes vierges (statut "printed") à un centre : statut "issued"."""
    ids = [label.pk for label in labels]
    if Label.objects.filter(pk__in=ids).exclude(status="printed").exists():
        raise IdentityError("Certaines étiquettes ont déjà été remises ou utilisées.")
    Label.objects.filter(pk__in=ids).update(status="issued", issued_to_center=center)
    record_event("label.issue", actor_user=issued_by, entity_table="center", entity_id=center.pk,
                 details={"count": len(ids)})


@transaction.atomic
def bind_label(unit, label, bound_by, *, at=None):
    """Pose une étiquette QR sur une unité. Refuse une étiquette déjà utilisée ou désactivée,
    ou une unité qui a déjà une étiquette QR active."""
    label = Label.objects.select_for_update().get(pk=label.pk)
    if label.status in ("deactivated", "lost"):
        raise IdentityError("Cette étiquette n'est plus utilisable.")
    if IdentitySupport.objects.filter(label=label, unbound_at__isnull=True).exists():
        raise IdentityError("Cette étiquette est déjà posée sur un autre animal.")
    if IdentitySupport.objects.filter(
        unit=unit, support_type="qr_label", unbound_at__isnull=True
    ).exists():
        raise IdentityError("Cet animal a déjà une étiquette.")
    support = IdentitySupport.objects.create(
        unit=unit, support_type="qr_label", label=label, bound_at=at or timezone.now(),
        bound_by=bound_by,
    )
    label.status = "active"
    if unit.current_center_id and not label.issued_to_center_id:
        label.issued_to_center_id = unit.current_center_id
    label.save(update_fields=["status", "issued_to_center"])
    record_event("label.bind", actor_user=bound_by, entity_table="identity_support",
                 entity_id=support.id, details={"unit_id": str(unit.id)})
    return support


# ---------------------------------------------------------------------------
# Lecture : consultation d'une fiche et scan (utilisé par les vues de l'API)
# ---------------------------------------------------------------------------

# Rôles professionnels qui consultent une fiche dans leur périmètre géographique.
PROFESSIONAL_ROLES = ("veterinarian", "authority")


def user_covers_zone(user, zone_id, roles=PROFESSIONAL_ROLES, at=None):
    """Vrai si l'utilisateur a un rôle professionnel actif sur cette zone ou une zone parente.

    Un rôle sans zone (membership.zone_id NULL) ne donne AUCUN périmètre géographique.
    """
    from apps.accounts.services import active_memberships, zone_and_ancestor_ids

    if not zone_id or not getattr(user, "is_authenticated", False):
        return False
    return active_memberships(user, at).filter(
        role__code__in=roles, zone_id__in=zone_and_ancestor_ids(zone_id)
    ).exists()


def user_can_view_unit(user, unit, at=None):
    """Fiche complète visible par : les membres ou mandataires du centre courant, et les
    vétérinaires ou autorités dont le périmètre couvre la zone de ce centre."""
    center_id = unit.current_center_id
    if not center_id:
        return False
    if user_can_access_center(user, center_id, at=at):
        return True
    zone_id = Center.objects.filter(pk=center_id).values_list("zone_id", flat=True).first()
    return user_covers_zone(user, zone_id, at=at)


def active_label(unit):
    """Étiquette QR actuellement posée sur l'unité, ou None."""
    support = (
        IdentitySupport.objects.filter(unit=unit, support_type="qr_label", unbound_at__isnull=True)
        .select_related("label")
        .first()
    )
    return support.label if support else None


def scan_label(code):
    """Résout un code scanné ou saisi. Retourne (résultat, label, unit).

    Résultats : "invalid" (format ou caractère de contrôle faux), "unknown" (aucune
    étiquette), "not_bound" (étiquette vierge), "found", "replaced" (étiquette
    désactivée : unit = l'unité qui la portait, pour renvoyer vers sa fiche),
    "lost" (étiquette déclarée perdue).
    Lecture seule : n'écrit pas d'identity_verification.
    """
    code = normalize_short_code(code)
    if not is_valid_short_code(code):
        return "invalid", None, None
    label = Label.objects.filter(short_code=code).first()
    if label is None:
        return "unknown", None, None
    support = (
        IdentitySupport.objects.filter(label=label).select_related("unit").order_by("-bound_at").first()
    )
    if support is None:
        return "not_bound", label, None
    if support.unbound_at is None:
        return "found", label, support.unit
    return ("lost" if label.status == "lost" else "replaced"), label, support.unit


def label_for_registration(code, center):
    """Étiquette utilisable pour enregistrer une unité dans `center`, ou IdentityError."""
    code = normalize_short_code(code)
    if not is_valid_short_code(code):
        raise IdentityError("Étiquette non reconnue. Essayez encore ou saisissez le code.")
    label = Label.objects.filter(short_code=code).first()
    if label is None:
        raise IdentityError("Étiquette non reconnue. Essayez encore ou saisissez le code.")
    if label.issued_to_center_id and label.issued_to_center_id != center.pk:
        raise IdentityError("Cette étiquette a été remise à un autre élevage.")
    return label


# ---------------------------------------------------------------------------
# Remplacer une étiquette (spec 9.4)
# ---------------------------------------------------------------------------

REPLACE_REASONS = ("lost", "damaged", "error")


@transaction.atomic
def replace_label(unit, new_label, replaced_by, *, reason, at=None):
    """Retire l'étiquette QR active de l'unité et pose `new_label`, dans une transaction.

    `reason` : "lost" (perdue : l'ancienne passe au statut "lost"), "damaged" (abîmée) ou
    "error" (mauvaise étiquette posée) : l'ancienne passe à "deactivated".
    L'identifiant de l'unité ne change jamais ; l'historique des supports est conservé.
    Un scan de l'ancienne étiquette renvoie ensuite « étiquette remplacée » (scan_label).
    Rejouer le même remplacement est sans effet (retourne le support actif).
    """
    if reason not in REPLACE_REASONS:
        raise IdentityError("Raison inconnue.")
    at = at or timezone.now()
    unit = TrackedUnit.objects.select_for_update().get(pk=unit.pk)
    old = (
        IdentitySupport.objects.select_for_update()
        .filter(unit=unit, support_type="qr_label", unbound_at__isnull=True)
        .first()
    )
    if old is not None:
        if old.label_id == new_label.pk:
            return old  # déjà fait (envoi rejoué hors ligne) : sans effet
        old.unbound_at = at
        old.unbound_reason = reason
        old.save(update_fields=["unbound_at", "unbound_reason"])
        Label.objects.filter(pk=old.label_id).update(
            status="lost" if reason == "lost" else "deactivated"
        )
    support = bind_label(unit, new_label, replaced_by, at=at)
    record_event(
        "label.replace", actor_user=replaced_by, entity_table="tracked_unit", entity_id=unit.pk,
        details={"reason": reason, "old_label_id": str(old.label_id) if old else None,
                 "new_label_id": str(new_label.pk)},
    )
    return support
