"""manage.py load_ci_zones [--country CODE]

Charge les 14 districts et les 33 régions de Côte d'Ivoire (tracés geoBoundaries, CC BY 4.0)
sous la zone pays donnée (par défaut DEMO-CI, la zone pays du seed de démonstration).
Idempotent.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.geo.models import Zone
from apps.geo.services import load_ci_zones


class Command(BaseCommand):
    help = "Charge les districts et les régions de Côte d'Ivoire."

    def add_arguments(self, parser):
        parser.add_argument("--country", default="DEMO-CI", help="Code de la zone pays (niveau 0).")

    def handle(self, *args, country, **options):
        root = Zone.objects.filter(code=country, level=0).first()
        if root is None:
            raise CommandError(f"Zone pays {country} absente : lancez d'abord manage.py seed --demo.")
        zones = load_ci_zones(root)
        self.stdout.write(f"{len(zones)} zones de Côte d'Ivoire prêtes sous {country}.")
