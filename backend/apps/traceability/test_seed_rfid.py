"""Commande seed_demo_rfid et scénario de démo du guide des ajouts (2 minutes)."""

import uuid
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.management.commands.seed import demo_id
from apps.traceability.models import MarketScan, RfidTag

User = get_user_model()


def run(command, *args):
    out = StringIO()
    call_command(command, *args, stdout=out)
    return out.getvalue()


@mock.patch.dict("os.environ", {"SEED_DEMO_PASSWORD": "73915284"})
class SeedDemoRfidTests(TestCase):
    def setUp(self):
        run("seed", "--demo")
        run("seed_demo_traceability")
        run("seed_demo_rfid")
        self.client = APIClient()
        self.manager = User.objects.get(phone="+2250000000003")
        self.market = demo_id("center", "M")

    def scan(self, number, direction="in", **extra):
        self.client.force_authenticate(user=self.manager)
        return self.client.post(f"/api/markets/{self.market}/scans/", {
            "id": str(uuid.uuid4()), "direction": direction, "code": number, **extra,
        }, format="json")

    def route(self, key):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/api/units/{demo_id('animal', key)}/route/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_seed_is_idempotent(self):
        counts = (RfidTag.objects.count(), MarketScan.objects.count())
        self.assertIn("Rien à créer", run("seed_demo_rfid"))
        self.assertEqual(counts, (RfidTag.objects.count(), MarketScan.objects.count()))
        self.assertEqual(RfidTag.objects.count(), 14)

    def test_demo_scenario(self):
        # Entrée : A (vert), D (avertissement neutre), numéro inconnu (gris).
        self.assertEqual(self.scan("384 000 000 000 101").data["result"], "ok")
        warned = self.scan("384 000 000 000 104").data
        self.assertEqual((warned["result"], warned["warnings"][0]["code"]), ("ok", "declared_missing"))
        self.assertEqual(self.scan("384 000 000 000 999").data["result"], "unknown")
        # Sortie de B vers l'Élevage B -> parcours « Probable ».
        out = self.scan("384 000 000 000 102", direction="out",
                        to_center_id=str(demo_id("center", "B")))
        self.assertEqual(out.data["result"], "ok")
        self.assertEqual(self.route("rfid-B")["steps"][0]["confidence_label"], "Probable")
        # C : transfert confirmé des deux côtés -> « Sûr » (vu par un professionnel de la zone).
        vet = User.objects.get(phone="+2250000000004")
        self.client.force_authenticate(user=vet)
        route_c = self.client.get(f"/api/units/{demo_id('animal', 'rfid-C')}/route/").data
        self.assertEqual(route_c["steps"][0]["confidence_label"], "Sûr")
        # Bilan du jour : 10 bovins du seed + B + A + D entrés, 1 inconnu, 1 alerte, 1 sortie.
        self.client.force_authenticate(user=self.manager)
        summary = self.client.get(f"/api/markets/{self.market}/summary/").data
        self.assertEqual((summary["entered"], summary["left"], summary["unknown"], summary["warnings"]),
                         (13, 1, 1, 1))
        self.assertNotIn("Élevage", str(summary["by_origin_zone"]))
