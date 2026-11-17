"""API identity : élevages, animaux et lots, scan. Données simulées."""

import uuid

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.tests.helpers import (
    give_role,
    make_center,
    make_species,
    make_user,
    make_zone,
)
from apps.audit.models import AuditLog
from apps.geo.models import Zone
from apps.identity import services
from apps.identity.models import IdentitySupport, Label, TrackedUnit


class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.region = make_zone("TEST-REG")
        self.zone = Zone.objects.create(parent=self.region, level=2, code="TEST-DEP", name="Dép test")
        self.other_zone = make_zone("TEST-AUTRE")
        self.cattle = make_species("cattle", "animal")
        self.poultry = make_species("poultry", "lot")

        self.breeder = make_user("+2250000000101", "Éleveur test")
        give_role(self.breeder, "breeder")
        self.center = make_center(self.breeder, name="Élevage A", zone=self.zone)

        self.stranger = make_user("+2250000000102", "Autre éleveur")
        give_role(self.stranger, "breeder")
        self.stranger_center = make_center(self.stranger, name="Élevage B", zone=self.zone)

        batch = services.create_label_batch(quantity=3, created_by=self.breeder)
        self.labels = list(Label.objects.filter(batch=batch).order_by("short_code"))

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client


class CenterApiTests(ApiTestCase):
    def test_list_only_my_centers(self):
        resp = self.as_user(self.breeder).get("/api/centers/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([c["name"] for c in resp.json()], ["Élevage A"])
        self.assertEqual(resp.json()[0]["access"], "holder")

    def test_anonymous_refused(self):
        self.assertEqual(self.client.get("/api/centers/").status_code, 401)

    def test_create_center_makes_me_holder_and_is_idempotent(self):
        center_id = str(uuid.uuid4())
        body = {"id": center_id, "name": "Nouvel élevage", "zone_id": str(self.zone.id),
                "species_ids": [str(self.cattle.id)]}
        resp = self.as_user(self.breeder).post("/api/centers/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["species"][0]["code"], "cattle")
        self.assertTrue(services.user_can_access_center(self.breeder, center_id))

        again = self.client.post("/api/centers/", body, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action="center.create", entity_id=center_id).count(), 1)

    def test_create_center_id_of_someone_else_conflicts(self):
        body = {"id": str(self.stranger_center.id), "name": "X", "zone_id": str(self.zone.id)}
        resp = self.as_user(self.breeder).post("/api/centers/", body, format="json")
        self.assertEqual(resp.status_code, 409)

    def test_create_center_requires_breeder_or_trader(self):
        vet = make_user("+2250000000103", "Vétérinaire")
        give_role(vet, "veterinarian", zone=self.zone)
        body = {"name": "X", "zone_id": str(self.zone.id)}
        self.assertEqual(self.as_user(vet).post("/api/centers/", body, format="json").status_code, 403)

    def test_create_center_unknown_zone(self):
        body = {"name": "X", "zone_id": str(uuid.uuid4())}
        resp = self.as_user(self.breeder).post("/api/centers/", body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("zone_id", resp.json())

    def test_detail_counts_and_access(self):
        services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder)
        services.register_lot(species=self.poultry, center=self.center, size=40, created_by=self.breeder)
        resp = self.as_user(self.breeder).get(f"/api/centers/{self.center.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual((data["animals_count"], data["lots_count"], data["heads_count"]), (1, 1, 41))

        self.assertEqual(self.as_user(self.stranger).get(f"/api/centers/{self.center.id}/").status_code, 403)
        self.assertEqual(
            self.as_user(self.stranger).get(f"/api/centers/{self.center.id}/units/").status_code, 403
        )

    def test_units_list(self):
        services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder,
                                 label=self.labels[0])
        services.register_lot(species=self.poultry, center=self.center, size=12, created_by=self.breeder)
        resp = self.as_user(self.breeder).get(f"/api/centers/{self.center.id}/units/")
        self.assertEqual(resp.status_code, 200)
        by_kind = {u["kind"]: u for u in resp.json()}
        self.assertEqual(by_kind["animal"]["label_code"], self.labels[0].short_code)
        self.assertEqual(by_kind["lot"]["size"], 12)


class UnitApiTests(ApiTestCase):
    def post_unit(self, user, **body):
        body.setdefault("center_id", str(self.center.id))
        return self.as_user(user).post("/api/units/", body, format="json")

    def test_register_animal_with_label(self):
        code = self.labels[0].short_code
        spaced = f"{code[:3]} {code[3:6]}-{code[6:]}".lower()
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.cattle.id),
                              local_name="Blanchette", sex="female", label_code=spaced)
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["label_code"], code)
        self.assertEqual(data["current_center"]["id"], str(self.center.id))
        self.assertEqual(data["animal"]["sex"], "female")
        self.assertEqual(Label.objects.get(pk=self.labels[0].pk).status, "active")

    def test_register_lot_requires_size(self):
        resp = self.post_unit(self.breeder, kind="lot", species_id=str(self.poultry.id))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("size", resp.json())
        ok = self.post_unit(self.breeder, kind="lot", species_id=str(self.poultry.id), size=30)
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["lot"]["current_size"], 30)

    def test_tracking_mode_is_respected(self):
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.poultry.id))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(TrackedUnit.objects.count(), 0)

    def test_replay_same_id_has_no_effect(self):
        unit_id = str(uuid.uuid4())
        body = {"id": unit_id, "kind": "animal", "species_id": str(self.cattle.id)}
        self.assertEqual(self.post_unit(self.breeder, **body).status_code, 201)
        self.assertEqual(self.post_unit(self.breeder, **body).status_code, 200)
        self.assertEqual(TrackedUnit.objects.filter(pk=unit_id).count(), 1)

    def test_cannot_register_in_someone_elses_center(self):
        resp = self.post_unit(self.stranger, kind="animal", species_id=str(self.cattle.id))
        self.assertEqual(resp.status_code, 403)

    def test_label_already_used_rolls_back_everything(self):
        services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder,
                                 label=self.labels[0])
        before = TrackedUnit.objects.count()
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.cattle.id),
                              label_code=self.labels[0].short_code)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "Cette étiquette est déjà posée sur un autre animal.")
        self.assertEqual(TrackedUnit.objects.count(), before)

    def test_bad_check_character_refused(self):
        code = self.labels[0].short_code
        wrong = code[:-1] + ("2" if code[-1] != "2" else "3")
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.cattle.id), label_code=wrong)
        self.assertEqual(resp.status_code, 400)

    def test_label_issued_to_another_center_refused(self):
        services.issue_labels([self.labels[1]], self.stranger_center, issued_by=self.stranger)
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.cattle.id),
                              label_code=self.labels[1].short_code)
        self.assertEqual(resp.status_code, 400)

    def test_detail_visibility(self):
        unit = services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder)
        url = f"/api/units/{unit.id}/"
        self.assertEqual(self.as_user(self.breeder).get(url).status_code, 200)
        # Un autre éleveur ne sait même pas que l'animal existe.
        self.assertEqual(self.as_user(self.stranger).get(url).status_code, 404)

        vet_region = make_user("+2250000000104", "Vétérinaire région")
        give_role(vet_region, "veterinarian", zone=self.region)  # zone parente : couvert
        self.assertEqual(self.as_user(vet_region).get(url).status_code, 200)

        vet_elsewhere = make_user("+2250000000105", "Vétérinaire ailleurs")
        give_role(vet_elsewhere, "veterinarian", zone=self.other_zone)
        self.assertEqual(self.as_user(vet_elsewhere).get(url).status_code, 404)

        vet_no_zone = make_user("+2250000000106", "Vétérinaire sans zone")
        give_role(vet_no_zone, "veterinarian")
        self.assertEqual(self.as_user(vet_no_zone).get(url).status_code, 404)


class ScanApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = services.register_animal(species=self.cattle, center=self.center,
                                             created_by=self.breeder, label=self.labels[0])

    def scan(self, user, code):
        return self.as_user(user).get(f"/api/scan/{code}/")

    def test_found_full_view(self):
        resp = self.scan(self.breeder, self.labels[0].short_code.lower())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual((data["result"], data["full_access"]), ("found", True))
        self.assertEqual(data["message"], "Animal retrouvé.")
        self.assertEqual(data["unit"]["id"], str(self.unit.id))

    def test_reduced_view_hides_center(self):
        resp = self.scan(self.stranger, self.labels[0].short_code)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["full_access"])
        self.assertIsNone(data["unit"])
        self.assertEqual(data["species"]["code"], "cattle")
        self.assertNotIn("Élevage A", resp.content.decode())

    def test_invalid_unknown_and_unbound(self):
        code = self.labels[0].short_code
        wrong = code[:-1] + ("2" if code[-1] != "2" else "3")
        self.assertEqual(self.scan(self.breeder, wrong).status_code, 400)
        self.assertEqual(self.scan(self.breeder, services.random_short_code()).status_code, 404)
        unbound = self.scan(self.breeder, self.labels[1].short_code)
        self.assertEqual(unbound.status_code, 404)

    def test_replaced_label_points_to_unit(self):
        support = IdentitySupport.objects.get(label=self.labels[0])
        IdentitySupport.objects.filter(pk=support.pk).update(
            unbound_at=support.bound_at, unbound_reason="replaced"
        )
        Label.objects.filter(pk=self.labels[0].pk).update(status="deactivated")
        resp = self.scan(self.breeder, self.labels[0].short_code)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], "replaced")
        self.assertEqual(resp.json()["unit"]["id"], str(self.unit.id))


class SpeciesApiTests(ApiTestCase):
    def test_species_list(self):
        resp = self.as_user(self.breeder).get("/api/species/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({s["code"] for s in resp.json()}, {"cattle", "poultry"})
