import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
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


def expire_overdue_movements(now=None):
    """Passe « expiré » les départs jamais reçus dont aucun code n'est plus valable
    (MV-05). Les unités sont libérées et restent au départ. Retourne le nombre expiré."""
    now = now or timezone.now()
    valid_code = MovementConfirmationCode.objects.filter(
        movement=OuterRef("pk"), used_at__isnull=True, expires_at__gt=now
    )
    candidates = (
        Movement.objects.filter(status="declared")
        .exclude(confirmations__side="receiver")
        .exclude(Exists(valid_code))
        .values_list("pk", flat=True)
    )
    count = 0
    for movement_id in list(candidates):
        with transaction.atomic():
            movement = _locked_movement(movement_id)
            if movement.status != "declared":
                continue
            _close_open_movement(movement)
            _set_status(movement, "expired", reason="Délai de confirmation dépassé",
                        created_by=movement.created_by, occurred_at=now)
            record_event(action="movement.expire", entity_table="movement",
                         entity_id=movement.id)
            count += 1
    return count


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
