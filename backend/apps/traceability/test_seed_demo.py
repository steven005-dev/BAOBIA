from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.core.management.commands.seed import demo_id
from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import Movement

# Fenêtre de la règle de démonstration (seed_alerts) : 21 jours avant l'observation.
LOOKBACK_DAYS = 21


def run(command, *args):
    out = StringIO()
    call_command(command, *args, stdout=out)
    return out.getvalue()


@mock.patch.dict("os.environ", {"SEED_DEMO_PASSWORD": "73915284"})
class SeedDemoTraceabilityTests(TestCase):
    def setUp(self):
        run("seed", "--demo")

    def movement(self, key):
        return Movement.objects.get(id=demo_id("movement", key))

    def test_creates_center_d_and_three_confirmed_simulated_movements(self):
        run("seed_demo_traceability")

        d_center = Center.objects.get(id=demo_id("center", "D"))
        a_center = Center.objects.get(id=demo_id("center", "A"))
        self.assertTrue(d_center.is_simulated)
        self.assertEqual(d_center.zone_id, a_center.zone_id)
        # Seuil d'affichage de la carte en démonstration : 2 élevages par zone.
        self.assertGreaterEqual(Center.objects.filter(zone=d_center.zone).count(), 2)

        for key, src, dst in (("A-D", "A", "D"), ("A-B", "A", "B"), ("B-M", "B", "M")):
            movement = self.movement(key)
            self.assertEqual(movement.status, "confirmed")
            self.assertTrue(movement.is_simulated)
            self.assertEqual(movement.from_center_id, demo_id("center", src))
            self.assertEqual(movement.to_center_id, demo_id("center", dst))
            self.assertIsNotNone(movement.received_at)
            self.assertTrue(movement.items.get().unit.species.code == "cattle")

        self.assertEqual(TrackedUnit.objects.get(id=demo_id("animal", "trace-1")).current_center_id,
                         demo_id("center", "M"))
        self.assertEqual(TrackedUnit.objects.get(id=demo_id("animal", "trace-2")).current_center_id,
                         demo_id("center", "D"))

    def test_dates_fit_the_exposure_window_with_margin(self):
        run("seed_demo_traceability")
        # Le signalement est fait le jour de la démo, au plus tard le lendemain du lancement.
        window_start = timezone.now() + timedelta(days=1) - timedelta(days=LOOKBACK_DAYS)

        a_d, a_b, b_m = self.movement("A-D"), self.movement("A-B"), self.movement("B-M")
        self.assertLess(a_d.occurred_at, window_start - timedelta(days=30))  # cas négatif
        self.assertGreater(a_b.occurred_at, window_start)
        self.assertGreater(b_m.occurred_at, window_start)
        # Profondeur 2 : B -> M part après l'arrivée de l'animal à B.
        self.assertGreater(b_m.occurred_at, a_b.received_at)

    def test_second_run_creates_nothing(self):
        run("seed_demo_traceability")
        counts = (Movement.objects.count(), Center.objects.count(), TrackedUnit.objects.count())

        output = run("seed_demo_traceability")

        self.assertIn("Rien à créer", output)
        self.assertEqual(
            counts, (Movement.objects.count(), Center.objects.count(), TrackedUnit.objects.count())
        )


class SeedDemoTraceabilityWithoutSeedTests(TestCase):
    def test_refuses_without_demo_seed(self):
        with self.assertRaises(CommandError):
            run("seed_demo_traceability")
        self.assertFalse(Movement.objects.exists())
