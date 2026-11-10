import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import (
    Movement,
    MovementItem,
    UnitOpenMovement,
    MovementConfirmation,
    MovementConfirmationCode,
    MovementDiscrepancy,
    MovementStatusEvent,
    StatusEvent,
)

User = get_user_model()


class TraceabilityModelsTestCase(TestCase):
    """
    Tests de validation des modèles du module Traceability (MV-01 à MV-08).
    Conformes à la spécification de base de données BAOBIA (Section 6 & 12).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+2250700000001",
            full_name="Romuald Konan",
            password="testpassword123",
        )
        self.zone = Zone.objects.create(
            code="ABJ",
            name="Abidjan",
            level=1,
        )
        self.center_a = Center.objects.create(
            name="Centre Élevage A",
            zone=self.zone,
            center_type="farm",
            created_by=self.user,
        )
        self.center_b = Center.objects.create(
            name="Centre Élevage B",
            zone=self.zone,
            center_type="farm",
            created_by=self.user,
        )
        self.species = Species.objects.create(
            code="cattle",
            label_fr="Bovins",
            tracking_mode="animal",
        )
        self.unit_1 = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_a,
            created_by=self.user,
        )
        self.unit_2 = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_a,
            created_by=self.user,
        )

    def test_mv01_create_valid_movement(self):
        """MV-01 : Création d'une déclaration de mouvement valide."""
        now = timezone.now()
        movement = Movement.objects.create(
            movement_type="transfer",
            from_center=self.center_a,
            to_center=self.center_b,
            occurred_at=now,
            created_by=self.user,
        )
        self.assertEqual(movement.status, "declared")
        self.assertIsNone(movement.received_at)
        self.assertFalse(movement.is_simulated)

    def test_mv01_cannot_move_to_same_center(self):
        """MV-01 / Contrainte chk_movement_different_centers : from_center <> to_center."""
        now = timezone.now()
        with self.assertRaises(IntegrityError):
            Movement.objects.create(
                movement_type="transfer",
                from_center=self.center_a,
                to_center=self.center_a,
                occurred_at=now,
                created_by=self.user,
            )

    def test_mv02_unit_open_movement_lock(self):
        """MV-02 : Verrou UnitOpenMovement empêche d'avoir deux mouvements ouverts pour la même unité."""
        now = timezone.now()
        mvt1 = Movement.objects.create(
            movement_type="transfer",
            from_center=self.center_a,
            to_center=self.center_b,
            occurred_at=now,
            created_by=self.user,
        )
        mvt2 = Movement.objects.create(
            movement_type="transfer",
            from_center=self.center_a,
            to_center=self.center_b,
            occurred_at=now,
            created_by=self.user,
        )

        # Verrouiller l'unité 1 sur le mouvement 1
        UnitOpenMovement.objects.create(unit=self.unit_1, movement=mvt1)

        # Tenter de verrouiller la même unité sur le mouvement 2 doit échouer (PK = unit_id)
        with self.assertRaises(IntegrityError):
            UnitOpenMovement.objects.create(unit=self.unit_1, movement=mvt2)

    def test_mv04_movement_confirmation_unique_per_side(self):
        """MV-04 : Une seule confirmation par côté (expéditeur / destinataire)."""
        now = timezone.now()
        mvt = Movement.objects.create(
            movement_type="transfer",
            from_center=self.center_a,
            to_center=self.center_b,
            occurred_at=now,
            created_by=self.user,
        )

        MovementConfirmation.objects.create(
            movement=mvt,
            side="sender",
            decision="confirm",
            occurred_at=now,
            created_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            MovementConfirmation.objects.create(
                movement=mvt,
                side="sender",
                decision="confirm",
                occurred_at=now,
                created_by=self.user,
            )

    def test_mv08_event_is_immutable(self):
        """Règle 3 / Ajout seul : un événement (MovementConfirmation, StatusEvent) ne se modifie ni ne se supprime."""
        now = timezone.now()
        mvt = Movement.objects.create(
            movement_type="transfer",
            from_center=self.center_a,
            to_center=self.center_b,
            occurred_at=now,
            created_by=self.user,
        )

        conf = MovementConfirmation.objects.create(
            movement=mvt,
            side="sender",
            decision="confirm",
            occurred_at=now,
            created_by=self.user,
        )

        # Modification interdite
        conf.decision = "refuse"
        with self.assertRaises(RuntimeError):
            conf.save()

        # Suppression interdite
        with self.assertRaises(RuntimeError):
            conf.delete()

    def test_status_event_supersedes_unique(self):
        """StatusEvent (CorrectableMixin) : une ligne ne peut être corrigée qu'une fois."""
        now = timezone.now()
        evt1 = StatusEvent.objects.create(
            unit=self.unit_1,
            event_type="birth",
            occurred_at=now,
            created_by=self.user,
        )
        evt_corr1 = StatusEvent.objects.create(
            unit=self.unit_1,
            event_type="birth",
            supersedes=evt1,
            occurred_at=now,
            created_by=self.user,
        )
        # Deuxième correction du même événement initial interdite
        with self.assertRaises(IntegrityError):
            StatusEvent.objects.create(
                unit=self.unit_1,
                event_type="birth",
                supersedes=evt1,
                occurred_at=now,
                created_by=self.user,
            )
