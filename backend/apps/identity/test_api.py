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
from apps.identity.models import IdentitySupport, IdentityVerification, Label, TrackedUnit


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

    def test_preprinted_tag_issued_to_my_center_accepted(self):
        # Spec v1.4 : boucle préimprimée remise par l'agent à cet élevage, scannée à l'ajout.
        services.issue_labels([self.labels[2]], self.center, issued_by=self.breeder)
        resp = self.post_unit(self.breeder, kind="animal", species_id=str(self.cattle.id),
                              label_code=self.labels[2].short_code)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["label_code"], self.labels[2].short_code)

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


class LabelReplaceApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = services.register_animal(species=self.cattle, center=self.center,
                                             created_by=self.breeder, label=self.labels[0])
        self.url = f"/api/units/{self.unit.id}/label/"

    def test_replace_lost_label_keeps_history(self):
        resp = self.as_user(self.breeder).post(
            self.url, {"label_code": self.labels[1].short_code, "reason": "lost"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["label_code"], self.labels[1].short_code)
        self.assertEqual(resp.json()["id"], str(self.unit.id))
        self.assertEqual(Label.objects.get(pk=self.labels[0].pk).status, "lost")
        self.assertEqual(IdentitySupport.objects.filter(unit=self.unit).count(), 2)
        self.assertTrue(AuditLog.objects.filter(action="label.replace", entity_id=self.unit.id).exists())
        # L'ancienne étiquette est signalée perdue, la nouvelle retrouve l'animal.
        old = self.client.get(f"/api/scan/{self.labels[0].short_code}/").json()
        self.assertEqual((old["result"], old["unit"]["id"]), ("lost", str(self.unit.id)))
        new = self.client.get(f"/api/scan/{self.labels[1].short_code}/").json()
        self.assertEqual(new["result"], "found")

    def test_damaged_label_is_deactivated_and_scan_says_replaced(self):
        self.as_user(self.breeder).post(
            self.url, {"label_code": self.labels[1].short_code, "reason": "damaged"}, format="json"
        )
        self.assertEqual(Label.objects.get(pk=self.labels[0].pk).status, "deactivated")
        self.assertEqual(self.client.get(f"/api/scan/{self.labels[0].short_code}/").json()["result"], "replaced")

    def test_label_used_elsewhere_rolls_back(self):
        services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder,
                                 label=self.labels[1])
        resp = self.as_user(self.breeder).post(
            self.url, {"label_code": self.labels[1].short_code, "reason": "damaged"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Label.objects.get(pk=self.labels[0].pk).status, "active")
        self.assertTrue(IdentitySupport.objects.filter(label=self.labels[0], unbound_at__isnull=True).exists())

    def test_replay_is_without_effect(self):
        body = {"label_code": self.labels[1].short_code, "reason": "damaged"}
        self.assertEqual(self.as_user(self.breeder).post(self.url, body, format="json").status_code, 200)
        self.assertEqual(self.client.post(self.url, body, format="json").status_code, 200)
        self.assertEqual(IdentitySupport.objects.filter(unit=self.unit).count(), 2)
        self.assertEqual(AuditLog.objects.filter(action="label.replace", entity_id=self.unit.id).count(), 1)

    def test_rights(self):
        body = {"label_code": self.labels[1].short_code, "reason": "lost"}
        self.assertEqual(self.as_user(self.stranger).post(self.url, body, format="json").status_code, 404)
        vet = make_user("+2250000000107", "Vétérinaire zone")
        give_role(vet, "veterinarian", zone=self.zone)
        self.assertEqual(self.as_user(vet).post(self.url, body, format="json").status_code, 403)


class VerificationApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = services.register_animal(species=self.cattle, center=self.center,
                                             created_by=self.breeder, label=self.labels[0])
        self.url = f"/api/units/{self.unit.id}/verifications/"

    def body(self, **extra):
        return {"label_code": self.labels[0].short_code, "occurred_at": "2026-11-17T09:00:00Z", **extra}

    def test_confirmed_with_position_and_replay(self):
        vid = str(uuid.uuid4())
        body = self.body(id=vid, latitude="5.360000", longitude="-4.008000", accuracy_m="12.0")
        resp = self.as_user(self.breeder).post(self.url, body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["result"], "confirmed")
        v = IdentityVerification.objects.get(pk=vid)
        self.assertEqual((v.position_source, str(v.latitude)), ("gps", "5.360000"))
        self.assertEqual(self.client.post(self.url, body, format="json").status_code, 200)
        self.assertEqual(IdentityVerification.objects.count(), 1)

    def test_result_is_computed_by_server(self):
        resp = self.as_user(self.breeder).post(
            self.url, self.body(label_code=self.labels[1].short_code, result="confirmed"), format="json"
        )
        self.assertEqual(resp.json()["result"], "mismatch")
        v = IdentityVerification.objects.get(pk=resp.json()["id"])
        self.assertEqual(v.position_source, "none")
        self.assertIsNone(v.latitude)

    def test_not_visible_and_immutable(self):
        self.assertEqual(self.as_user(self.stranger).post(self.url, self.body(), format="json").status_code, 404)
        resp = self.as_user(self.breeder).post(self.url, self.body(), format="json")
        v = IdentityVerification.objects.get(pk=resp.json()["id"])
        with self.assertRaises(RuntimeError):
            v.save()


class ZonesAndLabelsApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.agent = make_user("+2250000000108", "Agent")
        give_role(self.agent, "field_agent")

    def test_zones_for_center_creation(self):
        resp = self.as_user(self.breeder).get("/api/centers/zones/")
        self.assertEqual(resp.status_code, 200)
        names = [z["name"] for z in resp.json()]
        self.assertIn("Dép test", names)
        dep = next(z for z in resp.json() if z["name"] == "Dép test")
        self.assertEqual(dep["parent_id"], str(self.region.id))

    def test_agent_issues_labels_all_or_nothing(self):
        url = f"/api/centers/{self.center.id}/labels/"
        codes = [self.labels[0].short_code, self.labels[1].short_code.lower()]
        resp = self.as_user(self.agent).post(url, {"codes": codes}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["issued"], 2)
        self.assertEqual(Label.objects.get(pk=self.labels[0].pk).issued_to_center_id, self.center.id)
        # Déjà remises : refusé, et la troisième n'est pas remise non plus.
        again = self.client.post(url, {"codes": [self.labels[0].short_code, self.labels[2].short_code]},
                                 format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(Label.objects.get(pk=self.labels[2].pk).status, "printed")

    def test_issue_refuses_unknown_code_and_breeders(self):
        url = f"/api/centers/{self.center.id}/labels/"
        resp = self.as_user(self.agent).post(url, {"codes": [services.random_short_code()]}, format="json")
        self.assertEqual(resp.status_code, 400)
        body = {"codes": [self.labels[0].short_code]}
        self.assertEqual(self.as_user(self.breeder).post(url, body, format="json").status_code, 403)

    def test_batch_for_printing(self):
        resp = self.as_user(self.agent).post("/api/label-batches/", {"quantity": 5}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.json()["codes"]), 5)
        self.assertTrue(all(services.is_valid_short_code(c) for c in resp.json()["codes"]))
        self.assertEqual(self.as_user(self.breeder).post("/api/label-batches/", {"quantity": 5},
                                                         format="json").status_code, 403)


class GeneratedLabelApiTests(ApiTestCase):
    """Le téléphone crée le code à l'ajout : l'étiquette n'existe pas encore en base."""

    def test_new_code_creates_and_binds_label(self):
        code = services.random_short_code()
        resp = self.as_user(self.breeder).post("/api/units/", {
            "kind": "animal", "center_id": str(self.center.id), "species_id": str(self.cattle.id),
            "label_code": code,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["label_code"], code)
        label = Label.objects.get(short_code=code)
        self.assertEqual((label.status, label.issued_to_center_id), ("active", self.center.id))
        self.assertTrue(AuditLog.objects.filter(action="label.generate", entity_id=label.id).exists())
        scan = self.client.get(f"/api/scan/{code}/").json()
        self.assertEqual((scan["result"], scan["unit"]["id"]), ("found", resp.json()["id"]))

    def test_invalid_generated_code_creates_nothing(self):
        code = services.random_short_code()
        wrong = code[:-1] + ("2" if code[-1] != "2" else "3")
        resp = self.as_user(self.breeder).post("/api/units/", {
            "kind": "animal", "center_id": str(self.center.id), "species_id": str(self.cattle.id),
            "label_code": wrong,
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Label.objects.filter(short_code=wrong).exists())
        self.assertEqual(TrackedUnit.objects.count(), 0)

    def test_replace_with_new_generated_code(self):
        unit = services.register_animal(species=self.cattle, center=self.center,
                                        created_by=self.breeder, label=self.labels[0])
        code = services.random_short_code()
        resp = self.as_user(self.breeder).post(
            f"/api/units/{unit.id}/label/", {"label_code": code, "reason": "damaged"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["label_code"], code)
        self.assertEqual(self.client.get(f"/api/scan/{self.labels[0].short_code}/").json()["result"], "replaced")

    def test_code_already_on_another_animal_is_refused(self):
        services.register_animal(species=self.cattle, center=self.center, created_by=self.breeder,
                                 label=self.labels[0])
        resp = self.as_user(self.breeder).post("/api/units/", {
            "kind": "animal", "center_id": str(self.center.id), "species_id": str(self.cattle.id),
            "label_code": self.labels[0].short_code,
        }, format="json")
        self.assertEqual(resp.status_code, 400)


class BreederRegisterApiTests(ApiTestCase):
    """Agent de terrain : inscrire un éleveur et son premier élevage."""

    def setUp(self):
        super().setUp()
        self.agent = make_user("+2250000000110", "Agent test")
        give_role(self.agent, "field_agent", zone=self.region)

    def body(self, **extra):
        data = {
            "id": str(uuid.uuid4()), "full_name": "Koffi Yao", "phone": "07 11 22 33 44",
            "password": "K7RT2M9P", "center_id": str(uuid.uuid4()),
            "center_name": "Ferme Koffi", "zone_id": str(self.zone.id),
            "species_ids": [str(self.cattle.id)], "consent": True,
        }
        data.update(extra)
        return data

    def test_agent_registers_breeder_center_and_mandate(self):
        body = self.body()
        resp = self.as_user(self.agent).post("/api/breeders/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["breeder"]["phone"], "+2250711223344")
        self.assertNotIn("password", resp.json()["breeder"])

        from django.contrib.auth import get_user_model
        from apps.accounts.services import user_has_role

        breeder = get_user_model().objects.get(pk=body["id"])
        self.assertTrue(breeder.check_password("K7RT2M9P"))
        self.assertTrue(user_has_role(breeder, "breeder"))
        # L'éleveur est détenteur ; l'agent a un mandat "declare" sur l'élevage.
        self.assertEqual(services.accessible_centers(breeder)[0]["access"], "holder")
        agent_access = {c["id"]: c for c in services.accessible_centers(self.agent)}
        self.assertEqual(agent_access[uuid.UUID(body["center_id"])]["mandate_scope"], "declare")
        log = AuditLog.objects.get(action="user.register", actor_user=self.agent)
        self.assertEqual(log.details["consent_notice"], "2026-11-20")

        # Rejeu hors ligne : sans effet.
        again = self.client.post("/api/breeders/", body, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action="user.register").count(), 1)

        # L'éleveur peut se connecter avec le mot de passe remis.
        self.client.force_authenticate(user=None)
        login = self.client.post("/api/auth/login/", {"phone": "0711223344", "password": "K7RT2M9P"},
                                 format="json")
        self.assertEqual(login.status_code, 200)

    def test_agent_can_add_animals_for_the_breeder(self):
        body = self.body()
        self.as_user(self.agent).post("/api/breeders/", body, format="json")
        unit = {"id": str(uuid.uuid4()), "kind": "animal", "center_id": body["center_id"],
                "species_id": str(self.cattle.id), "label_code": self.labels[0].short_code}
        resp = self.client.post("/api/units/", unit, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_consent_required(self):
        body = self.body(consent=False)
        resp = self.as_user(self.agent).post("/api/breeders/", body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(services.Center.objects.filter(pk=body["center_id"]).exists())

    def test_only_field_agent(self):
        resp = self.as_user(self.breeder).post("/api/breeders/", self.body(), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_zone_outside_agent_sector_refused(self):
        resp = self.as_user(self.agent).post(
            "/api/breeders/", self.body(zone_id=str(self.other_zone.id)), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_phone_already_used_rolls_back(self):
        body = self.body(phone=self.breeder.phone)
        resp = self.as_user(self.agent).post("/api/breeders/", body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("déjà un compte", resp.json()["detail"])
        self.assertFalse(services.Center.objects.filter(pk=body["center_id"]).exists())

    def test_weak_password_refused_and_nothing_created(self):
        body = self.body(password="123")
        resp = self.as_user(self.agent).post("/api/breeders/", body, format="json")
        self.assertEqual(resp.status_code, 400)
        from django.contrib.auth import get_user_model
        self.assertFalse(get_user_model().objects.filter(pk=body["id"]).exists())

    def test_same_center_id_from_another_agent_conflicts(self):
        body = self.body()
        self.as_user(self.agent).post("/api/breeders/", body, format="json")
        other = make_user("+2250000000111", "Autre agent")
        give_role(other, "field_agent", zone=self.region)
        resp = self.as_user(other).post("/api/breeders/", body, format="json")
        self.assertEqual(resp.status_code, 409)
