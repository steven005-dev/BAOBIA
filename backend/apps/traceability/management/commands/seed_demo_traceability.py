"""manage.py seed_demo_traceability

Mouvements de démonstration pour le moteur d'alertes (docs/CONTRAT_SANTE_MOUVEMENTS.md,
section C). À lancer après `seed --demo` (puis `seed_health` et `seed_alerts`).

Crée, tout marqué simulé :
- l'élevage D (zone Nord, détenteur : éleveur 1), par identity.services.create_center ;
- deux bovins propres à cette démo à l'élevage A, par identity.services.register_animal
  (les bovins du seed peuvent avoir été déplacés par les tests E2E) ;
- trois mouvements bovins confirmés, datés par rapport au jour du lancement :
    A -> D  il y a 60 jours          cas négatif (hors fenêtre de 21 jours)
    A -> B  il y a 5 jours           exposé, profondeur 1
    B -> M  il y a 3 jours           exposé, profondeur 2 (après l'arrivée à B)
  M (marché) remplace C, qui n'élève pas de bovins dans le seed.

Toute écriture passe par identity.services et traceability.services.
Idempotent : UUID fixes (uuid5) ; relancer ne crée aucun doublon.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.management.commands.seed import DEMO_USERS, demo_id
from apps.core.models import Species
from apps.identity import services as identity_services
from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import Movement
from apps.traceability.services import confirm_movement_receipt, declare_movement

DEMO_ANIMALS = (
    # clé, nom, sexe
    ("trace-1", "Bovin démo 1 (simulé)", "female"),
    ("trace-2", "Bovin démo 2 (simulé)", "male"),
)

DEMO_MOVEMENTS = (
    # clé, animal, départ, arrivée, type, jours avant aujourd'hui, heures avant réception
    ("A-D", "trace-2", "A", "D", "transfer", 60, 3),
    ("A-B", "trace-1", "A", "B", "sale", 5, 4),
    ("B-M", "trace-1", "B", "M", "sale", 3, 4),
)

# Détenteur de chaque centre, comme dans seed --demo (D : même éleveur que A).
HOLDERS = {"A": "breeder1", "B": "breeder2", "M": "breeder3", "D": "breeder1"}


class Command(BaseCommand):
    help = "Ajoute les mouvements de démonstration du moteur d'alertes (simulés)."

    def handle(self, *args, **options):
        self.created = []
        now = timezone.now()
        with transaction.atomic():
            cattle = Species.objects.filter(code="cattle").first()
            if cattle is None:
                raise CommandError("Espèce « cattle » absente : lancez d'abord `seed --demo`.")
            users = self._users()
            centers = self._centers(users, cattle, now)
            self._animals(users, centers, cattle)
            for spec in DEMO_MOVEMENTS:
                self._movement(spec, users, centers, now)

        if self.created:
            self.stdout.write("Créé : " + ", ".join(self.created))
        else:
            self.stdout.write("Rien à créer : tout existe déjà.")
        self.stdout.write(self.style.SUCCESS("Mouvements de démonstration prêts."))

    def _users(self):
        phones = {key: phone for key, phone, _name, _role in DEMO_USERS}
        users = {}
        for key in set(HOLDERS.values()):
            user = User.objects.filter(phone=phones[key]).first()
            if user is None:
                raise CommandError("Comptes de démonstration absents : lancez d'abord `seed --demo`.")
            if not user.is_simulated:
                raise CommandError(f"Le numéro {phones[key]} appartient à un compte non simulé : arrêt.")
            users[key] = user
        return users

    def _centers(self, users, cattle, now):
        centers = {}
        for key in ("A", "B", "M"):
            center = Center.objects.filter(id=demo_id("center", key)).first()
            if center is None:
                raise CommandError(f"Centre {key} absent : lancez d'abord `seed --demo`.")
            centers[key] = center

        d_center = Center.objects.filter(id=demo_id("center", "D")).first()
        if d_center is None:
            d_center = identity_services.create_center(
                center_id=demo_id("center", "D"), name="Élevage D (simulé)",
                zone=centers["A"].zone, center_type="farm", created_by=users["breeder1"],
                holder=users[HOLDERS["D"]], species=[cattle], is_simulated=True, starts_at=now - timedelta(days=90),
            )
            self.created.append("centre D")
        centers["D"] = d_center
        return centers

    def _animals(self, users, centers, cattle):
        for key, name, sex in DEMO_ANIMALS:
            unit_id = demo_id("animal", key)
            if TrackedUnit.objects.filter(id=unit_id).exists():
                continue
            identity_services.register_animal(
                unit_id=unit_id, species=cattle, center=centers["A"],
                created_by=users[HOLDERS["A"]], local_name=name, sex=sex, is_simulated=True,
            )
            self.created.append(name)

    def _movement(self, spec, users, centers, now):
        key, animal_key, from_key, to_key, movement_type, days_ago, hours = spec
        movement_id = demo_id("movement", key)
        if Movement.objects.filter(id=movement_id).exists():
            return
        unit = TrackedUnit.objects.get(id=demo_id("animal", animal_key))
        if unit.current_center_id != centers[from_key].id:
            raise CommandError(
                f"{unit.local_name} n'est pas à l'élevage {from_key} : mouvement {key} impossible. "
                "Vérifiez les mouvements existants avant de relancer."
            )
        departed_at = now - timedelta(days=days_ago)
        movement, code = declare_movement(
            movement_id=movement_id, from_center=centers[from_key], to_center=centers[to_key],
            movement_type=movement_type, items=[{"unit": unit, "quantity_sent": 1}],
            created_by=users[HOLDERS[from_key]], occurred_at=departed_at, is_simulated=True,
        )
        confirm_movement_receipt(
            movement_id=movement.id, receiver_center_id=centers[to_key].id, code=code,
            created_by=users[HOLDERS[to_key]], occurred_at=departed_at + timedelta(hours=hours),
        )
        movement.refresh_from_db()
        if movement.status != "confirmed":
            raise CommandError(f"Mouvement {key} non confirmé (statut {movement.status}).")
        self.created.append(f"mouvement {from_key} -> {to_key}")
