"""Tests du module alerts (docs/BAOBIA_DB_SPEC.md, section 12). Données simulées.

Scénario (cahier des charges, annexes A3 et A4), règle : 21 jours en amont, profondeur 2.
  A (foyer) --J-5--> B --J-3--> C --J-2--> E   (E au-delà de la profondeur)
  A --J-60--> D                                 (hors fenêtre : cas négatif)
"""

from datetime import timedelta

from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.helpers import (
    give_role,
    make_center,
    make_habilitation,
    make_species,
    make_user,
    make_zone,
)
from apps.geo.models import Zone, ZoneStat
from apps.health import services as health_services
from apps.health.models import Disease, HealthReport
from apps.identity import services as identity_services
from apps.notifications.models import Notification
from apps.traceability.models import Movement, MovementItem

from . import services
from .models import Alert, AlertEvent, AlertExposure, AlertReport, AlertReview, DiseaseRule


class AlertScenarioMixin:
    def setUp(self):
        self.now = timezone.now()
        self.region = make_zone("TEST-REG")
        self.zone = Zone.objects.create(parent=self.region, level=2, code="TEST-DEP",
                                        name="Dép test")
        self.cattle = make_species("cattle")
        verifier = make_user("+2250000000399", "Vérificateur")
        self.vet = make_user("+2250000000300", "Vétérinaire test")
        give_role(self.vet, "veterinarian", zone=self.region)
        self.habilitation = make_habilitation(self.vet, verifier=verifier, ref="VET-A")

        self.users, self.centers, self.units = {}, {}, {}
        for index, key in enumerate("ABCDE", start=1):
            user = make_user(f"+22500000003{index:02d}", f"Éleveur {key}")
            give_role(user, "breeder")
            self.users[key] = user
            self.centers[key] = make_center(user, name=f"Élevage {key}", zone=self.zone)
            self.units[key] = identity_services.register_animal(
                species=self.cattle, center=self.centers[key], created_by=user
            )

        self.disease = Disease.objects.create(code="fmd", label_fr="Fièvre aphteuse")
        self.rule = DiseaseRule.objects.create(
            disease=self.disease, version=1, lookback_days=21, lookforward_days=0,
            max_depth=2, min_zone_effectif=2, include_unconfirmed=False,
            valid_from=timezone.localdate() - timedelta(days=90), approved_by=self.vet,
        )
        self.move("A", "B", days_ago=5)
        self.move("B", "C", days_ago=3)
        self.move("C", "E", days_ago=2)
        self.move("A", "D", days_ago=60)

    def move(self, origin, target, *, days_ago, status="confirmed", unit_key=None):
        at = self.now - timedelta(days=days_ago)
        movement = Movement.objects.create(
            movement_type="transfer", from_center=self.centers[origin],
            to_center=self.centers[target], occurred_at=at, created_by=self.users[origin],
            status=status, received_at=at + timedelta(hours=4) if status != "declared" else None,
            is_simulated=True,
        )
        MovementItem.objects.create(movement=movement, unit=self.units[unit_key or origin])
        return movement

    def report_at_a(self):
        report, _ = health_services.submit_report(
            report_id=__import__("uuid").uuid4(), user=self.users["A"], center=self.centers["A"],
            report_kind="suspicion", affected_count=1, self_severity="high",
            occurred_at=self.now, subjects=[{"unit_id": self.units["A"].pk,
                                             "condition": "sick"}],
        )
        return report

    def validate(self, report, decision="validate_level3"):
        return health_services.review_report(report=report, vet=self.vet, decision=decision,
                                             disease=self.disease)

    def exposure_map(self, alert):
        alert.refresh_from_db()
        return {
            e.center.name: (e.exposure_status, e.depth)
            for e in services.current_exposures(alert).select_related("center")
        }


class ExposureEngineTests(AlertScenarioMixin, TestCase):
    def test_validation_creates_level3_alert_with_explained_exposures(self):
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        self.assertEqual((alert.level, alert.validated_by, alert.habilitation),
                         (3, self.vet, self.habilitation))
        self.assertEqual(alert.rule, self.rule)
        self.assertEqual(self.exposure_map(alert), {
            "Élevage B": ("exposed", 1),
            "Élevage C": ("exposed", 2),
            "Élevage D": ("excluded_negative", 1),
        })
        c = services.current_exposures(alert).get(center=self.centers["C"])
        self.assertEqual(
            [(s.from_center.name, s.to_center.name, s.explanation_code)
             for s in c.steps.order_by("step_no")],
            [("Élevage A", "Élevage B", "sent_from_focus"),
             ("Élevage B", "Élevage C", "sent_after_exposure")],
        )
        d = services.current_exposures(alert).get(center=self.centers["D"])
        self.assertEqual(d.steps.get().explanation_code, "outside_window")

    def test_movement_of_another_species_is_ignored(self):
        # Une alerte bovine ne suit pas un mouvement qui ne porte que des porcs.
        pig = make_species("pig")
        pig_unit = identity_services.register_animal(
            species=pig, center=self.centers["A"], created_by=self.users["A"])
        self.units["A-pig"] = pig_unit
        self.move("A", "E", days_ago=1, unit_key="A-pig")
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        self.assertEqual(alert.species, self.cattle)
        self.assertNotIn("Élevage E", self.exposure_map(alert))

    def test_mixed_movement_counts_and_names_the_right_animal(self):
        pig = make_species("pig")
        self.units["A-pig"] = identity_services.register_animal(
            species=pig, center=self.centers["A"], created_by=self.users["A"])
        movement = self.move("A", "E", days_ago=1, unit_key="A-pig")
        MovementItem.objects.create(movement=movement, unit=self.units["A"])
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        self.assertEqual(self.exposure_map(alert)["Élevage E"], ("exposed", 1))
        step = services.current_exposures(alert).get(center=self.centers["E"]).steps.get()
        self.assertEqual(step.unit_id, self.units["A"].pk)

    def test_depth_is_respected(self):
        self.validate(self.report_at_a())
        self.assertNotIn("Élevage E", self.exposure_map(Alert.objects.get()))

    def test_unconfirmed_movement_not_counted_when_rule_says_so(self):
        self.move("A", "E", days_ago=1, status="declared")
        self.validate(self.report_at_a())
        self.assertEqual(self.exposure_map(Alert.objects.get())["Élevage E"],
                         ("excluded_negative", 1))

    def test_disputed_movement_counts_with_reduced_confidence(self):
        Movement.objects.filter(from_center=self.centers["A"],
                                to_center=self.centers["B"]).update(status="disputed")
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        self.assertEqual(self.exposure_map(alert)["Élevage B"], ("exposed", 1))
        self.assertEqual(alert.confidence, "reduced")

    def test_one_side_movement_counts_with_reduced_confidence(self):
        # Spec v1.4, 9.6 : un transfert déclaré d'un seul côté réduit aussi la confiance.
        self.rule.include_unconfirmed = True
        self.rule.save(update_fields=["include_unconfirmed"])
        Movement.objects.filter(from_center=self.centers["A"],
                                to_center=self.centers["B"]).update(status="declared",
                                                                    received_at=None)
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        self.assertEqual(self.exposure_map(alert)["Élevage B"], ("exposed", 1))
        self.assertEqual(alert.confidence, "reduced")
        event = AlertEvent.objects.filter(alert=alert, event_type="recomputed").latest("occurred_at")
        self.assertEqual(event.payload["one_side_movements"], 2)  # chemins vers B et C

    def test_confirmed_movements_keep_normal_confidence(self):
        self.validate(self.report_at_a())
        self.assertEqual(Alert.objects.get().confidence, "normal")

    def test_departure_before_exposure_does_not_propagate(self):
        # B a envoyé vers E AVANT de recevoir l'animal de A : E n'est pas exposé par B.
        Movement.objects.filter(from_center=self.centers["C"]).update(occurred_at=self.now)
        self.move("B", "E", days_ago=10, unit_key="B")
        self.validate(self.report_at_a())
        self.assertNotIn("Élevage E", self.exposure_map(Alert.objects.get()))

    def test_recompute_creates_a_new_run_and_keeps_the_old_one(self):
        self.validate(self.report_at_a())
        alert = Alert.objects.get()
        first_run = alert.current_run_id
        services.compute_exposures(alert, self.vet)
        alert.refresh_from_db()
        self.assertNotEqual(alert.current_run_id, first_run)
        self.assertTrue(AlertExposure.objects.filter(run_id=first_run).exists())
        self.assertEqual(AlertEvent.objects.filter(alert=alert, event_type="recomputed").count(), 2)

    def test_level2_computes_exposures_without_notifying_breeders(self):
        self.validate(self.report_at_a(), decision="raise_level2")
        alert = Alert.objects.get()
        self.assertEqual(alert.level, 2)
        self.assertIn("Élevage B", self.exposure_map(alert))
        self.assertFalse(Notification.objects.exists())

    def test_dismiss_cancels_the_open_alert(self):
        report = self.report_at_a()
        self.validate(report, decision="raise_level2")
        health_services.review_report(report=report, vet=self.vet, decision="dismiss",
                                      note="Simulé : examen négatif")
        self.assertEqual(Alert.objects.get().status, "cancelled")


class OneAlertPerFocusTests(AlertScenarioMixin, TestCase):
    """Une seule alerte ouverte par foyer, maladie et espèce."""

    def dismiss(self, report):
        return health_services.review_report(report=report, vet=self.vet, decision="dismiss",
                                             note="Pas de lien avec le foyer.")

    def test_second_validated_report_joins_the_open_alert(self):
        first, second = self.report_at_a(), self.report_at_a()
        self.validate(first)
        notifications = Notification.objects.count()
        self.validate(second)
        alert = Alert.objects.get()
        self.assertEqual(
            set(AlertReport.objects.filter(alert=alert).values_list("report_id", flat=True)),
            {first.pk, second.pk})
        self.assertEqual(alert.level, 3)
        self.assertEqual(Notification.objects.count(), notifications)  # pas de 2e message
        event = AlertEvent.objects.filter(alert=alert, event_type="reviewed")             .latest("occurred_at")
        self.assertTrue(event.payload["attached"])

    def test_level2_then_level3_on_another_report_raises_the_same_alert(self):
        first, second = self.report_at_a(), self.report_at_a()
        self.validate(first, decision="raise_level2")
        self.validate(second)
        alert = Alert.objects.get()
        self.assertEqual((alert.level, alert.validated_by), (3, self.vet))

    def test_dismissing_one_report_keeps_the_alert_open(self):
        first, second = self.report_at_a(), self.report_at_a()
        self.validate(first)
        self.validate(second)
        self.dismiss(second)
        self.assertEqual(Alert.objects.get().status, "open")
        self.dismiss(first)
        self.assertEqual(Alert.objects.get().status, "cancelled")

    def test_other_disease_opens_its_own_alert(self):
        other = Disease.objects.create(code="lsd", label_fr="Dermatose nodulaire")
        DiseaseRule.objects.create(
            disease=other, version=1, lookback_days=21, lookforward_days=0, max_depth=2,
            min_zone_effectif=2, include_unconfirmed=False,
            valid_from=timezone.localdate() - timedelta(days=90), approved_by=self.vet,
        )
        self.validate(self.report_at_a())
        health_services.review_report(report=self.report_at_a(), vet=self.vet,
                                      decision="validate_level3", disease=other)
        self.assertEqual(
            sorted(Alert.objects.values_list("disease__code", flat=True)), ["fmd", "lsd"])

    def test_closed_alert_is_not_reused(self):
        first = self.report_at_a()
        self.validate(first)
        health_services.review_report(report=first, vet=self.vet, decision="close")
        self.validate(self.report_at_a())
        self.assertEqual(
            sorted(Alert.objects.values_list("status", flat=True)), ["closed", "open"])


class NeutralNotificationTests(AlertScenarioMixin, TestCase):
    def test_exposed_breeders_get_a_neutral_message_only(self):
        self.validate(self.report_at_a())
        notified = {n.user_id: n for n in Notification.objects.all()}
        self.assertEqual(set(notified), {self.users["B"].pk, self.users["C"].pk})
        for notification in notified.values():
            self.assertEqual(notification.message_code, "exposure.contact_possible")
            self.assertEqual(notification.params, {})
        self.assertNotIn(self.users["A"].pk, notified)
        self.assertNotIn(self.users["D"].pk, notified)


class EndOfSurveillanceTests(AlertScenarioMixin, TestCase):
    """Point 5 : fin de surveillance aux élevages qui avaient reçu « Contact possible »."""

    def ended(self):
        return Notification.objects.filter(message_code="exposure.ended")

    def test_closing_tells_the_notified_breeders(self):
        report = self.report_at_a()
        self.validate(report)
        notified = set(Notification.objects.filter(
            message_code="exposure.contact_possible").values_list("user_id", flat=True))
        health_services.review_report(report=report, vet=self.vet, decision="close")
        self.assertEqual(set(self.ended().values_list("user_id", flat=True)), notified)
        # L'ancien « Contact possible » est marqué lu : l'accueil ne montre que la fin.
        self.assertFalse(Notification.objects.filter(message_code="exposure.contact_possible",
                                                     read_at__isnull=True).exists())
        self.assertFalse(self.ended().filter(read_at__isnull=False).exists())
        for notification in self.ended():
            self.assertEqual(notification.params, {})  # neutre : ni foyer ni lieu

    def test_cancelling_after_notification_also_tells_them(self):
        report = self.report_at_a()
        self.validate(report)
        health_services.review_report(report=report, vet=self.vet, decision="dismiss",
                                      note="Examen négatif.")
        self.assertEqual(self.ended().count(), 2)  # éleveurs de B et C

    def test_nobody_told_at_level2_so_no_end_message(self):
        report = self.report_at_a()
        self.validate(report, decision="raise_level2")
        health_services.review_report(report=report, vet=self.vet, decision="dismiss",
                                      note="Examen négatif.")
        self.assertFalse(Notification.objects.exists())

    def test_alert_kept_open_sends_no_end_message(self):
        first, second = self.report_at_a(), self.report_at_a()
        self.validate(first)
        self.validate(second)
        health_services.review_report(report=second, vet=self.vet, decision="dismiss",
                                      note="Sans lien.")
        self.assertFalse(self.ended().exists())


class ZoneStatTests(AlertScenarioMixin, TestCase):
    def test_zone_turns_to_alert_after_validation(self):
        self.validate(self.report_at_a())
        stat = ZoneStat.objects.get(zone=self.zone, species=None)
        self.assertEqual((stat.state, stat.centers_count, stat.is_masked), ("alert", 5, False))

    def test_pending_report_does_not_change_the_map(self):
        # RG-14 : avant examen, un signalement n'a aucun effet visible hors des professionnels.
        self.report_at_a()
        services.recompute_zone_stats()
        self.assertEqual(ZoneStat.objects.get(zone=self.zone, species=None).state, "normal")

    def test_level2_decision_puts_zone_under_watch(self):
        # Élevage sans mouvement : le niveau 2 n'expose personne, la zone est « À surveiller ».
        other_zone = Zone.objects.create(parent=self.region, level=2, code="TEST-DEP2",
                                         name="Dép 2")
        breeder = make_user("+2250000000397", "Éleveur F")
        give_role(breeder, "breeder")
        center = make_center(breeder, name="Élevage F", zone=other_zone)
        make_center(breeder, name="Élevage G", zone=other_zone)  # seuil d'affichage : 2
        unit = identity_services.register_animal(species=self.cattle, center=center,
                                                 created_by=breeder)
        report, _ = health_services.submit_report(
            report_id=__import__("uuid").uuid4(), user=breeder, center=center,
            report_kind="suspicion", affected_count=1, self_severity="high",
            occurred_at=self.now, subjects=[{"unit_id": unit.pk, "condition": "sick"}],
        )
        self.validate(report, decision="raise_level2")
        services.recompute_zone_stats()
        self.assertEqual(ZoneStat.objects.get(zone=other_zone, species=None).state, "watch")
        self.assertEqual(ZoneStat.objects.get(zone=self.zone, species=None).state, "normal")

    def test_small_zone_is_masked(self):
        lonely_zone = make_zone("TEST-SEUL")
        breeder = make_user("+2250000000398", "Éleveur isolé")
        center = make_center(breeder, name="Élevage isolé", zone=lonely_zone)
        identity_services.register_animal(species=self.cattle, center=center,
                                          created_by=breeder)
        services.recompute_zone_stats()
        stat = ZoneStat.objects.get(zone=lonely_zone, species=None)
        self.assertEqual((stat.state, stat.is_masked), ("unknown", True))


class AlertConstraintTests(AlertScenarioMixin, TestCase):
    def assert_db_refuses(self, func):
        with self.assertRaises(DatabaseError), transaction.atomic():
            func()

    def alert(self, **overrides):
        values = {"rule": self.rule, "focus_center": self.centers["A"], "zone": self.zone,
                  "level": 1, "opened_at": self.now}
        values.update(overrides)
        return Alert.objects.create(**values)

    def test_level3_refused_without_validating_vet(self):
        self.assert_db_refuses(lambda: self.alert(level=3))
        self.assert_db_refuses(lambda: self.alert(level=3, validated_by=self.vet,
                                                  validated_at=self.now))

    def test_level3_refused_without_valid_habilitation_by_service(self):
        report = self.report_at_a()
        self.habilitation.status = "revoked"
        self.habilitation.save()
        with self.assertRaises(health_services.HealthError):
            self.validate(report)
        self.assertFalse(Alert.objects.exists())

    def test_alert_checks(self):
        self.assert_db_refuses(lambda: self.alert(level=4))
        self.assert_db_refuses(lambda: self.alert(focus_center=None))
        self.assert_db_refuses(lambda: self.alert(trigger_kind="zone_cluster", focus_center=None))
        self.assert_db_refuses(lambda: self.alert(confidence="low"))
        self.assert_db_refuses(lambda: self.alert(status="done"))
        self.alert(trigger_kind="zone_cluster", focus_center=None, species=self.cattle)

    def test_rule_checks_and_versions(self):
        def rule(**overrides):
            values = {"disease": self.disease, "version": 2, "lookback_days": 1,
                      "lookforward_days": 0, "max_depth": 1, "valid_from": self.now.date(),
                      "approved_by": self.vet}
            values.update(overrides)
            return DiseaseRule.objects.create(**values)

        for override in ({"max_depth": 7}, {"version": 0}, {"lookback_days": -1},
                         {"cluster_min_reports": 1}, {"cluster_min_ratio": 2},
                         {"escalation_hours": 0}, {"min_zone_effectif": 0}):
            with self.subTest(override=override):
                self.assert_db_refuses(lambda: rule(**override))
        self.assert_db_refuses(lambda: rule(version=1))  # (maladie, NULL, 1) existe déjà

    def test_used_rule_is_frozen(self):
        DiseaseRule.objects.filter(pk=self.rule.pk).update(lookback_days=30)  # pas encore utilisée
        self.alert()
        self.assert_db_refuses(
            lambda: DiseaseRule.objects.filter(pk=self.rule.pk).update(lookback_days=40)
        )

    def test_review_and_event_are_append_only(self):
        alert = self.alert()
        review = AlertReview.objects.create(alert=alert, decision="need_info",
                                            habilitation=self.habilitation,
                                            occurred_at=self.now, created_by=self.vet)
        event = AlertEvent.objects.create(alert=alert, event_type="opened",
                                          occurred_at=self.now, created_by=self.vet)
        self.assert_db_refuses(lambda: AlertReview.objects.create(
            alert=alert, decision="approve", habilitation=self.habilitation,
            occurred_at=self.now, created_by=self.vet))
        for obj, table in ((review, "alert_review"), (event, "alert_event")):
            with self.assertRaises(RuntimeError):
                obj.save()
            with self.assertRaises(RuntimeError):
                obj.delete()
            for sql in (f"UPDATE {table} SET created_at = now() WHERE id = %s",
                        f"DELETE FROM {table} WHERE id = %s"):
                self.assert_db_refuses(lambda: connection.cursor().execute(sql, [obj.pk]))

    def test_exposure_unique_per_run_center_with_null_unit(self):
        alert = self.alert()
        values = {"alert": alert, "run_id": __import__("uuid").uuid4(),
                  "center": self.centers["B"], "exposure_status": "exposed", "depth": 1,
                  "computed_at": self.now}
        AlertExposure.objects.create(**values)
        self.assert_db_refuses(lambda: AlertExposure.objects.create(**values))
        self.assert_db_refuses(lambda: AlertExposure.objects.create(
            **{**values, "run_id": __import__("uuid").uuid4(), "exposure_status": "infected"}))


class ReportStatusUnchangedTests(AlertScenarioMixin, TestCase):
    def test_report_without_rule_cannot_be_validated(self):
        DiseaseRule.objects.all().delete()
        report = self.report_at_a()
        with self.assertRaises(services.AlertsError):
            self.validate(report)
        self.assertEqual(HealthReport.objects.get(pk=report.pk).status, "submitted")
