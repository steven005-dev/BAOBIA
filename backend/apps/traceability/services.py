import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Case, CharField, Exists, OuterRef, Value, When
from django.utils import timezone

from apps.audit.services import record_event
from apps.identity.models import TrackedUnit
from apps.identity.services import set_current_center
from apps.traceability.exceptions import (
    InvalidConfirmationCodeError,
    InvalidMovementDataError,
    MovementNotReceivableError,
    OperationConflictError,
    UnitAlreadyLockedError,
    UnitNotAtOriginCenterError,
)
from apps.traceability.models import (
    Movement,
    MovementConfirmation,
    MovementConfirmationCode,
    MovementDiscrepancy,
    MovementItem,
    MovementStatusEvent,
    StatusEvent,
    UnitOpenMovement,
)


# Décision du chef de projet (21/11, Q2) : un verrou garde un animal d'être vendu deux
# fois, mais un départ déclaré d'un seul côté ne doit jamais le bloquer pour toujours.
# Après ce délai, le verrou se lève ; le mouvement reste `declared` (« probable ») et
# compte toujours pour l'exposition (spec v1.4, 9.6).
def lock_delay() -> timedelta:
    return timedelta(hours=getattr(settings, "MOVEMENT_LOCK_HOURS", 72))


def release_stale_locks(unit_ids, now=None) -> int:
    """Lève les verrous des unités posés par un départ resté `declared` depuis plus que le
    délai (heure du serveur). Retourne le nombre de verrous levés ; journalise chacun."""
    now = now or timezone.now()
    stale = list(
        UnitOpenMovement.objects.filter(
            unit_id__in=list(unit_ids), movement__status="declared",
            since__lte=now - lock_delay(),
        ).select_related("movement")
    )
    for lock in stale:
        record_event(
            action="movement.lock_released", entity_table="movement",
            entity_id=lock.movement_id,
            details={"unit_id": str(lock.unit_id), "after_hours": lock_delay().total_seconds() / 3600},
        )
    if stale:
        UnitOpenMovement.objects.filter(pk__in=[lock.pk for lock in stale]).delete()
    return len(stale)


def generate_confirmation_code() -> Tuple[str, str]:
    """
    Génère un code de confirmation aléatoire à 6 chiffres lisibles
    et son empreinte de hachage SHA-256 pour stockage sécurisé.
    """
    # 6 chiffres lisibles pour saisie facile par téléphone ou SMS
    plain_code = f"{secrets.randbelow(900000) + 100000}"
    code_hash = hashlib.sha256(plain_code.encode("utf-8")).hexdigest()
    return plain_code, code_hash


def declare_movement(
    *,
    from_center,
    to_center=None,
    movement_type: str = "transfer",
    items: List[Dict[str, Any]],
    created_by,
    occurred_at=None,
    device=None,
    to_party_note: Optional[str] = None,
    expected_return_on=None,
    planned_route=None,
    is_simulated: bool = False,
    movement_id: Optional[uuid.UUID] = None,
) -> Tuple[Movement, str]:
    """
    Déclare un mouvement d'animaux ou de lots entre centres (MV-01, MV-02, MV-03).
    Opération atomique exécutée sous transaction :
      1. Verrouille les unités concernées (select_for_update).
      2. Vérifie qu'elles sont bien dans le centre expéditeur (from_center).
      3. Pose le verrou d'exclusivité UnitOpenMovement (échec si déjà verrouillé).
      4. Crée le Movement, les MovementItem et le premier MovementStatusEvent.
      5. Génère le code de confirmation haché (MovementConfirmationCode).
      6. Enregistre l'événement d'audit.

    Retourne : (movement, plain_confirmation_code)
    """
    if not items:
        raise InvalidMovementDataError("La déclaration doit contenir au moins une unité.")

    if to_center and from_center.id == to_center.id:
        raise InvalidMovementDataError("Le centre de départ et de destination doivent être distincts.")

    now = occurred_at or timezone.now()
    m_id = movement_id or uuid.uuid4()

    # Normaliser la liste des unités
    normalized_items = []
    unit_ids = []
    for item in items:
        unit = item.get("unit")
        unit_id = unit.id if hasattr(unit, "id") else item.get("unit_id")
        qty = item.get("quantity_sent", 1)
        if not unit_id:
            raise InvalidMovementDataError("Chaque ligne de mouvement doit référencer une unité.")
        unit_ids.append(unit_id)
        normalized_items.append({"unit_id": unit_id, "quantity_sent": qty})

    with transaction.atomic():
        # (1) Verrouiller les unités en base
        units = list(
            TrackedUnit.objects.select_for_update()
            .filter(id__in=unit_ids)
        )
        found_unit_ids = {u.id for u in units}
        for u_id in unit_ids:
            if u_id not in found_unit_ids:
                raise InvalidMovementDataError(f"Unité {u_id} introuvable.")

        # Q2 : un verrou posé par un départ resté « probable » se lève après le délai.
        release_stale_locks(unit_ids)

        # (2) Vérifier la localisation actuelle dans le centre expéditeur
        from_center_id = from_center.id if hasattr(from_center, "id") else from_center
        for unit in units:
            if unit.current_center_id != from_center_id:
                raise UnitNotAtOriginCenterError(
                    f"L'unité {unit.id} ne se trouve pas dans le centre expéditeur {from_center_id}."
                )

        # (3) Créer l'enregistrement de mouvement
        movement = Movement.objects.create(
            id=m_id,
            movement_type=movement_type,
            from_center=from_center,
            to_center=to_center,
            to_party_note=to_party_note,
            expected_return_on=expected_return_on,
            planned_route=planned_route,
            occurred_at=now,
            created_by=created_by,
            device=device,
            is_simulated=is_simulated,
        )

        # (4) Poser le verrou UnitOpenMovement pour chaque unité
        for unit in units:
            try:
                UnitOpenMovement.objects.create(unit=unit, movement=movement)
            except IntegrityError:
                raise UnitAlreadyLockedError(
                    f"L'unité {unit.id} est déjà engagée dans un mouvement non terminé."
                )

        # (5) Créer les lignes de mouvement (MovementItem)
        for item_data in normalized_items:
            MovementItem.objects.create(
                movement=movement,
                unit_id=item_data["unit_id"],
                quantity_sent=item_data["quantity_sent"],
            )

        # (6) Journaliser le changement de statut initial
        MovementStatusEvent.objects.create(
            movement=movement,
            status="declared",
            reason="Déclaration initiale du mouvement",
            occurred_at=now,
            created_by=created_by,
            device=device,
            is_simulated=is_simulated,
        )

        # MV-04 : la déclaration enregistrée par l'éleveur vaut confirmation de l'expéditeur.
        MovementConfirmation.objects.create(
            movement=movement,
            side="sender",
            decision="confirm",
            occurred_at=now,
            created_by=created_by,
            device=device,
            is_simulated=is_simulated,
        )

        # (7) Générer le code de confirmation
        plain_code, code_hash = generate_confirmation_code()
        MovementConfirmationCode.objects.create(
            movement=movement,
            code_hash=code_hash,
            expires_at=now + timedelta(days=7),
        )

        # (8) Enregistrer dans le journal d'audit (AuditLog)
        record_event(
            action="movement.declare",
            actor_user=created_by,
            entity_table="movement",
            entity_id=movement.id,
            details={
                "from_center_id": str(from_center_id),
                "to_center_id": str(to_center.id) if to_center else None,
                "movement_type": movement_type,
                "units_count": len(normalized_items),
            },
            device=device,
        )

    return movement, plain_code


def confirmation_mode(user, center_id, at=None) -> str:
    """« direct » si la personne est membre de l'élevage, « assisted » si elle agit par
    mandat (agent). MV-04 : une confirmation assistée n'est jamais présentée comme directe."""
    from apps.identity.services import accessible_centers

    for center in accessible_centers(user, at=at):
        if str(center["id"]) == str(center_id):
            return "assisted" if center["access"] == "mandate" else "direct"
    return "assisted"


def _received_quantities(movement, items_received):
    """Quantité reçue par unité (MV-06). Sans détail : tout ce qui est parti est reçu."""
    sent = {str(item.unit_id): item for item in movement.items.select_related("unit")}
    received = {unit_id: item.quantity_sent for unit_id, item in sent.items()}
    seen = set()
    for line in items_received or ():
        unit_id = str(line.get("unit_id"))
        if unit_id not in sent:
            raise InvalidMovementDataError("Cette unité ne fait pas partie de ce départ.")
        if unit_id in seen:
            raise InvalidMovementDataError("Une unité est indiquée deux fois.")
        seen.add(unit_id)
        quantity = line.get("quantity_received")
        if quantity is None or int(quantity) < 0:
            raise InvalidMovementDataError("Indiquez le nombre reçu (0 ou plus).")
        if sent[unit_id].unit.kind == "animal" and int(quantity) > 1:
            raise InvalidMovementDataError("Un animal ne peut être reçu qu'une fois.")
        received[unit_id] = int(quantity)
    return sent, received


def _close_open_movement(movement):
    """Libère les unités et invalide les codes encore valables du mouvement."""
    UnitOpenMovement.objects.filter(movement=movement).delete()
    movement.confirmation_codes.filter(used_at__isnull=True).update(expires_at=timezone.now())


def _set_status(movement, status, *, reason, created_by, occurred_at, device=None):
    movement.status = status
    movement.save(update_fields=["status"])
    MovementStatusEvent.objects.create(
        movement=movement,
        status=status,
        reason=reason[:160],
        occurred_at=occurred_at,
        created_by=created_by,
        device=device,
        is_simulated=movement.is_simulated,
    )


def _locked_movement(movement_id):
    movement = Movement.objects.select_for_update().filter(pk=movement_id).first()
    if movement is None:
        raise MovementNotReceivableError("Mouvement introuvable.")
    return movement


def confirm_movement_receipt(
    *,
    movement_id,
    receiver_center_id,
    code: str,
    created_by,
    confirmation_id=None,
    occurred_at=None,
    device=None,
    items_received=None,
):
    """Confirme la réception et déplace les unités dans une même transaction (MV-04 à MV-06).

    `items_received` : [{"unit_id", "quantity_received"}] pour le rapprochement (MV-06).
    Les unités absentes de la liste sont reçues en totalité. Un écart crée un
    `MovementDiscrepancy` et passe le mouvement en `partial` au lieu de valider
    automatiquement. Une unité reçue à 0 reste à l'élevage de départ.
    Le mode (direct ou assisté par un agent mandaté) est enregistré dans l'audit.
    """
    error = None
    now = occurred_at or timezone.now()

    with transaction.atomic():
        movement = _locked_movement(movement_id)
        if not movement.to_center_id or str(movement.to_center_id) != str(receiver_center_id):
            raise MovementNotReceivableError("Ce mouvement n'est pas destiné à cet élevage.")

        # Rejouer une réception déjà enregistrée est sans effet (file hors ligne).
        if movement.confirmations.filter(side="receiver").exists():
            return movement
        if movement.status != "declared":
            raise MovementNotReceivableError(
                "Ce départ ne peut plus être reçu (annulé, expiré ou contesté)."
            )
        sent, received = _received_quantities(movement, items_received)
        # Q2 : le verrou a pu être levé après le délai et l'animal repartir ailleurs.
        # BAOBIA ne déplace pas un animal en silence : la réception est « à vérifier ».
        other_locks = set(
            UnitOpenMovement.objects.filter(unit_id__in=list(sent))
            .exclude(movement=movement).values_list("unit_id", flat=True)
        )
        for unit_id, item in sent.items():
            if received[unit_id] > 0 and (
                item.unit.current_center_id != movement.from_center_id
                or item.unit_id in other_locks
            ):
                raise OperationConflictError(
                    "Un animal de ce départ a été déplacé depuis : réception à vérifier."
                )

        confirmation_code = movement.confirmation_codes.select_for_update().order_by("-expires_at").first()
        if confirmation_code is None:
            raise InvalidConfirmationCodeError("Code de confirmation introuvable.")
        if confirmation_code.used_at or confirmation_code.expires_at <= now:
            raise InvalidConfirmationCodeError("Ce code a expiré ou a déjà été utilisé.")
        if confirmation_code.attempts >= 5:
            raise InvalidConfirmationCodeError("Trop d'essais. Demandez de l'aide.")

        expected_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(confirmation_code.code_hash, expected_hash):
            confirmation_code.attempts += 1
            confirmation_code.save(update_fields=["attempts"])
            error = "Code incorrect. Vérifiez le code et réessayez."
        else:
            confirmation_code.used_at = now
            confirmation_code.save(update_fields=["used_at"])
            mode = confirmation_mode(created_by, movement.to_center_id)

            discrepancies = []
            for unit_id, item in sent.items():
                quantity = received[unit_id]
                item.quantity_received = quantity
                item.save(update_fields=["quantity_received"])
                if quantity > 0:
                    set_current_center(item.unit, movement.to_center)
                if quantity != item.quantity_sent:
                    discrepancies.append(MovementDiscrepancy.objects.create(
                        movement=movement,
                        unit=item.unit,
                        kind="missing" if quantity == 0 else "count_mismatch",
                        quantity_expected=item.quantity_sent,
                        quantity_found=quantity,
                        occurred_at=now,
                        created_by=created_by,
                        device=device,
                        is_simulated=movement.is_simulated,
                    ))

            confirmation_kwargs = {"id": confirmation_id} if confirmation_id else {}
            MovementConfirmation.objects.create(
                movement=movement,
                side="receiver",
                decision="confirm_with_discrepancy" if discrepancies else "confirm",
                occurred_at=now,
                created_by=created_by,
                device=device,
                is_simulated=movement.is_simulated,
                **confirmation_kwargs,
            )

            UnitOpenMovement.objects.filter(movement=movement).delete()
            movement.received_at = now
            movement.save(update_fields=["received_at"])
            assisted = " avec l'aide d'un agent" if mode == "assisted" else ""
            if discrepancies:
                total_sent = sum(item.quantity_sent for item in sent.values())
                total_received = sum(received.values())
                reason = f"Reçu avec écart{assisted} : {total_received} reçus sur {total_sent}"
            else:
                reason = f"Réception confirmée par le destinataire{assisted}"
            _set_status(movement, "partial" if discrepancies else "confirmed", reason=reason,
                        created_by=created_by, occurred_at=now, device=device)
            record_event(
                action="movement.confirm_receipt",
                actor_user=created_by,
                entity_table="movement",
                entity_id=movement.id,
                details={
                    "to_center_id": str(movement.to_center_id),
                    "mode": mode,
                    "discrepancies": len(discrepancies),
                },
                device=device,
            )

    # Lever après le commit afin de conserver le compteur d'essais erronés.
    if error:
        raise InvalidConfirmationCodeError(error)
    return movement


def _require_reason(reason):
    reason = (reason or "").strip()
    if not reason:
        raise InvalidMovementDataError("Indiquez le motif.")
    return reason


@transaction.atomic
def refuse_movement_receipt(
    *, movement_id, receiver_center_id, created_by, reason, confirmation_id=None,
    occurred_at=None, device=None,
):
    """Le destinataire refuse la réception : mouvement « contesté », unités laissées au
    départ (MV-05, MV-09). BAOBIA ne tranche pas. Rejouer est sans effet."""
    reason = _require_reason(reason)
    now = occurred_at or timezone.now()
    movement = _locked_movement(movement_id)
    if not movement.to_center_id or str(movement.to_center_id) != str(receiver_center_id):
        raise MovementNotReceivableError("Ce mouvement n'est pas destiné à cet élevage.")
    if movement.confirmations.filter(side="receiver").exists():
        return movement
    if movement.status != "declared":
        raise MovementNotReceivableError("Ce départ ne peut plus être refusé.")

    confirmation_kwargs = {"id": confirmation_id} if confirmation_id else {}
    MovementConfirmation.objects.create(
        movement=movement, side="receiver", decision="refuse", occurred_at=now,
        created_by=created_by, device=device, is_simulated=movement.is_simulated,
        **confirmation_kwargs,
    )
    _close_open_movement(movement)
    _set_status(movement, "disputed", reason=f"Réception refusée : {reason}",
                created_by=created_by, occurred_at=now, device=device)
    record_event(
        action="movement.refuse_receipt", actor_user=created_by, entity_table="movement",
        entity_id=movement.id, device=device,
        details={"to_center_id": str(movement.to_center_id),
                 "mode": confirmation_mode(created_by, movement.to_center_id)},
    )
    return movement


@transaction.atomic
def cancel_movement(*, movement_id, center_id, created_by, reason, occurred_at=None,
                    device=None):
    """L'élevage de départ annule un départ pas encore reçu (MV-05). Le mouvement n'est
    jamais effacé : il passe « annulé » et les unités sont libérées. Rejouer est sans effet."""
    reason = _require_reason(reason)
    now = occurred_at or timezone.now()
    movement = _locked_movement(movement_id)
    if str(movement.from_center_id) != str(center_id):
        raise MovementNotReceivableError("Seul l'élevage de départ peut annuler ce départ.")
    if movement.status == "cancelled":
        return movement
    if movement.status != "declared" or movement.confirmations.filter(side="receiver").exists():
        raise InvalidMovementDataError("Ce départ a déjà été reçu ou refusé : il ne s'annule plus.")

    _close_open_movement(movement)
    _set_status(movement, "cancelled", reason=f"Départ annulé : {reason}",
                created_by=created_by, occurred_at=now, device=device)
    record_event(
        action="movement.cancel", actor_user=created_by, entity_table="movement",
        entity_id=movement.id, device=device, details={"reason": reason[:160]},
    )
    return movement


@transaction.atomic
def contest_movement(*, movement_id, center_id, created_by, reason, occurred_at=None,
                     device=None):
    """Une des deux parties conteste un mouvement reçu (MV-09). Toutes les versions sont
    gardées dans l'historique des statuts ; BAOBIA ne tranche ni la propriété ni le litige :
    les unités ne bougent pas. Rejouer est sans effet."""
    reason = _require_reason(reason)
    now = occurred_at or timezone.now()
    movement = _locked_movement(movement_id)
    if str(center_id) not in (str(movement.from_center_id), str(movement.to_center_id)):
        raise MovementNotReceivableError("Seules les deux parties peuvent contester.")
    if movement.status == "disputed":
        return movement
    if movement.status not in ("confirmed", "partial"):
        raise InvalidMovementDataError("Seul un mouvement reçu peut être contesté.")

    side = "départ" if str(center_id) == str(movement.from_center_id) else "destinataire"
    _set_status(movement, "disputed", reason=f"Contesté par l'élevage {side} : {reason}",
                created_by=created_by, occurred_at=now, device=device)
    record_event(
        action="movement.contest", actor_user=created_by, entity_table="movement",
        entity_id=movement.id, device=device,
        details={"center_id": str(center_id), "reason": reason[:160]},
    )
    return movement


# Spec v1.4 (9.6, 9.11) : un mouvement déclaré d'un seul côté reste `declared` et compte
# pour l'exposition avec une confiance réduite ; il n'expire donc pas automatiquement.
CONFIDENCE_BY_STATUS = {
    "confirmed": "confirmed",  # sûr : expéditeur et destinataire
    "partial": "confirmed",    # reçu par les deux, avec un écart de nombre
    "declared": "one_side",    # probable : déclaré d'un seul côté
    "disputed": "disputed",    # contesté : compte par prudence, confiance réduite
}


def movement_confidence(movement) -> Optional[str]:
    """Confiance d'un mouvement pour le calcul d'exposition (R1) ; None s'il ne compte pas
    (annulé, expiré)."""
    return CONFIDENCE_BY_STATUS.get(movement.status)


def movements_for_exposure(*, from_center_ids, since=None, until=None, species_id=None,
                           include_one_side=True):
    """Mouvements sortants à suivre pour l'exposition (lecture seule, pour alerts).

    Chaque mouvement porte `confidence` : « confirmed », « one_side » ou « disputed ».
    Seuls les mouvements vers un élevage enregistré comptent ; `species_id` garde ceux qui
    portent au moins une unité de cette espèce. Ne modifie rien.
    """
    statuses = [s for s, c in CONFIDENCE_BY_STATUS.items()
                if include_one_side or c != "one_side"]
    movements = Movement.objects.filter(
        from_center_id__in=list(from_center_ids), to_center__isnull=False, status__in=statuses,
    )
    if since is not None:
        movements = movements.filter(occurred_at__gte=since)
    if until is not None:
        movements = movements.filter(occurred_at__lte=until)
    if species_id is not None:
        movements = movements.filter(
            Exists(MovementItem.objects.filter(movement=OuterRef("pk"),
                                               unit__species_id=species_id))
        )
    return movements.annotate(
        confidence=Case(
            *[When(status=s, then=Value(c)) for s, c in CONFIDENCE_BY_STATUS.items()],
            output_field=CharField(),
        )
    ).order_by("occurred_at")


UNIT_EVENT_TYPES = ("death", "slaughter", "missing", "found", "stolen_declared", "stolen_lifted")
# MV-13 : vol et disparition visibles par défaut des seuls professionnels habilités.
RESTRICTED_UNIT_EVENTS = ("missing", "stolen_declared", "stolen_lifted", "found")


@transaction.atomic
def record_unit_event(*, unit_id, center_id, event_type, created_by, occurred_at=None,
                      event_id=None, note=None, device=None):
    """Enregistre un événement de vie d'une unité : décès, abattage, disparition, vol...
    (MV-02). Événement immuable ; rejouer le même `event_id` est sans effet.

    Le statut de vie de l'unité (`tracked_unit.life_status`) appartient au module identity :
    il n'est pas modifié ici tant qu'identity ne fournit pas la fonction publique.
    """
    if event_type not in UNIT_EVENT_TYPES:
        raise InvalidMovementDataError("Type d'événement inconnu.")
    if event_id:
        existing = StatusEvent.objects.filter(pk=event_id).first()
        if existing is not None:
            if (str(existing.unit_id) != str(unit_id) or existing.event_type != event_type
                    or existing.created_by_id != created_by.pk):
                raise OperationConflictError("Cette référence a déjà été utilisée.")
            return existing, False

    unit = TrackedUnit.objects.select_for_update().filter(pk=unit_id).first()
    if unit is None:
        raise InvalidMovementDataError("Unité introuvable.")
    if str(unit.current_center_id) != str(center_id):
        raise UnitNotAtOriginCenterError("Cette unité n'est pas dans cet élevage.")
    release_stale_locks([unit.pk])
    if UnitOpenMovement.objects.filter(unit=unit).exists():
        raise UnitAlreadyLockedError("Cette unité est dans un départ pas encore reçu.")

    kwargs = {"id": event_id} if event_id else {}
    event = StatusEvent.objects.create(
        unit=unit,
        event_type=event_type,
        payload={"note": note[:500]} if note else {},
        visibility="professionals" if event_type in RESTRICTED_UNIT_EVENTS else "owner",
        occurred_at=occurred_at or timezone.now(),
        created_by=created_by,
        device=device,
        is_simulated=getattr(created_by, "is_simulated", False),
        **kwargs,
    )
    record_event(
        action="unit.status_event", actor_user=created_by, entity_table="status_event",
        entity_id=event.pk, device=device,
        details={"unit_id": str(unit.pk), "event_type": event_type,
                 "mode": confirmation_mode(created_by, center_id)},
    )
    return event, True


# ---------------------------------------------------------------------------
# Passage au marché (R2, spec v1.4 9.11 ; décisions du chef de projet du 21/11)
# ---------------------------------------------------------------------------

OUT_OF_SYSTEM_REASON = "Sorti du système : acheteur non inscrit"


def _market(center):
    if center.center_type != "market":
        raise InvalidMovementDataError("Cet élevage n'est pas un marché.")
    if center.status != "active":
        raise InvalidMovementDataError("Ce marché est fermé.")
    return center


def resolve_label_codes(codes):
    """Codes d'étiquettes scannés ou saisis -> unités (par identity.services.scan_label).
    Refuse un code inconnu, vierge, remplacé ou perdu, et un même animal deux fois."""
    from apps.identity.services import normalize_short_code, scan_label

    units = []
    for raw in codes:
        result, _label, unit = scan_label(raw)
        if result != "found":
            raise InvalidMovementDataError(
                f"Étiquette {normalize_short_code(raw)} : non reconnue ou plus valable."
            )
        if unit.pk in {u.pk for u in units}:
            raise InvalidMovementDataError("Un animal est scanné deux fois.")
        units.append(unit)
    if not units:
        raise InvalidMovementDataError("Scannez au moins un animal.")
    return units


def _quantity(unit):
    lot = getattr(unit, "lot", None) if unit.kind == "lot" else None
    return lot.current_size if lot else 1


@transaction.atomic
def declare_market_entry(*, market, label_codes, created_by, entry_id, occurred_at=None,
                         device=None):
    """Entrée au marché déclarée par le marché seul, sans code (Q1).

    Un mouvement par animal, élevage d'origine -> marché, d'identifiant dérivé de
    `entry_id` (rejouer est sans effet). Le marché confirme la réception : l'animal compte
    au marché tout de suite, sans verrou. L'origine n'a pas confirmé : le mouvement reste
    `declared` (« probable ») et compte pour l'exposition avec une confiance réduite.
    Retourne (mouvements, créé).
    """
    _market(market)
    now = occurred_at or timezone.now()
    units = resolve_label_codes(label_codes)
    # Le mouvement du premier animal (ordre des identifiants) porte l'identifiant de
    # l'opération ; les autres en dérivent. Ainsi un rejeu avec d'autres animaux se voit.
    entry_uuid = uuid.UUID(str(entry_id))
    ordered = sorted(units, key=lambda unit: str(unit.pk))
    ids = {unit.pk: (entry_uuid if index == 0 else uuid.uuid5(entry_uuid, str(unit.pk)))
           for index, unit in enumerate(ordered)}
    if Movement.objects.filter(pk=entry_uuid).exists():
        existing = {m.pk: m for m in Movement.objects.filter(pk__in=ids.values())
                    .prefetch_related("items")}
        same = len(existing) == len(ids) and all(
            existing[movement_id].to_center_id == market.pk
            and [item.unit_id for item in existing[movement_id].items.all()] == [unit_id]
            for unit_id, movement_id in ids.items()
        )
        if not same:
            raise OperationConflictError("Cette référence a déjà été utilisée pour une autre entrée.")
        return [existing[ids[unit.pk]] for unit in ordered], False

    locked = list(TrackedUnit.objects.select_for_update().filter(pk__in=list(ids)))
    release_stale_locks(ids)
    if UnitOpenMovement.objects.filter(unit_id__in=list(ids)).exists():
        raise UnitAlreadyLockedError("Un animal est dans un départ pas encore reçu.")
    simulated = bool(created_by.is_simulated or market.is_simulated)
    movements = []
    for unit in locked:
        if unit.current_center_id is None:
            raise InvalidMovementDataError("Un animal n'a pas d'élevage connu.")
        if unit.current_center_id == market.pk:
            raise InvalidMovementDataError("Un animal est déjà au marché.")
        movement = Movement.objects.create(
            id=ids[unit.pk], movement_type="sale", from_center_id=unit.current_center_id,
            to_center=market, occurred_at=now, created_by=created_by, device=device,
            is_simulated=simulated or unit.is_simulated,
        )
        quantity = _quantity(unit)
        MovementItem.objects.create(movement=movement, unit=unit, quantity_sent=quantity,
                                    quantity_received=quantity)
        MovementStatusEvent.objects.create(
            movement=movement, status="declared",
            reason="Entrée au marché déclarée par le marché",
            occurred_at=now, created_by=created_by, device=device,
            is_simulated=movement.is_simulated,
        )
        MovementConfirmation.objects.create(
            movement=movement, side="receiver", decision="confirm", occurred_at=now,
            created_by=created_by, device=device, is_simulated=movement.is_simulated,
        )
        movement.received_at = now
        movement.save(update_fields=["received_at"])
        set_current_center(unit, market)
        record_event(
            action="movement.market_entry", actor_user=created_by, entity_table="movement",
            entity_id=movement.pk, device=device,
            details={"market_id": str(market.pk), "unit_id": str(unit.pk),
                     "mode": confirmation_mode(created_by, market.pk)},
        )
        movements.append(movement)
    return movements, True


@transaction.atomic
def declare_market_exit(*, market, label_codes, created_by, exit_id, to_center=None,
                        to_party_note=None, occurred_at=None, device=None):
    """Sortie du marché déclarée par le marché (R2).

    - Vers un élevage inscrit : départ classique (`declare_movement`), avec code ; il reste
      « probable » tant que l'acheteur ne confirme pas (verrou levé après le délai, Q2).
    - Vers un acheteur non inscrit (Q3) : mouvement clos tout de suite, motif « sorti du
      système » ; l'animal quitte le système (plus d'élevage courant) et reste retrouvable
      dans l'historique. Il ne propage aucune exposition (pas de destination enregistrée).
    Retourne (mouvement, code ou None, créé). Rejouer le même `exit_id` est sans effet.
    """
    _market(market)
    if to_center is None and not (to_party_note or "").strip():
        raise InvalidMovementDataError("Indiquez l'élevage acheteur ou une description de l'acheteur.")
    units = resolve_label_codes(label_codes)

    existing = Movement.objects.filter(pk=exit_id).first()
    if existing is not None:
        same = (
            existing.from_center_id == market.pk
            and existing.to_center_id == (to_center.pk if to_center else None)
            and set(existing.items.values_list("unit_id", flat=True)) == {u.pk for u in units}
        )
        if not same:
            raise OperationConflictError("Cette référence a déjà été utilisée pour une autre sortie.")
        code = None
        if to_center is not None and existing.status == "declared":
            code = renew_confirmation_code(existing)
        return existing, code, False

    movement, code = declare_movement(
        movement_id=exit_id, from_center=market, to_center=to_center, movement_type="sale",
        items=[{"unit": unit, "quantity_sent": _quantity(unit)} for unit in units],
        created_by=created_by, occurred_at=occurred_at, device=device,
        to_party_note=(to_party_note or "").strip() or None,
        is_simulated=bool(created_by.is_simulated or market.is_simulated),
    )
    if to_center is not None:
        return movement, code, True

    now = occurred_at or timezone.now()
    _close_open_movement(movement)
    for item in movement.items.select_related("unit"):
        set_current_center(item.unit, None)
    MovementStatusEvent.objects.create(
        movement=movement, status="declared", reason=OUT_OF_SYSTEM_REASON, occurred_at=now,
        created_by=created_by, device=device, is_simulated=movement.is_simulated,
    )
    record_event(
        action="movement.market_exit", actor_user=created_by, entity_table="movement",
        entity_id=movement.pk, device=device,
        details={"market_id": str(market.pk), "out_of_system": True},
    )
    return movement, None, True


def renew_confirmation_code(movement) -> str:
    """Invalide les codes encore valables et en crée un nouveau (rejeu d'une déclaration)."""
    now = timezone.now()
    movement.confirmation_codes.filter(used_at__isnull=True, expires_at__gt=now).update(
        expires_at=now
    )
    plain_code, code_hash = generate_confirmation_code()
    MovementConfirmationCode.objects.create(
        movement=movement, code_hash=code_hash, expires_at=now + timedelta(days=7),
    )
    return plain_code
