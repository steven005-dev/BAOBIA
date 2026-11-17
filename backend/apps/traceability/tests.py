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
from apps.identity.services import add_center_member
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


class DeclareMovementServiceTestCase(TestCase):
    """
    Tests du service métier declare_movement() (MV-01, MV-02, MV-03, Section 9.1 DB spec).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+2250700000002",
            full_name="Kouamé N'Goran",
            password="testpassword123",
        )
        self.zone = Zone.objects.create(code="BKE", name="Bouaké", level=1)
        self.center_from = Center.objects.create(
            name="Ferme Nord",
            zone=self.zone,
            center_type="farm",
            created_by=self.user,
        )
        self.center_to = Center.objects.create(
            name="Marché Central",
            zone=self.zone,
            center_type="market",
            created_by=self.user,
        )
        self.species = Species.objects.create(
            code="sheep",
            label_fr="Ovins",
            tracking_mode="animal",
        )
        self.unit_1 = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_from,
            created_by=self.user,
        )
        self.unit_2 = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_from,
            created_by=self.user,
        )

    def test_declare_movement_success(self):
        """MV-01, MV-02, MV-03 : Déclaration nominale réussie avec verrous et journalisation."""
        from apps.audit.models import AuditLog
        from apps.traceability.services import declare_movement

        now = timezone.now()
        client_uuid = uuid.uuid4()
        movement, plain_code = declare_movement(
            movement_id=client_uuid,
            from_center=self.center_from,
            to_center=self.center_to,
            movement_type="transfer",
            items=[
                {"unit": self.unit_1, "quantity_sent": 1},
                {"unit": self.unit_2, "quantity_sent": 1},
            ],
            created_by=self.user,
            occurred_at=now,
        )

        # 1. Vérification du mouvement
        self.assertEqual(movement.id, client_uuid)
        self.assertEqual(movement.status, "declared")
        self.assertEqual(movement.from_center, self.center_from)
        self.assertEqual(movement.to_center, self.center_to)

        # 2. Vérification des verrous (MV-02)
        self.assertTrue(UnitOpenMovement.objects.filter(unit=self.unit_1, movement=movement).exists())
        self.assertTrue(UnitOpenMovement.objects.filter(unit=self.unit_2, movement=movement).exists())

        # 3. Vérification des items (MV-03)
        self.assertEqual(movement.items.count(), 2)

        # 4. Vérification de l'événement de statut (MV-08)
        self.assertTrue(movement.status_events.filter(status="declared").exists())

        # 5. Vérification du code de confirmation (MV-07)
        self.assertIsNotNone(plain_code)
        self.assertTrue(movement.confirmation_codes.exists())

        # 6. Vérification de l'audit
        self.assertTrue(
            AuditLog.objects.filter(
                action="movement.declare",
                entity_table="movement",
                entity_id=movement.id,
            ).exists()
        )

    def test_declare_movement_refuses_already_locked_unit(self):
        """MV-02 : Refus si une des unités est déjà dans un mouvement ouvert."""
        from apps.traceability.exceptions import UnitAlreadyLockedError
        from apps.traceability.services import declare_movement

        # Première déclaration verrouille unit_1
        declare_movement(
            from_center=self.center_from,
            to_center=self.center_to,
            items=[{"unit": self.unit_1}],
            created_by=self.user,
        )

        # Deuxième déclaration avec la même unit_1 doit lever UnitAlreadyLockedError
        with self.assertRaises(UnitAlreadyLockedError):
            declare_movement(
                from_center=self.center_from,
                to_center=self.center_to,
                items=[{"unit": self.unit_1}],
                created_by=self.user,
            )

    def test_declare_movement_refuses_unit_not_at_origin_center(self):
        """Refus si l'unité déclarée ne réside pas dans le centre expéditeur."""
        from apps.traceability.exceptions import UnitNotAtOriginCenterError
        from apps.traceability.services import declare_movement

        # Unité résidant dans center_to et non center_from
        other_unit = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_to,
            created_by=self.user,
        )

        with self.assertRaises(UnitNotAtOriginCenterError):
            declare_movement(
                from_center=self.center_from,
                to_center=self.center_to,
                items=[{"unit": other_unit}],
                created_by=self.user,
            )


class MovementAPITestCase(TestCase):
    """
    Tests d'intégration des endpoints REST de traçabilité (MV-01 à MV-03).
    Vérification des droits côté serveur (Règle 5) et formats d'échange.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="+2250700000003",
            full_name="Aya Touré",
            password="testpassword123",
        )
        self.receiver = User.objects.create_user(
            phone="+2250700000004",
            full_name="Koffi Bamba",
            password="testpassword123",
        )
        self.zone = Zone.objects.create(code="DAL", name="Daloa", level=1)
        self.center_from = Center.objects.create(
            name="Élevage Daloa 1",
            zone=self.zone,
            center_type="farm",
            created_by=self.user,
        )
        self.center_to = Center.objects.create(
            name="Marché Daloa",
            zone=self.zone,
            center_type="market",
            created_by=self.user,
        )
        # L'API de mouvement vérifie explicitement l'accès au centre d'origine.
        add_center_member(self.center_from, self.user, "holder")
        add_center_member(self.center_to, self.receiver, "holder")
        self.species = Species.objects.create(
            code="goat",
            label_fr="Caprins",
            tracking_mode="animal",
        )
        self.unit = TrackedUnit.objects.create(
            kind="animal",
            species=self.species,
            current_center=self.center_from,
            created_by=self.user,
        )

    def test_api_declare_movement_unauthenticated_rejected(self):
        """Règle 5 : Rejet 401 sur toute requête non authentifiée."""
        payload = {
            "from_center_id": str(self.center_from.id),
            "to_center_id": str(self.center_to.id),
            "movement_type": "transfer",
            "items": [{"unit_id": str(self.unit.id), "quantity_sent": 1}],
        }
        response = self.client.post("/api/movements/", payload, format="json")
        self.assertEqual(response.status_code, 401)

    def test_api_declare_movement_authenticated_success(self):
        """MV-01 : Création réussie via POST /api/movements/ avec 201 Created."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "from_center_id": str(self.center_from.id),
            "to_center_id": str(self.center_to.id),
            "movement_type": "transfer",
            "to_party_note": "Acheteur local",
            "items": [{"unit_id": str(self.unit.id), "quantity_sent": 1}],
        }
        response = self.client.post("/api/movements/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "declared")
        self.assertIn("confirmation_code", response.data)
        self.assertEqual(len(response.data["items"]), 1)

    def test_api_transfer_requires_registered_destination(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/movements/",
            {
                "from_center_id": str(self.center_from.id),
                "movement_type": "transfer",
                "to_party_note": "Élevage voisin",
                "items": [{"unit_id": str(self.unit.id), "quantity_sent": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("to_center_id", response.data)

    def test_destination_share_code_is_scoped_and_exposes_minimal_data(self):
        self.client.force_authenticate(user=self.user)
        denied = self.client.post(
            "/api/movements/destination-code/",
            {"center_id": str(self.center_to.id)},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(user=self.receiver)
        shared = self.client.post(
            "/api/movements/destination-code/",
            {"center_id": str(self.center_to.id)},
            format="json",
        )
        self.assertEqual(shared.status_code, 200)
        self.assertEqual(shared.data["expires_in_days"], 30)

        self.client.force_authenticate(user=self.user)
        resolved = self.client.get(
            "/api/movements/destination-code/",
            {"code": shared.data["code"]},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(
            resolved.data,
            {"center_id": str(self.center_to.id), "center_name": self.center_to.name},
        )

        invalid = self.client.get(
            "/api/movements/destination-code/", {"code": "not-a-signed-code"}
        )
        self.assertEqual(invalid.status_code, 400)

    def test_api_receiver_confirms_movement_and_unit_changes_center(self):
        """MV-04/05 : le destinataire confirme avec son compte et localise l'animal."""
        movement_id = uuid.uuid4()
        self.client.force_authenticate(user=self.user)
        declaration = self.client.post(
            "/api/movements/",
            {
                "id": str(movement_id),
                "from_center_id": str(self.center_from.id),
                "to_center_id": str(self.center_to.id),
                "movement_type": "transfer",
                "items": [{"unit_id": str(self.unit.id), "quantity_sent": 1}],
            },
            format="json",
        )
        self.assertEqual(declaration.status_code, 201)

        self.client.force_authenticate(user=self.receiver)
        confirmation_payload = {
            "id": str(uuid.uuid4()),
            "center_id": str(self.center_to.id),
            "code": declaration.data["confirmation_code"],
        }
        confirmation = self.client.post(
            f"/api/movements/{movement_id}/confirm/",
            confirmation_payload,
            format="json",
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(confirmation.data["status"], "confirmed")

        self.unit.refresh_from_db()
        self.assertEqual(self.unit.current_center_id, self.center_to.id)
        self.assertFalse(UnitOpenMovement.objects.filter(unit=self.unit).exists())
        self.assertEqual(
            set(MovementConfirmation.objects.filter(movement_id=movement_id).values_list("side", flat=True)),
            {"sender", "receiver"},
        )

        retry = self.client.post(
            f"/api/movements/{movement_id}/confirm/",
            confirmation_payload,
            format="json",
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(
            MovementConfirmation.objects.filter(movement_id=movement_id, side="receiver").count(),
            1,
        )

    def test_api_declare_movement_already_locked_returns_409(self):
        """MV-02 : Tentative de double mouvement renvoie un code HTTP 409 Conflict."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "from_center_id": str(self.center_from.id),
            "to_center_id": str(self.center_to.id),
            "movement_type": "transfer",
            "items": [{"unit_id": str(self.unit.id), "quantity_sent": 1}],
        }
        res1 = self.client.post("/api/movements/", payload, format="json")
        self.assertEqual(res1.status_code, 201)

        # Deuxième tentative avec la même unité
        res2 = self.client.post("/api/movements/", payload, format="json")
        self.assertEqual(res2.status_code, 409)
        self.assertIn("engag", res2.data["detail"])


