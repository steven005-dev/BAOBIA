"""manage.py seed_health

Charge le catalogue de départ du module health (maladies, symptômes).
À lancer après manage.py seed (qui crée les espèces). Idempotent.
Liste provisoire, à faire valider par un vétérinaire (voir apps/health/catalog.py).
"""

from django.core.management.base import BaseCommand, CommandError

from apps.health.services import HealthError, load_catalog


class Command(BaseCommand):
    help = "Charge les maladies et symptômes de départ (idempotent)."

    def handle(self, *args, **options):
        try:
            created = load_catalog()
        except HealthError as exc:
            raise CommandError(str(exc)) from exc
        if created:
            self.stdout.write("Créé : " + ", ".join(created))
        else:
            self.stdout.write("Rien à créer : tout existe déjà.")
        self.stdout.write(self.style.SUCCESS("Catalogue santé chargé."))
