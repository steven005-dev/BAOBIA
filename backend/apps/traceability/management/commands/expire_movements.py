"""manage.py expire_movements

Passe « expiré » les départs jamais reçus dont le code de confirmation n'est plus
valable (MV-05). Les unités sont libérées et restent à l'élevage de départ.
À lancer régulièrement (tâche planifiée) ; relancer est sans effet.
"""

from django.core.management.base import BaseCommand

from apps.traceability.services import expire_overdue_movements


class Command(BaseCommand):
    help = "Expire les départs non reçus dont le code n'est plus valable."

    def handle(self, *args, **options):
        count = expire_overdue_movements()
        self.stdout.write(self.style.SUCCESS(f"{count} départ(s) expiré(s)."))
