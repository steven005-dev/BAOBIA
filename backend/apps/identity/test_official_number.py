"""Identifiant officiel (21/11) : numéro de la boucle Vet'Tronic (15 chiffres) dans la liste, la
fiche et le scan ; le code QR BAOBIA reste. Données simulées : seed --demo puis seed_official_tags."""

import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.management.commands.seed import demo_id
from apps.identity.models import TrackedUnit
from apps.traceability.models import RfidTag


class OfficialNumberTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch.dict(os.environ, {"SEED_DEMO_PASSWORD": "Essai-parcours-2026"}):
            call_command("seed", demo=True, stdout=StringIO())
        call_command("seed_official_tags", stdout=StringIO())
        cls.breeder = User.objects.get(phone="+2250000000001")
        cls.other = User.objects.get(phone="+2250000000003")

    def setUp(self):
        self.client = APIClient()

    def test_every_demo_ruminant_gets_one_ivorian_number_and_reseeding_changes_nothing(self):
        ruminants = TrackedUnit.objects.filter(is_simulated=True, kind="animal",
                                               species__code__in=("cattle", "sheep", "goat"))
        self.assertTrue(ruminants.exists())
        for unit in ruminants:
            tag = RfidTag.objects.get(unit=unit, status="active")
            self.assertRegex(tag.number, r"^384\d{12}$")
        before = RfidTag.objects.count()
        out = StringIO()
        call_command("seed_official_tags", stdout=out)
        self.assertIn("posés : 0", out.getvalue())
        self.assertEqual(RfidTag.objects.count(), before)
        # porcs et volailles gardent le code BAOBIA seulement
        self.assertFalse(RfidTag.objects.filter(unit__species__code__in=("pig", "poultry")).exists())

    def test_list_and_record_show_the_official_number_and_keep_the_qr_code(self):
        self.client.force_authenticate(user=self.breeder)
        items = self.client.get(f"/api/centers/{demo_id('center', 'A')}/units/").json()
        cow = next(i for i in items if i["species"]["code"] == "cattle")
        self.assertRegex(cow["official_number"], r"^384( \d{3}){4}$")
        self.assertTrue(cow["label_code"])  # le code QR BAOBIA est gardé
        record = self.client.get(f"/api/units/{cow['id']}/").json()
        self.assertEqual(record["official_number"], cow["official_number"])

    def test_scan_by_official_number_with_or_without_spaces(self):
        tag = RfidTag.objects.filter(unit__current_center_id=demo_id("center", "A"),
                                     status="active").first()
        self.client.force_authenticate(user=self.breeder)
        for code in (tag.number, " ".join(tag.number[i:i + 3] for i in range(0, 15, 3))):
            data = self.client.get(f"/api/scan/{code}/").json()
            self.assertEqual((data["result"], data["unit"]["id"]), ("found", str(tag.unit_id)))
        # un autre éleveur : vue réduite, sans élevage
        self.client.force_authenticate(user=self.other)
        data = self.client.get(f"/api/scan/{tag.number}/").json()
        self.assertEqual((data["full_access"], data["unit"]), (False, None))
        self.assertEqual(self.client.get("/api/scan/384999999999999/").status_code, 404)
