"""manage.py seed_alerts

Charge les règles sanitaires de DÉMONSTRATION (version 1) et calcule la carte.
À lancer après : manage.py seed --demo puis manage.py seed_health. Idempotent :
une règle existante n'est jamais modifiée (on créerait une nouvelle version).
Les règles sont approuvées par le vétérinaire simulé du seed de démonstration.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts import catalog, services
from apps.alerts.models import DiseaseRule
from apps.health.models import Disease

DEMO_VET_PHONE = "+2250000000004"  # vétérinaire simulé de core/seed.py


class Command(BaseCommand):
    help = "Charge les règles sanitaires de démonstration (expérimentales) et la carte."

    @transaction.atomic
    def handle(self, *args, **options):
        vet = User.objects.filter(phone=DEMO_VET_PHONE).first()
        if vet is None:
            raise CommandError("Vétérinaire simulé absent : lancez d'abord manage.py seed --demo.")
        diseases = {d.code: d for d in Disease.objects.filter(code__in=catalog.DEMO_RULES)}
        if not diseases:
            raise CommandError("Maladies absentes : lancez d'abord manage.py seed_health.")
        created = []
        for code, values in catalog.DEMO_RULES.items():
            disease = diseases.get(code)
            if disease is None:
                continue
            _, is_new = DiseaseRule.objects.get_or_create(
                disease=disease, species=None, version=1,
                defaults={**values, "valid_from": timezone.localdate().replace(month=1, day=1),
                          "approved_by": vet},
            )
            if is_new:
                created.append(code)
        services.recompute_zone_stats()
        if created:
            self.stdout.write("Règles créées (expérimentales) : " + ", ".join(created))
        else:
            self.stdout.write("Rien à créer : les règles existent déjà.")
        self.stdout.write(self.style.SUCCESS("Règles de démonstration et carte prêtes."))
