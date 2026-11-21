"""API alerts et carte : masquage par profil (RG-13, CA-02, CA-04). Données simulées."""

import json

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.tests.helpers import give_role, make_habilitation, make_user, make_zone
from apps.audit.models import AuditLog

from .models import Alert
from .tests import AlertScenarioMixin


class AlertApiTests(AlertScenarioMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.validate(self.report_at_a())
        self.alert = Alert.objects.get()

    def get(self, user, url):
        self.client.force_authenticate(user=user)
        return self.client.get(url)

    def test_vet_sees_the_explained_alert(self):
        resp = self.get(self.vet, f"/api/alerts/{self.alert.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual((data["level"], data["exposed_count"], data["excluded_count"]),
                         (3, 2, 1))
        by_center = {e["center"]["name"]: e for e in data["exposures"]}
        self.assertEqual([s["to"] for s in by_center["Élevage C"]["path"]],
                         ["Élevage B", "Élevage C"])
        self.assertEqual(by_center["Élevage D"]["path"][0]["reason"], "outside_window")
        self.assertTrue(data["rule"]["experimental"])
        self.assertTrue(AuditLog.objects.filter(action="alert.view",
                                                entity_id=self.alert.id).exists())

    def test_detail_gives_the_timeline_and_the_map_district(self):
        from apps.geo.models import Zone

        data = self.get(self.vet, f"/api/alerts/{self.alert.id}/").json()
        self.assertIsNone(data["map_district"])  # zones de test hors de la Côte d'Ivoire
        self.assertTrue(data["reports"][0]["created_at"])
        types = [e["type"] for e in data["events"]]
        for expected in ("opened", "reviewed", "notified"):
            self.assertIn(expected, types)
        # Zone du foyer rattachée à une région, elle-même dans un district (CI-D-…).
        district = Zone.objects.create(level=1, code="CI-D-TST", name="District test")
        self.region.parent = district
        self.region.save(update_fields=["parent"])
        data = self.get(self.vet, f"/api/alerts/{self.alert.id}/").json()
        self.assertEqual(data["map_district"], "CI-D-TST")

    def test_vet_list(self):
        resp = self.get(self.vet, "/api/alerts/")
        self.assertEqual([a["id"] for a in resp.json()], [str(self.alert.id)])

    def test_breeders_never_see_alerts_or_origin(self):
        for key in ("A", "B", "C"):
            with self.subTest(breeder=key):
                self.assertEqual(self.get(self.users[key], "/api/alerts/").status_code, 403)
                self.assertEqual(
                    self.get(self.users[key], f"/api/alerts/{self.alert.id}/").status_code, 403)

    def test_exposed_breeder_message_does_not_reveal_origin(self):
        resp = self.get(self.users["C"], "/api/notifications/")
        self.assertEqual(resp.status_code, 200)
        text = json.dumps(resp.json(), ensure_ascii=False)
        self.assertIn("exposure.contact_possible", text)
        for secret in ("Élevage A", str(self.centers["A"].id), "Élevage B",
                       str(self.users["A"].id)):
            self.assertNotIn(secret, text)

    def test_vet_of_another_zone_cannot_see_the_alert(self):
        far_vet = make_user("+2250000000397", "Vétérinaire autre zone")
        give_role(far_vet, "veterinarian", zone=make_zone("TEST-LOIN"))
        make_habilitation(far_vet, verifier=self.vet, ref="VET-LOIN")
        self.assertEqual(self.get(far_vet, "/api/alerts/").json(), [])
        self.assertEqual(self.get(far_vet, f"/api/alerts/{self.alert.id}/").status_code, 404)


class MapApiTests(AlertScenarioMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.validate(self.report_at_a())

    def test_map_shows_zone_state_without_farm_names(self):
        self.client.force_authenticate(user=self.users["B"])
        data = self.client.get("/api/map/zones/").json()
        zone = next(z for z in data["zones"] if z["zone"]["code"] == "TEST-DEP")
        self.assertEqual((zone["state"], zone["centers_count"]), ("alert", 5))
        self.assertEqual([c["name"] for c in data["my_centers"]], ["Élevage B"])
        text = json.dumps(data["zones"], ensure_ascii=False)
        self.assertNotIn("Élevage", text)

    def test_species_filter(self):
        self.client.force_authenticate(user=self.vet)
        data = self.client.get("/api/map/zones/?species=cattle").json()
        self.assertEqual({z["state"] for z in data["zones"]}, {"alert"})

    def test_parent_zone_takes_the_state_of_its_children(self):
        """Carte de Côte d'Ivoire : la région (zone mère) compte les élevages de ses zones filles
        et prend l'état le plus grave."""
        self.client.force_authenticate(user=self.vet)
        zones = {z["zone"]["code"]: z for z in self.client.get("/api/map/zones/").json()["zones"]}
        parent = zones[self.region.code]
        self.assertEqual(parent["state"], "alert")
        self.assertGreaterEqual(parent["centers_count"], zones["TEST-DEP"]["centers_count"])

    def test_parent_of_a_masked_zone_hides_its_counts(self):
        """Sinon l'effectif d'une zone masquée se retrouve par soustraction depuis la zone mère."""
        from apps.geo.models import ZoneStat

        ZoneStat.objects.filter(zone=self.zone).update(is_masked=True, state="unknown")
        self.client.force_authenticate(user=self.users["B"])
        zones = {z["zone"]["code"]: z for z in self.client.get("/api/map/zones/").json()["zones"]}
        parent = zones[self.region.code]
        self.assertEqual((parent["centers_count"], parent["animals_count"]), (None, None))
        self.assertFalse(parent["is_masked"])  # l'état de la zone mère reste affiché

    def test_farm_points_only_for_professionals(self):
        from apps.identity.models import Center

        Center.objects.filter(zone=self.zone).update(latitude="9.500000", longitude="-5.600000")
        self.client.force_authenticate(user=self.vet)
        points = self.client.get("/api/map/zones/").json()["points"]
        self.assertTrue(points)
        self.assertEqual(set(points[0]), {"latitude", "longitude", "zone_id", "type"})  # ni nom ni id
        self.client.force_authenticate(user=self.users["B"])
        self.assertEqual(self.client.get("/api/map/zones/").json()["points"], [])

    def test_masked_zone_hides_counts(self):
        from apps.geo.models import ZoneStat

        ZoneStat.objects.filter(zone=self.zone).update(is_masked=True, state="unknown")
        self.client.force_authenticate(user=self.vet)
        zone = next(z for z in self.client.get("/api/map/zones/").json()["zones"]
                    if z["zone"]["code"] == "TEST-DEP")
        self.assertEqual((zone["state"], zone["centers_count"], zone["animals_count"]),
                         ("unknown", None, None))
