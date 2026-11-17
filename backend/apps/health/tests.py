"""Tests du module health (docs/BAOBIA_DB_SPEC.md, section 12).

- création valide ; refus de chaque CHECK et UNIQUE ;
- événements (health_event, health_report_review) : UPDATE et DELETE refusés,
  par l'ORM et en SQL brut ;
- catalogue de départ idempotent.
"""

import uuid

from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.helpers import (
    make_center,
    make_habilitation,
    make_species,
    make_user,
    make_zone,
)
from apps.core.models import Species
from apps.identity import services as identity_services
from apps.identity.models import Attachment

from .models import (
    Disease,
    DiseaseSpecies,
    HealthEvent,
    HealthReport,
    HealthReportAttachment,
    HealthReportReview,
    HealthReportSubject,
    HealthReportSymptom,
    Symptom,
    SymptomSpecies,
)
from .services import HealthError, load_catalog


class HealthFixtureMixin:
    def setUp(self):
        self.breeder = make_user("+2250700000001", "Éleveur test")
        self.vet = make_user("+2250700000002", "Vétérinaire test")
        self.verifier = make_user("+2250700000003", "Vérificateur test")
        self.habilitation = make_habilitation(self.vet, verifier=self.verifier)
        self.cattle = make_species("cattle")
        self.center = make_center(self.breeder, zone=make_zone("TEST-H"))
        self.unit = identity_services.register_animal(
            species=self.cattle, center=self.center, created_by=self.breeder, is_simulated=True
        )
        self.disease = Disease.objects.create(code="test_d", label_fr="Maladie test")
        self.symptom = Symptom.objects.create(code="test_s", label_fr="Symptôme test")

    def make_report(self, **overrides):
        values = {
            "center": self.center,
            "report_kind": "suspicion",
            "affected_count": 2,
            "self_severity": "medium",
            "occurred_at": timezone.now(),
            "created_by": self.breeder,
            "is_simulated": True,
        }
        values.update(overrides)
        return HealthReport.objects.create(**values)

    def make_review(self, report, **overrides):
        values = {
            "report": report,
            "decision": "retain_suspicion",
            "habilitation": self.habilitation,
            "occurred_at": timezone.now(),
            "created_by": self.vet,
        }
        values.update(overrides)
        return HealthReportReview.objects.create(**values)

    def make_event(self, **overrides):
        values = {
            "unit": self.unit,
            "event_type": "vaccination",
            "disease": self.disease,
            "occurred_at": timezone.now(),
            "created_by": self.breeder,
        }
        values.update(overrides)
        return HealthEvent.objects.create(**values)

    def assert_db_refuses(self, func):
        with self.assertRaises(DatabaseError), transaction.atomic():
            func()


class HealthReportConstraintTests(HealthFixtureMixin, TestCase):
    def test_valid_report_with_symptoms_subjects_and_photo(self):
        report = self.make_report(latitude="5.345317", longitude="-4.024429",
                                  position_source="gps")
        HealthReportSymptom.objects.create(report=report, symptom=self.symptom)
        HealthReportSubject.objects.create(report=report, unit=self.unit, condition="sick")
        attachment = Attachment.objects.create(
            storage_key="test/photo.jpg", mime_type="image/jpeg", size_bytes=10,
            sha256="0" * 64, uploaded_by=self.breeder,
        )
        HealthReportAttachment.objects.create(report=report, attachment=attachment)
        report.refresh_from_db()
        self.assertEqual(report.status, "submitted")
        self.assertEqual(list(report.symptoms.all()), [self.symptom])
        self.assertEqual(report.subjects.get().condition, "sick")

    def test_report_checks(self):
        for field, value in (
            ("report_kind", "other"),
            ("affected_count", 0),
            ("self_severity", "max"),
            ("position_source", "sat"),
        ):
            with self.subTest(field=field):
                self.assert_db_refuses(lambda: self.make_report(**{field: value}))

    def test_report_status_check(self):
        report = self.make_report()
        self.assert_db_refuses(
            lambda: HealthReport.objects.filter(pk=report.pk).update(status="contaminated")
        )

    def test_symptom_cannot_be_checked_twice(self):
        report = self.make_report()
        HealthReportSymptom.objects.create(report=report, symptom=self.symptom)
        self.assert_db_refuses(
            lambda: HealthReportSymptom.objects.create(report=report, symptom=self.symptom)
        )

    def test_subject_unique_and_condition_check(self):
        report = self.make_report()
        self.assert_db_refuses(
            lambda: HealthReportSubject.objects.create(
                report=report, unit=self.unit, condition="bad"
            )
        )
        HealthReportSubject.objects.create(report=report, unit=self.unit, condition="dead")
        self.assert_db_refuses(
            lambda: HealthReportSubject.objects.create(
                report=report, unit=self.unit, condition="sick"
            )
        )

    def test_catalog_codes_unique(self):
        self.assert_db_refuses(lambda: Disease.objects.create(code="test_d", label_fr="X"))
        self.assert_db_refuses(lambda: Symptom.objects.create(code="test_s", label_fr="X"))

    def test_catalog_species_links_unique(self):
        DiseaseSpecies.objects.create(disease=self.disease, species=self.cattle)
        self.assert_db_refuses(
            lambda: DiseaseSpecies.objects.create(disease=self.disease, species=self.cattle)
        )
        SymptomSpecies.objects.create(symptom=self.symptom, species=self.cattle)
        self.assert_db_refuses(
            lambda: SymptomSpecies.objects.create(symptom=self.symptom, species=self.cattle)
        )


class HealthReviewAppendOnlyTests(HealthFixtureMixin, TestCase):
    def test_valid_review(self):
        review = self.make_review(self.make_report(), decision="validate_level3",
                                  disease=self.disease)
        self.assertEqual(review.habilitation, self.habilitation)

    def test_review_decision_check(self):
        report = self.make_report()
        self.assert_db_refuses(lambda: self.make_review(report, decision="approve"))

    def test_review_orm_update_and_delete_refused(self):
        review = self.make_review(self.make_report())
        review.note = "modifié"
        with self.assertRaises(RuntimeError):
            review.save()
        with self.assertRaises(RuntimeError):
            review.delete()

    def test_review_queryset_and_sql_update_delete_refused(self):
        review = self.make_review(self.make_report())
        self.assert_db_refuses(
            lambda: HealthReportReview.objects.filter(pk=review.pk).update(note="x")
        )
        self.assert_db_refuses(lambda: HealthReportReview.objects.filter(pk=review.pk).delete())
        for sql in (
            "UPDATE health_report_review SET note = 'x' WHERE id = %s",
            "DELETE FROM health_report_review WHERE id = %s",
        ):
            with self.subTest(sql=sql):
                self.assert_db_refuses(lambda: connection.cursor().execute(sql, [review.pk]))
        self.assertTrue(HealthReportReview.objects.filter(pk=review.pk, note=None).exists())


class HealthEventTests(HealthFixtureMixin, TestCase):
    def test_valid_event_and_correction(self):
        event = self.make_event(product="Vaccin A")
        correction = self.make_event(product="Vaccin B", supersedes=event)
        self.assertEqual(correction.supersedes_id, event.pk)

    def test_event_type_check(self):
        self.assert_db_refuses(lambda: self.make_event(event_type="surgery"))

    def test_event_corrected_only_once(self):
        event = self.make_event()
        self.make_event(supersedes=event)
        self.assert_db_refuses(lambda: self.make_event(supersedes=event))

    def test_event_update_and_delete_refused(self):
        event = self.make_event()
        with self.assertRaises(RuntimeError):
            event.save()
        with self.assertRaises(RuntimeError):
            event.delete()
        self.assert_db_refuses(
            lambda: HealthEvent.objects.filter(pk=event.pk).update(product="x")
        )
        for sql in (
            "UPDATE health_event SET product = 'x' WHERE id = %s",
            "DELETE FROM health_event WHERE id = %s",
        ):
            with self.subTest(sql=sql):
                self.assert_db_refuses(lambda: connection.cursor().execute(sql, [event.pk]))


class HealthCatalogTests(TestCase):
    def test_catalog_requires_species(self):
        with self.assertRaises(HealthError):
            load_catalog()

    def test_catalog_is_idempotent(self):
        call_command("seed", verbosity=0)
        first = load_catalog()
        self.assertTrue(first)
        disease_count, symptom_count = Disease.objects.count(), Symptom.objects.count()
        links = DiseaseSpecies.objects.count() + SymptomSpecies.objects.count()
        self.assertEqual(load_catalog(), [])
        self.assertEqual(Disease.objects.count(), disease_count)
        self.assertEqual(Symptom.objects.count(), symptom_count)
        self.assertEqual(DiseaseSpecies.objects.count() + SymptomSpecies.objects.count(), links)
        # 6 à 8 symptômes au plus pour le prototype (charte, section 15).
        self.assertLessEqual(symptom_count, 8)
        cattle = Species.objects.get(code="cattle")
        self.assertTrue(Disease.objects.filter(code="fmd", species=cattle).exists())

    def test_existing_rows_are_never_modified(self):
        call_command("seed", verbosity=0)
        Symptom.objects.create(code="fever", label_fr="Libellé validé par un vétérinaire")
        load_catalog()
        self.assertEqual(
            Symptom.objects.get(code="fever").label_fr, "Libellé validé par un vétérinaire"
        )


class HealthModuleRegistrationTests(TestCase):
    def test_report_uuid_can_come_from_device(self):
        breeder = make_user("+2250700000009")
        center = make_center(breeder, zone=make_zone("TEST-UUID"))
        report_id = uuid.uuid4()
        report = HealthReport.objects.create(
            id=report_id, center=center, report_kind="death", self_severity="high",
            occurred_at=timezone.now(), created_by=breeder,
        )
        self.assertEqual(report.pk, report_id)
