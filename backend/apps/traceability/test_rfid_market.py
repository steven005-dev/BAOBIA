"""Guide de réalisation des ajouts (21/11) : boucle RFID (1), scan au marché (2), animal
déclaré disparu vu au marché (3), parcours de l'animal (4), bilan du marché (5)."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import Center, Label
from apps.identity.services import (
    add_center_member,
    create_label_batch,
    register_animal,
)
from apps.notifications.models import Notification
from apps.traceability.models import MarketScan, Movement, RfidTag
from apps.traceability.services import (
    declare_rfid_lost,
    format_rfid,
    normalize_rfid,
    record_unit_event,
)

User = get_user_model()
TAG_A, TAG_B, TAG_D = "384000000000101", "384000000000102", "384000000000104"


class NumberFormatTests(TestCase):
    def test_normalize_and_format(self):
        self.assertEqual(normalize_rfid("384 000 000 000 028"), "384000000000028")
        self.assertIsNone(normalize_rfid("38400000000002"))     # 14 chiffres
        self.assertIsNone(normalize_rfid("3840000000000281"))   # 16 chiffres
        self.assertEqual(format_rfid("384000000000028"), "384 000 000 000 028")


class Base(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(phone="+2250700000031", full_name="Éleveur A",
                                               password="testpassword123")
        self.buyer = User.objects.create_user(phone="+2250700000032", full_name="Éleveur B",
                                              password="testpassword123")
        self.manager = User.objects.create_user(phone="+2250700000033", full_name="Gestionnaire",
                                                password="testpassword123")
        self.outsider = User.objects.create_user(phone="+2250700000034", full_name="Tiers",
                                                 password="testpassword123")
        self.north = Zone.objects.create(code="PORO", name="Poro", level=1)
        self.south = Zone.objects.create(code="GBEKE", name="Gbêkê", level=1)
        self.farm = Center.objects.create(name="Élevage Koné", zone=self.north,
                                          center_type="farm", created_by=self.farmer)
        self.other_farm = Center.objects.create(name="Élevage Yao", zone=self.south,
                                                center_type="farm", created_by=self.buyer)
        self.market = Center.objects.create(name="Marché de Korhogo", zone=self.north,
                                            center_type="market", created_by=self.manager)
        add_center_member(self.farm, self.farmer, "holder")
        add_center_member(self.other_farm, self.buyer, "holder")
        add_center_member(self.market, self.manager, "holder")
        self.cattle = Species.objects.create(code="cattle", label_fr="Bovin", tracking_mode="animal")
        batch = create_label_batch(quantity=4, created_by=self.manager)
        self.labels = list(Label.objects.filter(batch=batch).order_by("short_code"))
        self.cows = [
            register_animal(species=self.cattle, center=self.farm, created_by=self.farmer,
                            label=label, sex="female", local_name=f"Vache {i}")
            for i, label in enumerate(self.labels[:3], start=1)
        ]

    def post(self, user, path, body):
        self.client.force_authenticate(user=user)
        return self.client.post(path, body, format="json")

    def get(self, user, path, params=None):
        self.client.force_authenticate(user=user)
        return self.client.get(path, params or {})

    def bind(self, cow, number, user=None, tag_id=None, mode="manual_entry"):
        return self.post(user or self.farmer, "/api/rfid-tags/", {
            "id": str(tag_id or uuid.uuid4()), "unit_id": str(cow.id), "number": number,
            "read_mode": mode,
        })

    def scan(self, code, direction="in", user=None, scan_id=None, **extra):
        return self.post(user or self.manager, f"/api/markets/{self.market.id}/scans/", {
            "id": str(scan_id or uuid.uuid4()), "direction": direction, "code": code, **extra,
        })


class RfidTagTests(Base):
    def test_bind_formats_number_and_replays(self):
        tag_id = uuid.uuid4()
        first = self.bind(self.cows[0], "384 000 000 000 101", tag_id=tag_id)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["number"], "384 000 000 000 101")
        self.assertEqual(first.data["warnings"], [])
        self.assertEqual(self.bind(self.cows[0], TAG_A, tag_id=tag_id).status_code, 200)
        self.assertEqual(RfidTag.objects.count(), 1)

    def test_same_active_number_is_refused_without_saying_where(self):
        self.bind(self.cows[0], TAG_A)
        second = self.bind(self.cows[1], TAG_A)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["detail"], "Cette boucle est déjà liée à un autre animal.")
        self.assertNotIn("Vache", str(second.data))

    def test_lost_tag_frees_its_number_and_history_stays(self):
        self.bind(self.cows[0], TAG_A)
        declare_rfid_lost(tag=RfidTag.objects.get(number=TAG_A), created_by=self.farmer)
        self.assertEqual(self.bind(self.cows[1], TAG_A).status_code, 201)
        self.assertEqual(RfidTag.objects.filter(number=TAG_A).count(), 2)  # rien ne s'efface

    def test_new_tag_replaces_the_old_one_and_foreign_prefix_warns(self):
        self.bind(self.cows[0], TAG_A)
        response = self.bind(self.cows[0], "900 000 000 000 555")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["warnings"], ["check_number"])
        self.assertEqual(RfidTag.objects.get(number=TAG_A).status, "replaced")

    def test_rules(self):
        self.assertEqual(self.bind(self.cows[0], "12345").status_code, 400)
        self.assertEqual(self.bind(self.cows[0], TAG_A, user=self.outsider).status_code, 403)


class MarketScanTests(Base):
    def setUp(self):
        super().setUp()
        self.bind(self.cows[0], TAG_A)
        self.bind(self.cows[1], TAG_B)

    def test_scan_by_tag_or_baobia_code_finds_the_same_animal(self):
        by_tag = self.scan("384 000 000 000 101")
        self.assertEqual(by_tag.status_code, 201, by_tag.data)
        self.assertEqual(by_tag.data["result"], "ok")
        self.assertEqual(by_tag.data["animal"]["label"], "Bovin · femelle")
        self.assertEqual(by_tag.data["animal"]["tag"], "384 000 000 000 101")
        self.assertEqual(by_tag.data["movement"]["confidence"], "one_side")
        by_code = self.scan(self.labels[1].short_code)
        self.assertEqual(by_code.data["animal"]["id"], str(self.cows[1].id))
        self.cows[0].refresh_from_db()
        self.assertEqual(self.cows[0].current_center_id, self.market.id)

    def test_same_scan_id_twice_creates_one_movement_and_rescan_is_flagged(self):
        scan_id = uuid.uuid4()
        self.scan(TAG_A, scan_id=scan_id)
        replay = self.scan(TAG_A, scan_id=scan_id)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(Movement.objects.filter(to_center=self.market).count(), 1)
        again = self.scan(TAG_A)
        self.assertEqual(again.data["result"], "already_scanned")
        self.assertEqual(Movement.objects.filter(to_center=self.market).count(), 1)

    def test_unknown_code_is_kept_and_does_not_block(self):
        unknown = self.scan("384 000 000 000 999")
        self.assertEqual(unknown.status_code, 201)
        self.assertEqual(unknown.data["result"], "unknown")
        self.assertIsNone(unknown.data["animal"])
        self.assertEqual(self.scan(TAG_A).data["result"], "ok")

    def test_exit_to_registered_farm_or_out_of_system(self):
        self.scan(TAG_A)
        self.scan(TAG_B)
        out = self.scan(TAG_A, direction="out", to_center_id=str(self.other_farm.id))
        self.assertEqual(out.data["result"], "ok")
        self.assertEqual(out.data["movement"]["confidence"], "one_side")
        gone = self.scan(TAG_B, direction="out")
        self.assertEqual(gone.data["result"], "ok")
        self.cows[1].refresh_from_db()
        self.assertIsNone(self.cows[1].current_center_id)  # sorti du système

    def test_exit_of_an_animal_not_at_the_market_is_refused_but_kept(self):
        refused = self.scan(TAG_A, direction="out")
        self.assertEqual(refused.data["result"], "refused")
        self.assertEqual(MarketScan.objects.filter(result="refused").count(), 1)

    def test_user_without_rights_on_the_market_gets_403(self):
        self.assertEqual(self.scan(TAG_A, user=self.outsider).status_code, 403)
        self.assertEqual(self.scan(TAG_A, user=self.farmer).status_code, 403)

    def test_position_is_kept(self):
        self.scan(TAG_A, latitude="9.507000", longitude="-7.568000", position_accuracy_m="12.0",
                  position_source="gps")
        scan = MarketScan.objects.get()
        self.assertEqual((str(scan.latitude), scan.position_source), ("9.507000", "gps"))


class DeclaredMissingTests(Base):
    def test_declared_missing_animal_seen_at_market(self):
        cow = self.cows[2]
        self.bind(cow, TAG_D)
        record_unit_event(unit_id=cow.id, center_id=self.farm.id, event_type="missing",
                          created_by=self.farmer, event_id=uuid.uuid4())
        response = self.scan(TAG_D)
        self.assertEqual(response.data["result"], "ok")  # le passage est quand même gardé
        self.assertEqual(response.data["warnings"][0]["code"], "declared_missing")
        text = str(response.data)
        for forbidden in ("Koné", "Éleveur A", "volé", "vol "):
            self.assertNotIn(forbidden, text)
        self.assertTrue(AuditLog.objects.filter(action="declared_missing_seen").exists())
        note = Notification.objects.get(user=self.farmer, message_code="declared_missing.seen")
        self.assertNotIn("Korhogo", str(note.params))
        # Déclaration levée (animal retrouvé) : plus d'avertissement.
        self.scan(TAG_D, direction="out")
        cow.refresh_from_db()
        self.assertIsNone(cow.current_center_id)

    def test_found_lifts_the_warning(self):
        cow = self.cows[2]
        self.bind(cow, TAG_D)
        record_unit_event(unit_id=cow.id, center_id=self.farm.id, event_type="missing",
                          created_by=self.farmer, event_id=uuid.uuid4())
        record_unit_event(unit_id=cow.id, center_id=self.farm.id, event_type="found",
                          created_by=self.farmer, event_id=uuid.uuid4(),
                          occurred_at=timezone.now() + timedelta(seconds=1))
        self.assertEqual(self.scan(TAG_D).data["warnings"], [])


class RouteTests(Base):
    def test_route_shows_confidence_and_hides_farm_names_without_access(self):
        self.bind(self.cows[0], TAG_A)
        self.scan(TAG_A)
        self.scan(TAG_A, direction="out", to_center_id=str(self.other_farm.id))
        owner = self.get(self.farmer, f"/api/units/{self.cows[0].id}/route/")
        self.assertEqual(owner.status_code, 404)  # l'animal a quitté son élevage

        manager = self.get(self.manager, f"/api/units/{self.cows[0].id}/route/")
        self.assertEqual(manager.status_code, 200, manager.data)
        self.assertEqual(manager.data["rfid"]["number"], "384 000 000 000 101")
        steps = manager.data["steps"]
        self.assertEqual([s["confidence_label"] for s in steps], ["Probable", "Probable"])
        entry = steps[1]
        self.assertEqual(entry["to"]["label"], "Marché de Korhogo")
        self.assertEqual(entry["from"]["label"], "Élevage")  # pas le nom de l'élevage
        self.assertEqual(entry["from"]["zone"], "Poro")
        self.assertEqual(entry["declared_by"], "receiver")

    def test_route_is_hidden_from_strangers(self):
        self.assertEqual(self.get(self.outsider, f"/api/units/{self.cows[0].id}/route/").status_code, 404)


class SummaryTests(Base):
    def test_summary_counts_and_groups_small_zones(self):
        extra = [
            register_animal(species=self.cattle, center=self.farm, created_by=self.farmer,
                            label=None, local_name=f"Bovin {i}")
            for i in range(5)
        ]
        for i, cow in enumerate(extra):
            self.bind(cow, f"3840000000002{i:02d}")
            self.scan(f"3840000000002{i:02d}")
        far = register_animal(species=self.cattle, center=self.other_farm, created_by=self.buyer,
                              label=None, local_name="Bovin du sud")
        self.post(self.buyer, "/api/rfid-tags/", {"id": str(uuid.uuid4()), "unit_id": str(far.id),
                                                 "number": "384000000000300",
                                                 "read_mode": "manual_entry"})
        self.scan("384000000000300")
        self.scan("384000000000999")  # inconnu

        response = self.get(self.manager, f"/api/markets/{self.market.id}/summary/")
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual((data["entered"], data["left"], data["unknown"], data["warnings"]),
                         (6, 0, 1, 0))
        self.assertEqual(data["by_origin_zone"], [{"zone": "Poro", "count": 5},
                                                  {"zone": "Autres zones", "count": 1}])
        self.assertNotIn("Élevage", str(data))
        self.assertEqual(self.get(self.outsider, f"/api/markets/{self.market.id}/summary/").status_code, 404)


class RescanOfDeclaredAnimalTests(Base):
    def test_rescan_keeps_the_warning_but_sends_no_new_message(self):
        cow = self.cows[2]
        self.bind(cow, TAG_D)
        record_unit_event(unit_id=cow.id, center_id=self.farm.id, event_type="stolen_declared",
                          created_by=self.farmer, event_id=uuid.uuid4())
        self.scan(TAG_D)
        again = self.scan(TAG_D)
        self.assertEqual(again.data["result"], "already_scanned")
        self.assertEqual(again.data["warnings"][0]["code"], "declared_missing")
        self.assertEqual(Notification.objects.filter(message_code="declared_missing.seen",
                                                     user=self.farmer).count(), 1)
        summary = self.get(self.manager, f"/api/markets/{self.market.id}/summary/").data
        self.assertEqual(summary["warnings"], 1)  # un animal, pas deux scans
