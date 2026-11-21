"""Passage au marché (R2, spec v1.4 9.11) et verrou levé après le délai (Q2).

Décisions du chef de projet (21/11) : le marché déclare seul l'entrée, sans code (Q1) ;
le verrou d'un départ « probable » se lève après 72 h (Q2) ; une sortie vers un acheteur
non inscrit est close tout de suite, « sorti du système » (Q3).
"""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import Center, Label
from apps.identity.services import (
    add_center_member,
    create_label_batch,
    grant_mandate,
    register_animal,
)
from apps.traceability.models import Movement, UnitOpenMovement
from apps.traceability.services import (
    OUT_OF_SYSTEM_REASON,
    movements_for_exposure,
    release_stale_locks,
)

User = get_user_model()


class MarketBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(phone="+2250700000021", full_name="Éleveur A",
                                               password="testpassword123")
        self.buyer = User.objects.create_user(phone="+2250700000022", full_name="Éleveur B",
                                              password="testpassword123")
        self.manager = User.objects.create_user(phone="+2250700000023", full_name="Gestionnaire",
                                                password="testpassword123")
        self.agent = User.objects.create_user(phone="+2250700000024", full_name="Agent marché",
                                              password="testpassword123")
        zone = Zone.objects.create(code="KHG", name="Korhogo", level=1)
        self.farm = Center.objects.create(name="Élevage A", zone=zone, center_type="farm",
                                          created_by=self.farmer)
        self.other_farm = Center.objects.create(name="Élevage B", zone=zone, center_type="farm",
                                                created_by=self.buyer)
        self.market = Center.objects.create(name="Marché de Korhogo", zone=zone,
                                            center_type="market", created_by=self.manager)
        add_center_member(self.farm, self.farmer, "holder")
        add_center_member(self.other_farm, self.buyer, "holder")
        add_center_member(self.market, self.manager, "holder")
        grant_mandate(self.agent, self.manager, [self.market], "move")
        cattle = Species.objects.create(code="cattle", label_fr="Bovins", tracking_mode="animal")
        batch = create_label_batch(quantity=3, created_by=self.manager)
        labels = list(Label.objects.filter(batch=batch).order_by("short_code"))
        self.codes = [label.short_code for label in labels]
        self.cows = [
            register_animal(species=cattle, center=self.farm, created_by=self.farmer,
                            label=label, local_name=f"Vache {i}")
            for i, label in enumerate(labels, start=1)
        ]

    def post(self, user, path, body):
        self.client.force_authenticate(user=user)
        return self.client.post(path, body, format="json")

    def enter(self, user=None, codes=None, entry_id=None):
        return self.post(user or self.manager, "/api/market/entries/", {
            "id": str(entry_id or uuid.uuid4()), "market_id": str(self.market.id),
            "label_codes": codes or self.codes[:2],
        })


class MarketEntryTests(MarketBase):
    def test_market_declares_entry_alone_and_animals_count_at_market(self):
        response = self.enter()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["movements"]), 2)
        for data in response.data["movements"]:
            self.assertEqual(data["status"], "declared")  # « probable » : l'origine n'a rien dit
            self.assertEqual(data["from_center"], self.farm.id)
            self.assertEqual(data["to_center"], self.market.id)
        for cow in self.cows[:2]:
            cow.refresh_from_db()
            self.assertEqual(cow.current_center_id, self.market.id)
            self.assertFalse(UnitOpenMovement.objects.filter(unit=cow).exists())
        confidences = {m.confidence for m in movements_for_exposure(from_center_ids=[self.farm.id])}
        self.assertEqual(confidences, {"one_side"})

    def test_agent_with_move_mandate_entry_is_assisted(self):
        response = self.enter(user=self.agent)
        self.assertEqual(response.status_code, 201, response.data)
        receiver = next(c for c in response.data["movements"][0]["confirmations"]
                        if c["side"] == "receiver")
        self.assertEqual(receiver["mode"], "assisted")

    def test_replay_is_idempotent_and_reuse_is_a_conflict(self):
        entry_id = uuid.uuid4()
        self.assertEqual(self.enter(entry_id=entry_id).status_code, 201)
        replay = self.enter(entry_id=entry_id)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(Movement.objects.count(), 2)
        self.assertEqual(self.enter(entry_id=entry_id, codes=self.codes[2:]).status_code, 409)

    def test_rules(self):
        self.assertEqual(self.enter(user=self.farmer).status_code, 403)
        self.assertEqual(self.enter(codes=["ZZZZZZZZZ"]).status_code, 400)
        self.assertEqual(self.enter(codes=[self.codes[0], self.codes[0]]).status_code, 400)
        response = self.post(self.farmer, "/api/market/entries/", {
            "id": str(uuid.uuid4()), "market_id": str(self.farm.id), "label_codes": self.codes[:1],
        })
        self.assertEqual(response.status_code, 400)  # un élevage n'est pas un marché
        self.enter(codes=self.codes[:1])
        self.assertEqual(self.enter(codes=self.codes[:1]).status_code, 400)  # déjà au marché
        self.assertEqual(Movement.objects.count(), 1)


class MarketExitTests(MarketBase):
    def setUp(self):
        super().setUp()
        self.enter()

    def exit(self, **extra):
        return self.post(self.manager, "/api/market/exits/", {
            "id": str(extra.pop("exit_id", uuid.uuid4())), "market_id": str(self.market.id),
            "label_codes": extra.pop("codes", self.codes[:1]), **extra,
        })

    def test_exit_to_registered_farm_is_a_normal_departure_with_code(self):
        response = self.exit(to_center_id=str(self.other_farm.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertRegex(response.data["confirmation_code"], r"^\d{6}$")
        self.assertFalse(response.data["out_of_system"])
        self.assertEqual(response.data["status"], "declared")
        self.assertTrue(UnitOpenMovement.objects.filter(unit=self.cows[0]).exists())

        self.client.force_authenticate(user=self.buyer)
        confirmed = self.client.post(f"/api/movements/{response.data['id']}/confirm/", {
            "center_id": str(self.other_farm.id), "code": response.data["confirmation_code"],
        }, format="json")
        self.assertEqual(confirmed.data["status"], "confirmed")
        self.cows[0].refresh_from_db()
        self.assertEqual(self.cows[0].current_center_id, self.other_farm.id)

    def test_exit_to_unregistered_buyer_is_closed_at_once(self):
        response = self.exit(to_party_note="Acheteur de Bouaké")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["out_of_system"])
        self.assertIsNone(response.data["confirmation_code"])
        self.cows[0].refresh_from_db()
        self.assertIsNone(self.cows[0].current_center_id)
        self.assertFalse(UnitOpenMovement.objects.filter(unit=self.cows[0]).exists())
        reasons = [e["reason"] for e in response.data["status_events"]]
        self.assertIn(OUT_OF_SYSTEM_REASON, reasons)
        # Retrouvable dans l'historique du marché.
        self.client.force_authenticate(user=self.manager)
        history = self.client.get("/api/movements/", {"center_id": str(self.market.id)})
        self.assertIn(response.data["id"], [m["id"] for m in history.data])

    def test_exit_rules(self):
        self.assertEqual(self.exit().status_code, 400)  # ni acheteur inscrit ni description
        self.assertEqual(self.exit(codes=self.codes[2:], to_party_note="X").status_code, 400)
        exit_id = uuid.uuid4()
        first = self.exit(exit_id=exit_id, to_center_id=str(self.other_farm.id))
        replay = self.exit(exit_id=exit_id, to_center_id=str(self.other_farm.id))
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertRegex(replay.data["confirmation_code"], r"^\d{6}$")
        self.assertEqual(self.exit(exit_id=exit_id, to_party_note="Autre").status_code, 409)


class StaleLockTests(MarketBase):
    """Q2 : un verrou de départ « probable » se lève après 72 h ; le mouvement reste."""

    def declare(self, cow, to_center):
        response = self.post(self.farmer, "/api/movements/", {
            "id": str(uuid.uuid4()), "from_center_id": str(self.farm.id),
            "to_center_id": str(to_center.id), "movement_type": "sale",
            "items": [{"unit_id": str(cow.id), "quantity_sent": 1}],
        })
        return response

    def age_lock(self, cow, hours):
        UnitOpenMovement.objects.filter(unit=cow).update(since=timezone.now() - timedelta(hours=hours))

    def test_lock_holds_before_the_delay(self):
        self.assertEqual(self.declare(self.cows[2], self.other_farm).status_code, 201)
        self.age_lock(self.cows[2], 71)
        self.assertEqual(self.declare(self.cows[2], self.market).status_code, 409)

    def test_lock_is_released_after_72_hours_and_movement_stays_probable(self):
        first = self.declare(self.cows[2], self.other_farm)
        self.age_lock(self.cows[2], 73)
        second = self.declare(self.cows[2], self.market)
        self.assertEqual(second.status_code, 201, second.data)
        stale = Movement.objects.get(pk=first.data["id"])
        self.assertEqual(stale.status, "declared")
        self.assertIn(str(stale.pk), {str(m.pk) for m in
                                      movements_for_exposure(from_center_ids=[self.farm.id])})
        self.assertTrue(AuditLog.objects.filter(action="movement.lock_released",
                                                entity_id=stale.pk).exists())
        # La confirmation tardive du premier acheteur ne déplace pas l'animal en silence.
        self.client.force_authenticate(user=self.buyer)
        late = self.client.post(f"/api/movements/{stale.pk}/confirm/", {
            "center_id": str(self.other_farm.id), "code": first.data["confirmation_code"],
        }, format="json")
        self.assertEqual(late.status_code, 409)

    @override_settings(MOVEMENT_LOCK_HOURS=1)
    def test_delay_comes_from_settings(self):
        self.declare(self.cows[2], self.other_farm)
        self.age_lock(self.cows[2], 2)
        self.assertEqual(release_stale_locks([self.cows[2].id]), 1)
        self.assertFalse(UnitOpenMovement.objects.filter(unit=self.cows[2]).exists())
