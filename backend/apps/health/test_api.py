"""API health : signalements et évaluation vétérinaire. Données simulées."""

import uuid

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.helpers import (
    give_role,
    make_center,
    make_habilitation,
    make_species,
    make_user,
    make_zone,
)
from apps.audit.models import AuditLog
from apps.geo.models import Zone
from apps.identity import services as identity_services

from .models import Disease, HealthReport, HealthReportReview, HealthReportSubject, Symptom
from .signals import report_reviewed


class HealthApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.region = make_zone("TEST-REG")
        self.zone = Zone.objects.create(parent=self.region, level=2, code="TEST-DEP",
                                        name="Dép test")
        self.other_zone = make_zone("TEST-AUTRE")
        self.cattle = make_species("cattle")

        self.breeder = make_user("+2250000000201", "Éleveur test")
        give_role(self.breeder, "breeder")
        self.center = make_center(self.breeder, name="Élevage A", zone=self.zone)
        self.unit = identity_services.register_animal(
            species=self.cattle, center=self.center, created_by=self.breeder
        )

        self.stranger = make_user("+2250000000202", "Autre éleveur")
        give_role(self.stranger, "breeder")
        self.stranger_center = make_center(self.stranger, name="Élevage B", zone=self.zone)
        self.stranger_unit = identity_services.register_animal(
            species=self.cattle, center=self.stranger_center, created_by=self.stranger
        )

        verifier = make_user("+2250000000209", "Vérificateur")
        # Vétérinaire de la région : couvre aussi la zone fille TEST-DEP.
        self.vet = make_user("+2250000000203", "Vétérinaire test")
        give_role(self.vet, "veterinarian", zone=self.region)
        make_habilitation(self.vet, verifier=verifier, ref="VET-1")
        self.far_vet = make_user("+2250000000204", "Vétérinaire autre zone")
        give_role(self.far_vet, "veterinarian", zone=self.other_zone)
        make_habilitation(self.far_vet, verifier=verifier, ref="VET-2")
        self.unverified_vet = make_user("+2250000000205", "Vétérinaire non habilité")
        give_role(self.unverified_vet, "veterinarian", zone=self.region)
        make_habilitation(self.unverified_vet, status="pending", ref="VET-3")

        self.fever = Symptom.objects.create(code="fever", label_fr="Corps chaud, fièvre")
        self.fever.species.add(self.cattle)
        self.fmd = Disease.objects.create(code="fmd", label_fr="Fièvre aphteuse")

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def body(self, **overrides):
        values = {
            "id": str(uuid.uuid4()),
            "center_id": str(self.center.id),
            "report_kind": "suspicion",
            "affected_count": 2,
            "self_severity": "high",
            "occurred_at": timezone.now().isoformat(),
            "symptom_codes": ["fever"],
            "subjects": [{"unit_id": str(self.unit.id), "condition": "sick"}],
        }
        values.update(overrides)
        return values

    def submit(self, user=None, **overrides):
        return self.as_user(user or self.breeder).post(
            "/api/health-reports/", self.body(**overrides), format="json"
        )


class ReportSubmitTests(HealthApiTestCase):
    def test_breeder_reports_a_case(self):
        resp = self.submit()
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["message"], "Signalement envoyé au vétérinaire.")
        self.assertEqual([s["code"] for s in data["symptoms"]], ["fever"])
        self.assertNotIn("reviews", data)
        self.assertTrue(
            AuditLog.objects.filter(action="health_report.submit", entity_id=data["id"]).exists()
        )

    def test_replaying_the_same_operation_creates_nothing(self):
        body = self.body()
        first = self.as_user(self.breeder).post("/api/health-reports/", body, format="json")
        again = self.as_user(self.breeder).post("/api/health-reports/", body, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(HealthReport.objects.count(), 1)
        self.assertEqual(HealthReportSubject.objects.count(), 1)

    def test_same_id_with_other_content_is_a_conflict(self):
        body = self.body()
        self.as_user(self.breeder).post("/api/health-reports/", body, format="json")
        body["affected_count"] = 5
        resp = self.as_user(self.breeder).post("/api/health-reports/", body, format="json")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(HealthReport.objects.get().affected_count, 2)

    def test_any_changed_field_on_replay_is_a_conflict(self):
        changes = {
            "occurred_at": (timezone.now() - timezone.timedelta(days=1)).isoformat(),
            "note": "Autre note",
            "latitude": "5.100000", "longitude": "-4.100000", "position_source": "manual",
            "symptom_codes": [],
            "subjects": [{"unit_id": str(self.unit.id), "condition": "dead"}],
            "self_severity": "low",
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                body = self.body(latitude="5.300000", longitude="-4.000000",
                                 position_source="gps")
                first = self.as_user(self.breeder).post("/api/health-reports/", body,
                                                        format="json")
                self.assertEqual(first.status_code, 201)
                same = self.as_user(self.breeder).post("/api/health-reports/", body,
                                                       format="json")
                self.assertEqual(same.status_code, 200)
                body[field] = value
                if field == "latitude":
                    body["longitude"] = changes["longitude"]
                resp = self.as_user(self.breeder).post("/api/health-reports/", body,
                                                       format="json")
                self.assertEqual(resp.status_code, 409, resp.content)

    def test_other_breeder_cannot_report_for_my_farm(self):
        resp = self.submit(user=self.stranger, subjects=[])
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(HealthReport.objects.exists())

    def test_vet_of_the_zone_can_report(self):
        self.assertEqual(self.submit(user=self.vet).status_code, 201)

    def test_animal_from_another_farm_is_refused(self):
        resp = self.submit(subjects=[{"unit_id": str(self.stranger_unit.id),
                                      "condition": "sick"}])
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(HealthReport.objects.exists())

    def test_unknown_symptom_is_refused(self):
        self.assertEqual(self.submit(symptom_codes=["glowing"]).status_code, 400)

    def test_invalid_values_are_refused(self):
        for override in ({"affected_count": 0}, {"report_kind": "other"},
                         {"latitude": "5.3"}):
            with self.subTest(override=override):
                self.assertEqual(self.submit(**override).status_code, 400)

    def test_anonymous_refused(self):
        self.assertEqual(self.client.post("/api/health-reports/", self.body(),
                                          format="json").status_code, 401)


class ReportVisibilityTests(HealthApiTestCase):
    def setUp(self):
        super().setUp()
        self.report_id = self.submit(latitude="5.300000", longitude="-4.000000",
                                     position_source="gps").json()["id"]

    def ids(self, user):
        resp = self.as_user(user).get("/api/health-reports/")
        self.assertEqual(resp.status_code, 200)
        return [r["id"] for r in resp.json()]

    def test_breeder_sees_his_report_without_vet_details(self):
        data = self.as_user(self.breeder).get(f"/api/health-reports/{self.report_id}/").json()
        self.assertEqual(data["status"], "submitted")
        self.assertNotIn("reviews", data)
        self.assertNotIn("position", data)

    def test_other_breeder_sees_nothing(self):
        self.assertEqual(self.ids(self.stranger), [])
        resp = self.as_user(self.stranger).get(f"/api/health-reports/{self.report_id}/")
        self.assertEqual(resp.status_code, 404)

    def test_vet_of_parent_zone_sees_details(self):
        self.assertEqual(self.ids(self.vet), [self.report_id])
        data = self.as_user(self.vet).get(f"/api/health-reports/{self.report_id}/").json()
        self.assertEqual(data["reviews"], [])
        self.assertEqual(data["position"]["source"], "gps")

    def test_vet_of_another_zone_sees_nothing(self):
        self.assertEqual(self.ids(self.far_vet), [])

    def test_symptoms_filtered_by_species(self):
        Symptom.objects.create(code="feathers", label_fr="Plumes ébouriffées")
        resp = self.as_user(self.breeder).get("/api/symptoms/?species=cattle")
        self.assertEqual([s["code"] for s in resp.json()], ["fever"])


class ReportReviewTests(HealthApiTestCase):
    def setUp(self):
        super().setUp()
        self.report_id = self.submit().json()["id"]
        self.url = f"/api/health-reports/{self.report_id}/review/"
        # Règle de test (valeurs simulées) : sans règle, aucune alerte ne peut être validée.
        from apps.alerts.models import DiseaseRule

        DiseaseRule.objects.create(
            disease=self.fmd, version=1, lookback_days=21, lookforward_days=0, max_depth=2,
            valid_from=timezone.localdate() - timezone.timedelta(days=30),
            approved_by=self.vet,
        )

    def review(self, user, **body):
        return self.as_user(user).post(self.url, body, format="json")

    def test_vet_validates_and_signal_is_sent(self):
        received = []

        def listener(sender, report, review, **kwargs):
            received.append((report.pk, review.decision))

        report_reviewed.connect(listener)
        try:
            resp = self.review(self.vet, decision="validate_level3", disease_code="fmd")
        finally:
            report_reviewed.disconnect(listener)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["report_status"], "validated")
        self.assertEqual(received, [(uuid.UUID(self.report_id), "validate_level3")])
        review = HealthReportReview.objects.get()
        self.assertEqual(review.habilitation.reference_number, "VET-1")
        breeder_view = self.as_user(self.breeder).get(
            f"/api/health-reports/{self.report_id}/").json()
        self.assertEqual(breeder_view["status"], "validated")

    def test_status_follows_decisions(self):
        for decision, expected in (("request_info", "under_review"),
                                   ("raise_level2", "under_review")):
            self.assertEqual(self.review(self.vet, decision=decision).json()["report_status"],
                             expected)
        resp = self.review(self.vet, decision="dismiss", note="Simulé : pas de signe")
        self.assertEqual(resp.json()["report_status"], "rejected")

    def test_dismiss_requires_a_reason(self):
        self.assertEqual(self.review(self.vet, decision="dismiss").status_code, 400)

    def test_validation_without_rule_is_refused(self):
        from apps.alerts.models import DiseaseRule

        DiseaseRule.objects.all().delete()
        resp = self.review(self.vet, decision="validate_level3", disease_code="fmd")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(HealthReportReview.objects.exists())

    def test_validation_requires_a_disease(self):
        self.assertEqual(self.review(self.vet, decision="validate_level3").status_code, 400)

    def test_closed_report_cannot_be_reviewed(self):
        self.review(self.vet, decision="close")
        self.assertEqual(self.review(self.vet, decision="request_info").status_code, 400)

    def test_breeder_cannot_review(self):
        self.assertEqual(self.review(self.breeder, decision="close").status_code, 403)

    def test_vet_without_valid_habilitation_cannot_review(self):
        resp = self.review(self.unverified_vet, decision="validate_level3", disease_code="fmd")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(HealthReportReview.objects.exists())

    def test_vet_of_another_zone_cannot_review(self):
        resp = self.review(self.far_vet, decision="close")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(HealthReportReview.objects.exists())
