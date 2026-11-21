"""manage.py seed_demo_rfid

Données de la démonstration « boucle RFID et marché » (guide de réalisation des ajouts,
21/11), toutes simulées. À lancer après `seed --demo` et `seed_demo_traceability`,
de préférence LE MATIN DE LA DÉMO : le bilan du marché compte les scans du jour.

| Bovin | Boucle              | Situation                                   |
|-------|---------------------|---------------------------------------------|
| A     | 384 000 000 000 101 | à l'Élevage B, normal (Entrée -> ligne verte) |
| B     | 384 000 000 000 102 | déjà au marché (Sortie -> parcours Probable)  |
| C     | 384 000 000 000 103 | transfert A -> B confirmé des deux côtés (Sûr) |
| D     | 384 000 000 000 104 | à l'Élevage B, déclaré disparu (avertissement) |
| -     | 384 000 000 000 999 | aucun animal (« Animal inconnu »)             |

Plus 10 bovins scannés à l'Entrée du marché aujourd'hui (6 de la zone Nord, 4 de la zone
Sud), pour un bilan crédible. L'Animal 1 de l'Élevage A (signalement de la démo) n'est
pas touché. Toute écriture passe par identity.services et traceability.services.
Idempotent : identifiants fixes ; relancer ne crée rien en double.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.core.management.commands.seed import DEMO_USERS, demo_id
from apps.core.models import Species
from apps.identity import services as identity_services
from apps.identity.models import Center, TrackedUnit
from apps.traceability.models import Movement, RfidTag, StatusEvent
from apps.traceability.services import (
    bind_rfid_tag,
    confirm_movement_receipt,
    declare_movement,
    record_market_scan,
    record_unit_event,
)

HOLDERS = {"A": "breeder1", "B": "breeder2", "C": "breeder3", "M": "breeder3"}


class Command(BaseCommand):
    help = "Ajoute les données simulées de la démo boucle RFID et marché."

    def handle(self, *args, **options):
        self.created = []
        with transaction.atomic():
            cattle = Species.objects.filter(code="cattle").first()
            if cattle is None:
                raise CommandError("Espèce « cattle » absente : lancez d'abord `seed --demo`.")
            users = self._users()
            centers = {}
            for key in ("A", "B", "C", "M"):
                center = Center.objects.filter(id=demo_id("center", key)).first()
                if center is None:
                    raise CommandError(f"Centre {key} absent : lancez d'abord `seed --demo`.")
                centers[key] = center
            market, manager = centers["M"], users[HOLDERS["M"]]

            bovin_a = self._cow("rfid-A", "Bovin A (simulé)", centers["B"], users, "B", cattle)
            bovin_b = self._cow("rfid-B", "Bovin B (simulé)", centers["B"], users, "B", cattle)
            bovin_c = self._cow("rfid-C", "Bovin C (simulé)", centers["A"], users, "A", cattle)
            bovin_d = self._cow("rfid-D", "Bovin D (simulé)", centers["B"], users, "B", cattle)
            for cow, number, owner in ((bovin_a, "384000000000101", "B"),
                                       (bovin_b, "384000000000102", "B"),
                                       (bovin_c, "384000000000103", "A"),
                                       (bovin_d, "384000000000104", "B")):
                self._tag(cow, number, users[HOLDERS[owner]])

            # B est déjà au marché : il sera scanné à la Sortie pendant la démo.
            self._scan("rfid-B-in", market, "384000000000102", manager)
            # C : transfert A -> B confirmé des deux côtés (parcours « Sûr »).
            self._confirmed_transfer(bovin_c, centers["A"], centers["B"], users)
            # D : déclaré disparu par son éleveur (visible des seuls professionnels).
            event_id = demo_id("status_event", "rfid-D-missing")
            if not StatusEvent.objects.filter(pk=event_id).exists():
                record_unit_event(unit_id=bovin_d.pk, center_id=centers["B"].pk,
                                  event_type="missing", created_by=users[HOLDERS["B"]],
                                  event_id=event_id, note="Déclaration simulée pour la démo")
                self.created.append("Bovin D déclaré disparu")

            # 10 bovins scannés à l'Entrée aujourd'hui : 6 du Nord (B), 4 du Sud (C).
            for i in range(10):
                farm_key = "B" if i < 6 else "C"
                cow = self._cow(f"rfid-bilan-{i}", f"Bovin bilan {i + 1} (simulé)",
                                centers[farm_key], users, farm_key, cattle)
                number = f"3840000000002{i:02d}"
                self._tag(cow, number, users[HOLDERS[farm_key]])
                self._scan(f"rfid-bilan-{i}-in", market, number, manager)

        if self.created:
            self.stdout.write("Créé : " + ", ".join(self.created))
        else:
            self.stdout.write("Rien à créer : tout existe déjà.")
        self.stdout.write(self.style.SUCCESS("Démo boucle RFID et marché prête."))

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

    def _cow(self, key, name, center, users, owner_key, cattle):
        unit_id = demo_id("animal", key)
        unit = TrackedUnit.objects.filter(id=unit_id).first()
        if unit is None:
            unit = identity_services.register_animal(
                unit_id=unit_id, species=cattle, center=center,
                created_by=users[HOLDERS[owner_key]], local_name=name, sex="female",
                is_simulated=True,
            )
            self.created.append(name)
        return unit

    def _tag(self, cow, number, user):
        if not RfidTag.objects.filter(unit=cow, number=number).exists():
            bind_rfid_tag(unit_id=cow.pk, number=number, read_mode="code_scan", created_by=user,
                          tag_id=demo_id("rfid_tag", number))
            self.created.append(f"boucle {number}")

    def _scan(self, key, market, number, manager):
        _body, created = record_market_scan(
            scan_id=demo_id("market_scan", key), market=market, direction="in", code=number,
            created_by=manager,
        )
        if created:
            self.created.append(f"scan {number}")

    def _confirmed_transfer(self, cow, origin, destination, users):
        movement_id = demo_id("movement", "rfid-C-transfer")
        if Movement.objects.filter(pk=movement_id).exists():
            return
        if cow.current_center_id != origin.pk:
            raise CommandError("Bovin C n'est pas à l'Élevage A : transfert impossible.")
        movement, code = declare_movement(
            movement_id=movement_id, from_center=origin, to_center=destination,
            movement_type="sale", items=[{"unit": cow, "quantity_sent": 1}],
            created_by=users[HOLDERS["A"]], is_simulated=True,
        )
        confirm_movement_receipt(movement_id=movement.pk, receiver_center_id=destination.pk,
                                 code=code, created_by=users[HOLDERS["B"]])
        self.created.append("transfert A -> B confirmé (Bovin C)")
