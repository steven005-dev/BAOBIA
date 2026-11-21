"""manage.py seed_official_tags

Donne un numéro officiel (15 chiffres, boucle Vet'Tronic, 384 = Côte d'Ivoire) à chaque
bovin, mouton et chèvre SIMULÉ qui n'en a pas (voir apps/core/demo_official_tags.py).
À lancer en dernier, après les autres seeds de démonstration. Idempotent.
"""

from django.core.management.base import BaseCommand

from apps.core.demo_official_tags import assign_official_tags


class Command(BaseCommand):
    help = "Numéros officiels (15 chiffres) pour les animaux de démonstration."

    def handle(self, *args, **options):
        count = assign_official_tags()
        self.stdout.write(f"Numéros officiels posés : {count}.")
