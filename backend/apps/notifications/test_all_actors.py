"""Tous les acteurs reçoivent des messages dans l'application (21/11).

Base de démo neuve : signalement à A, validation niveau 3, clôture, et un transfert A -> B.
Qui reçoit quoi : vétérinaire (à examiner), éleveurs de A (décision), autorité (alerte
validée puis close), agent mandaté sur B (contact possible), éleveur de B (animaux à
recevoir). Celui qui agit n'est jamais prévenu de sa propre action.
"""

import os
import uuid
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.core.management.commands.seed import demo_id
from apps.health import services as health_services
from apps.health.models import Disease
from apps.identity.models import Center, TrackedUnit
from apps.notifications.models import Notification
from apps.traceability.services import declare_movement


def codes(user):
    return list(Notification.objects.filter(user=user).values_list("message_code", flat=True))


class AllActorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch.dict(os.environ, {"SEED_DEMO_PASSWORD": "Essai-parcours-2026"}):
            for command, kwargs in (("seed", {"demo": True}), ("seed_health", {}),
                                    ("seed_alerts", {}), ("seed_demo_traceability", {})):
                call_command(command, stdout=StringIO(), **kwargs)
        phone = {"b1": "1", "b2": "2", "b3": "3", "vet": "4", "agent": "5", "auth": "6"}
        cls.u = {k: User.objects.get(phone=f"+225000000000{v}") for k, v in phone.items()}
        cls.unit = (TrackedUnit.objects.filter(current_center_id=demo_id("center", "A"),
                                               species__code="cattle", kind="animal",
                                               life_status="active")
                    .exclude(id__in=[demo_id("animal", "trace-1"), demo_id("animal", "trace-2")])
                    .first())
        Notification.objects.all().delete()  # on ne regarde que ce qui suit
        cls.report, _ = health_services.submit_report(
            report_id=uuid.uuid4(), user=cls.u["b1"], center=cls.unit.current_center,
            report_kind="suspicion", affected_count=1, self_severity="high",
            occurred_at=timezone.now(), subjects=[{"unit_id": cls.unit.pk, "condition": "sick"}],
        )

    def test_vet_is_told_of_a_new_report_not_the_breeder(self):
        self.assertIn("report.to_review", codes(self.u["vet"]))
        note = Notification.objects.get(user=self.u["vet"], message_code="report.to_review")
        self.assertEqual(note.params["report_id"], str(self.report.pk))
        self.assertNotIn("report.to_review", codes(self.u["b1"]))  # celui qui signale

    def test_decision_reaches_the_farm_authority_and_mandated_agent(self):
        health_services.review_report(report=self.report, vet=self.u["vet"],
                                      decision="validate_level3",
                                      disease=Disease.objects.get(code="fmd"))
        for key in ("b1", "b2"):  # détenteur et co-détenteur de A
            self.assertIn("report.reviewed", codes(self.u[key]), key)
        self.assertNotIn("report.reviewed", codes(self.u["vet"]))  # il a décidé
        self.assertIn("alert.authority_validated", codes(self.u["auth"]))
        # L'agent a un mandat sur B (exposé) : il est prévenu pour aider l'éleveur.
        self.assertIn("exposure.contact_possible", codes(self.u["agent"]))

        health_services.review_report(report=self.report, vet=self.u["vet"], decision="close")
        self.assertIn("alert.authority_closed", codes(self.u["auth"]))
        self.assertIn("exposure.ended", codes(self.u["agent"]))

    def test_transfer_tells_the_receiving_farm_not_the_sender(self):
        declare_movement(from_center=Center.objects.get(id=demo_id("center", "A")),
                         to_center=Center.objects.get(id=demo_id("center", "B")),
                         items=[{"unit": self.unit}], created_by=self.u["b1"])
        self.assertIn("movement.to_confirm", codes(self.u["b2"]))  # détenteur de B
        self.assertIn("movement.to_confirm", codes(self.u["agent"]))  # mandat sur B
        self.assertNotIn("movement.to_confirm", codes(self.u["b1"]))  # il a déclaré
        note = Notification.objects.filter(message_code="movement.to_confirm").first()
        self.assertEqual(note.params, {"count": 1})  # aucun nom d'élevage
