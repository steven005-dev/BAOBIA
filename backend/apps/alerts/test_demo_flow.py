"""Parcours de démonstration de bout en bout (docs/DEMO.md, contrat section C).

Base neuve : seed --demo, seed_health, seed_alerts, seed_demo_traceability ; l'éleveur 1
signale un bovin malade à A ; le vétérinaire de démo valide au niveau 3. On vérifie les
expositions (B et M en contact possible, D écarté) et la couleur de la carte à chaque
niveau : zone de démo, région, district, pays.
"""

import os
import uuid
from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command, get_commands
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.core.management.commands.seed import demo_id
from apps.geo.models import ZoneStat
from apps.health import services as health_services
from apps.health.models import Disease
from apps.identity.models import TrackedUnit

from . import services
from .models import AlertReport


@skipUnless("seed_demo_traceability" in get_commands(),
            "Commande de Romuald (feature/traceability-models) pas encore dans main.")
class DemoFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch.dict(os.environ, {"SEED_DEMO_PASSWORD": "Essai-parcours-2026"}):
            for command, kwargs in (("seed", {"demo": True}), ("seed_health", {}),
                                    ("seed_alerts", {}), ("seed_demo_traceability", {})):
                call_command(command, stdout=StringIO(), **kwargs)

    def state(self, code):
        return ZoneStat.objects.get(zone__code=code, species__isnull=True).state

    def test_report_then_level3_colors_the_map_at_every_level(self):
        center_a = demo_id("center", "A")
        unit = (TrackedUnit.objects.filter(current_center_id=center_a, species__code="cattle",
                                           kind="animal", life_status="active")
                .exclude(id__in=[demo_id("animal", "trace-1"), demo_id("animal", "trace-2")])
                .first())
        breeder = User.objects.get(phone="+2250000000001")
        vet = User.objects.get(phone="+2250000000004")

        report, _ = health_services.submit_report(
            report_id=uuid.uuid4(), user=breeder, center=unit.current_center,
            report_kind="suspicion", affected_count=1, self_severity="high",
            occurred_at=timezone.now(), subjects=[{"unit_id": unit.pk, "condition": "sick"}],
        )
        services.recompute_zone_stats()
        # RG-14 : avant examen, la carte ne bouge pas.
        for code in ("DEMO-NORD", "CI-R-POR", "CI-D-SV", "DEMO-CI"):
            self.assertEqual(self.state(code), "normal", code)

        health_services.review_report(report=report, vet=vet, decision="validate_level3",
                                      disease=Disease.objects.get(code="fmd"))
        alert = AlertReport.objects.get(report=report).alert
        exposures = {
            e.center_id: (e.exposure_status, e.depth)
            for e in services.current_exposures(alert)
        }
        self.assertEqual(exposures, {
            demo_id("center", "B"): ("exposed", 1),
            demo_id("center", "M"): ("exposed", 2),
            demo_id("center", "D"): ("excluded_negative", 1),
        })
        self.assertEqual(alert.confidence, "normal")

        # Foyer (A) dans le Poro : alerte jusqu'au district des Savanes et au pays.
        for code in ("DEMO-NORD", "CI-R-POR", "CI-D-SV", "DEMO-CI"):
            self.assertEqual(self.state(code), "alert", code)
        # Marché (M) dans le Gbêkê : contact possible jusqu'au district de la Vallée du Bandama.
        for code in ("DEMO-SUD", "CI-R-GBE", "CI-D-VB"):
            self.assertEqual(self.state(code), "exposure", code)
