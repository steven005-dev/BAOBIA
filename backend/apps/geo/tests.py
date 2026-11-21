"""Tests du module geo (docs/BAOBIA_DB_SPEC.md, section 12)."""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.helpers import make_species, make_zone

from .models import Zone, ZoneStat


class ZoneStatConstraintTests(TestCase):
    def setUp(self):
        self.zone = make_zone("TEST-GEO")
        self.cattle = make_species("cattle")

    def make_stat(self, **overrides):
        values = {"zone": self.zone, "species": self.cattle, "state": "normal",
                  "computed_at": timezone.now()}
        values.update(overrides)
        return ZoneStat.objects.create(**values)

    def assert_db_refuses(self, func):
        with self.assertRaises(IntegrityError), transaction.atomic():
            func()

    def test_valid_stat_for_each_state(self):
        for index, state in enumerate(("normal", "watch", "exposure", "alert", "unknown")):
            zone = make_zone(f"TEST-GEO-{index}")
            self.assertEqual(self.make_stat(zone=zone, state=state).state, state)

    def test_state_check(self):
        self.assert_db_refuses(lambda: self.make_stat(state="bad"))

    def test_counts_check(self):
        self.assert_db_refuses(lambda: self.make_stat(centers_count=-1))
        self.assert_db_refuses(lambda: self.make_stat(animals_count=-1))

    def test_one_row_per_zone_and_species(self):
        self.make_stat()
        self.assert_db_refuses(lambda: self.make_stat(state="alert"))

    def test_one_row_per_zone_for_all_species_null(self):
        # species NULL = toutes espèces : NULLS NOT DISTINCT interdit un doublon.
        self.make_stat(species=None)
        self.assert_db_refuses(lambda: self.make_stat(species=None))

    def test_zone_level_check(self):
        self.assert_db_refuses(lambda: Zone.objects.create(level=7, code="BAD", name="Mauvaise"))


class LoadCiZonesTests(TestCase):
    def test_districts_and_regions_under_the_country(self):
        from .services import load_ci_zones

        country = Zone.objects.create(level=0, code="TEST-CI", name="Pays test")
        zones = load_ci_zones(country)
        load_ci_zones(country)  # idempotent
        self.assertEqual(Zone.objects.filter(level=1, parent=country).count(), 14)
        self.assertEqual(Zone.objects.filter(level=2, parent__parent=country).count(), 33)
        self.assertEqual(zones["CI-R-POR"].parent.code, "CI-D-SV")  # Poro -> Savanes
        self.assertIsNotNone(zones["CI-R-GBE"].latitude)
