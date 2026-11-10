import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.identity.models import TrackedUnit
from apps.traceability.exceptions import (
    InvalidMovementDataError,
    UnitAlreadyLockedError,
    UnitNotAtOriginCenterError,
)
from apps.traceability.models import (
    Movement,
    MovementConfirmationCode,
    MovementItem,
    MovementStatusEvent,
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
