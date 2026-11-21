"""Cycle de vie d'un mouvement : confirmation assistée (MV-04), rapprochement (MV-06),
refus, annulation (MV-05), contestation (MV-09), événements de vie (MV-02), confiance des
mouvements pour l'exposition (R1, spec v1.4)."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import Center, TrackedUnit
from apps.identity.services import add_center_member, grant_mandate, register_lot
from apps.traceability.models import (
    Movement,
    MovementConfirmation,
    MovementDiscrepancy,
    StatusEvent,
    UnitOpenMovement,
)
from apps.traceability import services
from apps.traceability.services import movements_for_exposure

User = get_user_model()


class LifecycleBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(phone="+2250700000011", full_name="Vendeur",
                                               password="testpassword123")
        self.buyer = User.objects.create_user(phone="+2250700000012", full_name="Acheteur",
                                              password="testpassword123")
        self.agent = User.objects.create_user(phone="+2250700000013", full_name="Agent",
                                              password="testpassword123")
        self.outsider = User.objects.create_user(phone="+2250700000014", full_name="Tiers",
                                                 password="testpassword123")
        zone = Zone.objects.create(code="BKE", name="Bouaké", level=1)
        self.origin = Center.objects.create(name="Élevage A", zone=zone, center_type="farm",
                                            created_by=self.seller)
        self.dest = Center.objects.create(name="Élevage B", zone=zone, center_type="farm",
                                          created_by=self.buyer)
        add_center_member(self.origin, self.seller, "holder")
        add_center_member(self.dest, self.buyer, "holder")
        grant_mandate(self.agent, self.buyer, [self.dest], "all")
        self.cattle = Species.objects.create(code="cattle", label_fr="Bovins",
                                             tracking_mode="animal")
        self.poultry = Species.objects.create(code="poultry", label_fr="Volailles",
                                              tracking_mode="lot")
        self.cow = TrackedUnit.objects.create(kind="animal", species=self.cattle,
                                              current_center=self.origin, created_by=self.seller)
        self.calf = TrackedUnit.objects.create(kind="animal", species=self.cattle,
                                               current_center=self.origin, created_by=self.seller)

    def declare(self, units, quantities=None):
        self.client.force_authenticate(user=self.seller)
        movement_id = uuid.uuid4()
        quantities = quantities or [1] * len(units)
        response = self.client.post("/api/movements/", {
            "id": str(movement_id),
            "from_center_id": str(self.origin.id),
            "to_center_id": str(self.dest.id),
            "movement_type": "sale",
            "items": [{"unit_id": str(u.id), "quantity_sent": q}
                      for u, q in zip(units, quantities)],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return movement_id, response.data["confirmation_code"]

    def confirm(self, user, movement_id, code, **extra):
        self.client.force_authenticate(user=user)
        return self.client.post(f"/api/movements/{movement_id}/confirm/", {
            "id": str(uuid.uuid4()), "center_id": str(self.dest.id), "code": code, **extra,
        }, format="json")

    def receiver_confirmation(self, data):
        return next(c for c in data["confirmations"] if c["side"] == "receiver")


class AssistedConfirmationTests(LifecycleBase):
    def test_buyer_confirmation_is_direct(self):
        movement_id, code = self.declare([self.cow])
        response = self.confirm(self.buyer, movement_id, code)
        self.assertEqual(response.status_code, 200)
        receiver = self.receiver_confirmation(response.data)
        self.assertEqual(receiver["mode"], "direct")
        self.assertEqual(receiver["entered_by_name"], "Acheteur")
        sender = next(c for c in response.data["confirmations"] if c["side"] == "sender")
        self.assertEqual(sender["mode"], "direct")

    def test_agent_confirmation_is_recorded_and_shown_as_assisted(self):
        movement_id, code = self.declare([self.cow])
        response = self.confirm(self.agent, movement_id, code)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "confirmed")
        receiver = self.receiver_confirmation(response.data)
        self.assertEqual(receiver["mode"], "assisted")
        self.assertEqual(receiver["entered_by_name"], "Agent")
        log = AuditLog.objects.filter(action="movement.confirm_receipt",
                                      entity_id=movement_id).get()
        self.assertEqual(log.details["mode"], "assisted")
        reason = Movement.objects.get(pk=movement_id).status_events.get(status="confirmed").reason
        self.assertIn("avec l'aide d'un agent", reason)

    def test_outsider_cannot_confirm(self):
        movement_id, code = self.declare([self.cow])
        response = self.confirm(self.outsider, movement_id, code)
        self.assertEqual(response.status_code, 403)


class ReconciliationTests(LifecycleBase):
    def test_full_receipt_without_detail_is_confirmed(self):
        movement_id, code = self.declare([self.cow, self.calf])
        response = self.confirm(self.buyer, movement_id, code)
        self.assertEqual(response.data["status"], "confirmed")
        self.assertEqual(response.data["discrepancies"], [])

    def test_missing_animal_is_flagged_and_stays_at_origin(self):
        movement_id, code = self.declare([self.cow, self.calf])
        response = self.confirm(self.buyer, movement_id, code, items_received=[
            {"unit_id": str(self.calf.id), "quantity_received": 0},
        ])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "partial")
        self.assertEqual(self.receiver_confirmation(response.data)["decision"],
                         "confirm_with_discrepancy")
        discrepancy = MovementDiscrepancy.objects.get(movement_id=movement_id)
        self.assertEqual((discrepancy.kind, discrepancy.quantity_expected,
                          discrepancy.quantity_found), ("missing", 1, 0))
        self.cow.refresh_from_db()
        self.calf.refresh_from_db()
        self.assertEqual(self.cow.current_center_id, self.dest.id)
        self.assertEqual(self.calf.current_center_id, self.origin.id)
        self.assertFalse(UnitOpenMovement.objects.filter(movement_id=movement_id).exists())
        reason = Movement.objects.get(pk=movement_id).status_events.get(status="partial").reason
        self.assertIn("1 reçus sur 2", reason)

    def test_lot_count_mismatch_five_sent_four_received(self):
        lot = register_lot(species=self.poultry, center=self.origin, size=5,
                           created_by=self.seller)
        movement_id, code = self.declare([lot], quantities=[5])
        response = self.confirm(self.buyer, movement_id, code, items_received=[
            {"unit_id": str(lot.id), "quantity_received": 4},
        ])
        self.assertEqual(response.data["status"], "partial")
        discrepancy = response.data["discrepancies"][0]
        self.assertEqual((discrepancy["kind"], discrepancy["quantity_expected"],
                          discrepancy["quantity_found"]), ("count_mismatch", 5, 4))

    def test_unknown_unit_or_double_animal_is_rejected_without_effect(self):
        movement_id, code = self.declare([self.cow])
        unknown = self.confirm(self.buyer, movement_id, code, items_received=[
            {"unit_id": str(self.calf.id), "quantity_received": 1},
        ])
        self.assertEqual(unknown.status_code, 400)
        twice = self.confirm(self.buyer, movement_id, code, items_received=[
            {"unit_id": str(self.cow.id), "quantity_received": 2},
        ])
        self.assertEqual(twice.status_code, 400)
        movement = Movement.objects.get(pk=movement_id)
        self.assertEqual(movement.status, "declared")
        self.assertFalse(movement.confirmations.filter(side="receiver").exists())


class RefuseCancelContestTests(LifecycleBase):
    def post(self, user, movement_id, action, center, reason="Bêtes non conformes"):
        self.client.force_authenticate(user=user)
        return self.client.post(f"/api/movements/{movement_id}/{action}/", {
            "center_id": str(center.id), "reason": reason,
        }, format="json")

    def test_receiver_refusal_disputes_and_keeps_units_at_origin(self):
        movement_id, code = self.declare([self.cow])
        response = self.post(self.buyer, movement_id, "refuse", self.dest)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "disputed")
        self.assertEqual(self.receiver_confirmation(response.data)["decision"], "refuse")
        self.cow.refresh_from_db()
        self.assertEqual(self.cow.current_center_id, self.origin.id)
        self.assertFalse(UnitOpenMovement.objects.filter(unit=self.cow).exists())
        # Le code ne permet plus de confirmer ensuite ; rejouer le refus est sans effet.
        self.assertEqual(self.confirm(self.buyer, movement_id, code).data["status"], "disputed")
        self.assertEqual(self.post(self.buyer, movement_id, "refuse", self.dest).status_code, 200)
        self.assertEqual(MovementConfirmation.objects.filter(movement_id=movement_id,
                                                             side="receiver").count(), 1)

    def test_refusal_requires_a_reason(self):
        movement_id, _ = self.declare([self.cow])
        self.assertEqual(self.post(self.buyer, movement_id, "refuse", self.dest,
                                   reason="").status_code, 400)

    def test_sender_cancels_before_receipt(self):
        movement_id, code = self.declare([self.cow])
        response = self.post(self.seller, movement_id, "cancel", self.origin, reason="Erreur")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertTrue(Movement.objects.filter(pk=movement_id).exists())  # jamais effacé
        self.assertFalse(UnitOpenMovement.objects.filter(unit=self.cow).exists())
        self.assertEqual(self.confirm(self.buyer, movement_id, code).status_code, 404)
        # L'animal peut repartir dans un nouveau départ.
        self.declare([self.cow])

    def test_receiver_cannot_cancel_and_received_movement_cannot_be_cancelled(self):
        movement_id, code = self.declare([self.cow])
        self.assertEqual(self.post(self.buyer, movement_id, "cancel", self.dest).status_code, 404)
        self.confirm(self.buyer, movement_id, code)
        self.assertEqual(self.post(self.seller, movement_id, "cancel", self.origin).status_code,
                         400)

    def test_either_party_contests_a_received_movement_without_moving_units(self):
        movement_id, code = self.declare([self.cow])
        self.assertEqual(self.post(self.seller, movement_id, "contest", self.origin)
                         .status_code, 400)  # pas encore reçu
        self.confirm(self.buyer, movement_id, code)
        response = self.post(self.seller, movement_id, "contest", self.origin,
                             reason="Paiement non reçu")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "disputed")
        statuses = [e["status"] for e in response.data["status_events"]]
        self.assertEqual(sorted(statuses), ["confirmed", "declared", "disputed"])
        self.cow.refresh_from_db()
        self.assertEqual(self.cow.current_center_id, self.dest.id)
        self.assertEqual(self.post(self.outsider, movement_id, "contest", self.origin)
                         .status_code, 403)


class ExposureConfidenceTests(LifecycleBase):
    """R1 / spec v1.4 : un mouvement déclaré d'un seul côté compte, avec sa confiance."""

    def confidences(self, **kwargs):
        return {str(m.pk): m.confidence
                for m in movements_for_exposure(from_center_ids=[self.origin.id], **kwargs)}

    def test_each_movement_carries_its_confidence(self):
        one_side, _ = self.declare([self.cow])
        sure, code = self.declare([self.calf])
        self.confirm(self.buyer, sure, code)
        self.assertEqual(self.confidences(),
                         {str(one_side): "one_side", str(sure): "confirmed"})
        self.assertEqual(self.confidences(include_one_side=False), {str(sure): "confirmed"})

    def test_disputed_counts_and_cancelled_does_not(self):
        disputed, _ = self.declare([self.cow])
        self.client.force_authenticate(user=self.buyer)
        self.client.post(f"/api/movements/{disputed}/refuse/",
                         {"center_id": str(self.dest.id), "reason": "Non conforme"}, format="json")
        cancelled, _ = self.declare([self.calf])
        self.client.force_authenticate(user=self.seller)
        self.client.post(f"/api/movements/{cancelled}/cancel/",
                         {"center_id": str(self.origin.id), "reason": "Erreur"}, format="json")
        self.assertEqual(self.confidences(), {str(disputed): "disputed"})

    def test_species_and_window_filters(self):
        movement_id, _ = self.declare([self.cow])
        self.assertIn(str(movement_id), self.confidences(species_id=self.cattle.id))
        self.assertEqual(self.confidences(species_id=self.poultry.id), {})
        self.assertEqual(self.confidences(since=timezone.now() + timedelta(days=1)), {})

    def test_one_side_departure_never_expires_on_its_own(self):
        self.assertFalse(hasattr(services, "expire_overdue_movements"))


class ClockTests(LifecycleBase):
    def test_future_phone_date_is_flagged(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post("/api/movements/", {
            "from_center_id": str(self.origin.id), "to_center_id": str(self.dest.id),
            "movement_type": "sale", "occurred_at": (timezone.now() + timedelta(days=2)).isoformat(),
            "items": [{"unit_id": str(self.cow.id), "quantity_sent": 1}],
        }, format="json")
        self.assertTrue(response.data["clock_suspect"])
        _, _ = self.declare([self.calf])
        normal = Movement.objects.exclude(pk=response.data["id"]).get()
        self.client.force_authenticate(user=self.seller)
        detail = self.client.get(f"/api/movements/{normal.id}/", {"center_id": str(self.origin.id)})
        self.assertFalse(detail.data["clock_suspect"])


class UnitEventTests(LifecycleBase):
    def post_event(self, user, event_type, unit=None, event_id=None, center=None):
        self.client.force_authenticate(user=user)
        return self.client.post("/api/unit-events/", {
            "id": str(event_id or uuid.uuid4()),
            "center_id": str((center or self.origin).id),
            "unit_id": str((unit or self.cow).id),
            "event_type": event_type,
        }, format="json")

    def test_death_is_recorded_once_and_replay_has_no_effect(self):
        event_id = uuid.uuid4()
        first = self.post_event(self.seller, "death", event_id=event_id)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["visibility"], "owner")
        self.assertEqual(self.post_event(self.seller, "death", event_id=event_id).status_code, 200)
        self.assertEqual(self.post_event(self.seller, "slaughter", event_id=event_id)
                         .status_code, 409)
        self.assertEqual(StatusEvent.objects.filter(unit=self.cow).count(), 1)

    def test_theft_is_restricted_to_professionals_and_its_author(self):
        add_center_member(self.origin, self.buyer, "worker")
        response = self.post_event(self.seller, "stolen_declared")
        self.assertEqual(response.data["visibility"], "professionals")
        self.client.force_authenticate(user=self.buyer)
        listing = self.client.get("/api/unit-events/", {"center_id": str(self.origin.id)})
        self.assertEqual(listing.data, [])
        self.client.force_authenticate(user=self.seller)
        listing = self.client.get("/api/unit-events/", {"center_id": str(self.origin.id)})
        self.assertEqual(len(listing.data), 1)

    def test_rules_unit_elsewhere_locked_or_no_access(self):
        self.assertEqual(self.post_event(self.seller, "death", center=self.dest).status_code, 403)
        self.assertEqual(self.post_event(self.buyer, "death", center=self.dest).status_code, 400)
        self.declare([self.cow])
        self.assertEqual(self.post_event(self.seller, "death").status_code, 409)
        self.assertEqual(self.post_event(self.seller, "birth").status_code, 400)
