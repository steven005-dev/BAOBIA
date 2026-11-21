"""Notifications sur le parcours de démonstration (base neuve, comme alerts.test_demo_flow).

Après la validation au niveau 3 d'un cas à l'élevage A : les membres des élevages exposés
(B, M) reçoivent UN message neutre « contact possible » ; le détenteur de A et de D (écarté)
n'en reçoit pas ; le message ne contient ni élevage d'origine ni lieu ; l'éleveur ne peut pas
ouvrir l'alerte ; marquer lu fonctionne.
"""

import json
import os
import uuid
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.management.commands.seed import demo_id
from apps.health import services as health_services
from apps.health.models import Disease
from apps.identity.models import TrackedUnit
from apps.notifications.models import Notification


class DemoNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch.dict(os.environ, {"SEED_DEMO_PASSWORD": "Essai-parcours-2026"}):
            for command, kwargs in (("seed", {"demo": True}), ("seed_health", {}),
                                    ("seed_alerts", {}), ("seed_demo_traceability", {})):
                call_command(command, stdout=StringIO(), **kwargs)
        cls.breeder1 = User.objects.get(phone="+2250000000001")  # A (foyer) et D (écarté)
        cls.breeder2 = User.objects.get(phone="+2250000000002")  # B (exposé), co-détenteur de A
        cls.breeder3 = User.objects.get(phone="+2250000000003")  # C et M (marché exposé)
        vet = User.objects.get(phone="+2250000000004")
        unit = (TrackedUnit.objects.filter(current_center_id=demo_id("center", "A"),
                                           species__code="cattle", kind="animal", life_status="active")
                .exclude(id__in=[demo_id("animal", "trace-1"), demo_id("animal", "trace-2")]).first())
        report, _ = health_services.submit_report(
            report_id=uuid.uuid4(), user=cls.breeder1, center=unit.current_center,
            report_kind="suspicion", affected_count=1, self_severity="high",
            occurred_at=timezone.now(), subjects=[{"unit_id": unit.pk, "condition": "sick"}],
        )
        health_services.review_report(report=report, vet=vet, decision="validate_level3",
                                      disease=Disease.objects.get(code="fmd"))

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def messages(self, user):
        self.client.force_authenticate(user=user)
        return self.client.get("/api/notifications/").json()

    def test_exposed_farms_get_one_neutral_message(self):
        for user in (self.breeder2, self.breeder3):
            exposure = [n for n in self.messages(user) if n["message_code"] == "exposure.contact_possible"]
            self.assertEqual(len(exposure), 1, user.phone)
            self.assertEqual(exposure[0]["params"], {})  # ni élevage d'origine, ni lieu
            text = json.dumps(exposure, ensure_ascii=False)
            self.assertNotIn("Élevage A", text)

    def test_holder_of_focus_and_excluded_farm_gets_no_exposure_message(self):
        codes = [n["message_code"] for n in self.messages(self.breeder1)]
        self.assertNotIn("exposure.contact_possible", codes)

    def test_breeder_cannot_open_the_alert_behind_the_message(self):
        note = Notification.objects.filter(user=self.breeder2,
                                           message_code="exposure.contact_possible").first()
        self.client.force_authenticate(user=self.breeder2)
        self.assertIn(self.client.get(f"/api/alerts/{note.alert_id}/").status_code, (403, 404))

    def test_mark_read(self):
        note = Notification.objects.get(user=self.breeder3, message_code="exposure.contact_possible")
        self.client.force_authenticate(user=self.breeder3)
        before = self.client.get("/api/notifications/unread-count/").json()["unread"]
        self.client.post("/api/notifications/read/", {"ids": [str(note.id)]}, format="json")
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json()["unread"], before - 1)
