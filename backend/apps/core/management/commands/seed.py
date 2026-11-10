"""manage.py seed [--demo]

Sans option : données de référence (rôles, espèces).
--demo : ajoute des données de démonstration, toutes simulées.

Idempotent : relancer ne crée aucun doublon. Clés naturelles (code, téléphone,
short_code, numéro d'habilitation) ; pour les objets sans clé naturelle (centres,
animaux, lot d'étiquettes, mandat), un UUID fixe dérivé d'un nom (uuid5).
Toute écriture métier passe par accounts.services et identity.services.
Ne crée rien pour traceability, health, alerts.
"""

import os
import random
import uuid
from datetime import date, timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts import services as accounts_services
from apps.accounts.models import Habilitation, Organization, Role, User
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity import services as identity_services
from apps.identity.models import Center, Label, LabelBatch, TrackedUnit

ROLES = (
    ("breeder", "Éleveur"),
    ("field_agent", "Agent de terrain"),
    ("veterinarian", "Vétérinaire"),
    ("authority", "Autorité"),
    ("trader", "Commerçant"),
)

SPECIES = (
    ("cattle", "Bovin", "animal"),
    ("sheep", "Mouton", "animal"),
    ("goat", "Chèvre", "animal"),
    ("pig", "Porc", "animal"),
    ("poultry", "Volaille", "lot"),
)

# Espace de noms des UUID fixes de démonstration (ne pas changer : idempotence).
DEMO_NAMESPACE = uuid.UUID("6f1c2a7e-0b9d-4c3e-9a51-0000ba0b1a00")

DEMO_USERS = (
    # clé, téléphone fictif, nom, rôle
    ("breeder1", "+2250000000001", "Éleveur 1 (simulé)", "breeder"),
    ("breeder2", "+2250000000002", "Éleveur 2 (simulé)", "breeder"),
    ("breeder3", "+2250000000003", "Éleveur 3 (simulé)", "breeder"),
    ("vet", "+2250000000004", "Vétérinaire (simulé)", "veterinarian"),
    ("agent", "+2250000000005", "Agent de terrain (simulé)", "field_agent"),
    ("authority", "+2250000000006", "Autorité (simulée)", "authority"),
)

DEMO_CENTERS = (
    # clé, nom, type, zone, détenteur, autres membres, espèces
    ("A", "Élevage A (simulé)", "farm", "north", "breeder1", (("breeder2", "co_holder"),),
     ("cattle", "pig", "poultry")),
    ("B", "Élevage B (simulé)", "farm", "north", "breeder2", (), ("cattle", "goat")),
    ("C", "Élevage C (simulé)", "farm", "south", "breeder3", (), ("sheep", "poultry")),
    ("M", "Marché (simulé)", "market", "south", "breeder3", (), ("cattle", "sheep", "goat")),
)

DEMO_ANIMALS = (
    # n°, centre, espèce, sexe, race, étiquetée
    (1, "A", "cattle", "female", "Zébu", True),
    (2, "A", "cattle", "male", "Zébu", True),
    (3, "A", "cattle", "female", "N'Dama", True),
    (4, "A", "pig", "female", None, True),
    (5, "B", "cattle", "male", "N'Dama", True),
    (6, "B", "cattle", "female", "Baoulé", True),
    (7, "B", "goat", "female", "Naine", True),
    (8, "C", "sheep", "male", "Djallonké", True),
    (9, "C", "sheep", "female", "Djallonké", False),
    (10, "B", "goat", "male", "Naine", False),
)

DEMO_LOTS = (
    # n°, centre, espèce, effectif
    (1, "A", "poultry", 40),
    (2, "C", "poultry", 25),
)

DEMO_LABEL_COUNT = 20


def demo_id(kind, key):
    return uuid.uuid5(DEMO_NAMESPACE, f"{kind}:{key}")


def demo_short_codes(count):
    """Codes courts valides et toujours les mêmes (générateur à graine fixe)."""
    rng = random.Random("baobia-demo-labels")
    alphabet = identity_services.SHORT_CODE_ALPHABET
    codes = []
    while len(codes) < count:
        body = "".join(rng.choice(alphabet) for _ in range(identity_services.SHORT_CODE_BODY_LENGTH))
        code = identity_services.make_short_code(body)
        if code not in codes:
            codes.append(code)
    return codes


class Command(BaseCommand):
    help = "Charge les données de référence ; avec --demo, ajoute des données simulées."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute les données de démonstration.")

    def handle(self, *args, **options):
        password = None
        if options["demo"]:
            password = os.environ.get("SEED_DEMO_PASSWORD")
            if not password:
                raise CommandError("SEED_DEMO_PASSWORD est requis avec --demo (voir .env.example).")
            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                raise CommandError("SEED_DEMO_PASSWORD refusé : " + " ".join(exc.messages))

        self.created = []
        with transaction.atomic():
            roles, species = self._seed_reference()
            if options["demo"]:
                self._seed_demo(roles, species, password)

        if self.created:
            self.stdout.write("Créé : " + ", ".join(self.created))
        else:
            self.stdout.write("Rien à créer : tout existe déjà.")
        self.stdout.write(self.style.SUCCESS("Seed terminé."))

    def _count(self, label, created):
        if created:
            self.created.append(label)

    # -- Référence -----------------------------------------------------------

    def _seed_reference(self):
        roles = {}
        for code, label in ROLES:
            roles[code], created = Role.objects.get_or_create(code=code, defaults={"label_fr": label})
            self._count(f"rôle {code}", created)
        species = {}
        for code, label, mode in SPECIES:
            species[code], created = Species.objects.get_or_create(
                code=code, defaults={"label_fr": label, "tracking_mode": mode}
            )
            self._count(f"espèce {code}", created)
        return roles, species

    # -- Démonstration ---------------------------------------------------------

    def _seed_demo(self, roles, species, password):
        now = timezone.now()
        today = timezone.localdate()

        root, created = Zone.objects.get_or_create(
            code="DEMO-CI", defaults={"level": 0, "name": "Pays de démonstration (simulé)"}
        )
        self._count("zone DEMO-CI", created)
        zones = {"root": root}
        for key, code, name in (("north", "DEMO-NORD", "Zone Nord (simulée)"),
                                ("south", "DEMO-SUD", "Zone Sud (simulée)")):
            zones[key], created = Zone.objects.get_or_create(
                code=code, defaults={"level": 1, "name": name, "parent": root}
            )
            self._count(f"zone {code}", created)

        org, created = Organization.objects.get_or_create(
            id=demo_id("organization", "vet-service"),
            defaults={"name": "Service vétérinaire (simulé)", "kind": "veterinary_service",
                      "zone": root, "is_simulated": True},
        )
        self._count("organisation vétérinaire", created)

        users = {}
        for key, phone, name, _role in DEMO_USERS:
            users[key] = self._demo_user(phone, name, password)

        role_scope = {
            "breeder1": (None, zones["north"]), "breeder2": (None, zones["north"]),
            "breeder3": (None, zones["south"]), "vet": (org, root),
            "agent": (None, zones["north"]), "authority": (None, root),
        }
        for key, _phone, _name, role_code in DEMO_USERS:
            organization, zone = role_scope[key]
            accounts_services.grant_role(
                users[key], role_code, organization=organization, zone=zone, starts_at=now
            )

        self._demo_habilitation(users["vet"], users["authority"], today)
        centers = self._demo_centers(users, zones, species, now)

        mandate_id = demo_id("mandate", "agent-B")
        if not users["agent"].received_mandates.filter(id=mandate_id).exists():
            identity_services.grant_mandate(
                users["agent"], users["breeder2"], [centers["B"]], "all",
                starts_at=now, mandate_id=mandate_id,
            )
            self._count("mandat agent -> Élevage B", True)

        labels = self._demo_labels(users["agent"], centers)
        self._demo_units(users, centers, species, labels)

    def _demo_user(self, phone, name, password):
        user = User.objects.filter(phone=phone).first()
        if user is not None:
            if not user.is_simulated:
                raise CommandError(f"Le numéro {phone} appartient à un compte non simulé : arrêt.")
            return user  # mot de passe inchangé si le compte existe déjà
        user = User.objects.create_user(phone, password, full_name=name, is_simulated=True)
        self._count(f"utilisateur {phone}", True)
        return user

    def _demo_habilitation(self, vet, verifier, today):
        habilitation, created = Habilitation.objects.get_or_create(
            user=vet,
            reference_number="DEMO-HAB-0001",
            defaults={
                "kind": "vet_order",
                "valid_from": today - timedelta(days=30),
                "valid_to": date(today.year + 1, 12, 31),
                "status": "pending",
                "is_simulated": True,
            },
        )
        self._count("habilitation vétérinaire", created)
        if habilitation.status == "pending":
            accounts_services.verify_habilitation(habilitation, verifier)

    def _demo_centers(self, users, zones, species, now):
        centers = {}
        for key, name, center_type, zone_key, holder, others, species_codes in DEMO_CENTERS:
            center = Center.objects.filter(id=demo_id("center", key)).first()
            if center is None:
                center = identity_services.create_center(
                    center_id=demo_id("center", key), name=name, zone=zones[zone_key],
                    center_type=center_type, created_by=users["agent"], holder=users[holder],
                    species=[species[c] for c in species_codes], is_simulated=True,
                    starts_at=now,
                )
                self._count(f"centre {key}", True)
            for member_key, member_role in others:
                identity_services.add_center_member(
                    center, users[member_key], member_role, starts_at=now
                )
            centers[key] = center
        return centers

    def _demo_labels(self, agent, centers):
        batch_id = demo_id("label_batch", "demo-1")
        codes = demo_short_codes(DEMO_LABEL_COUNT)
        if not LabelBatch.objects.filter(id=batch_id).exists():
            identity_services.create_label_batch(
                batch_id=batch_id, quantity=DEMO_LABEL_COUNT, created_by=agent, codes=codes,
                note="Étiquettes de démonstration (simulées)",
            )
            # Les 4 étiquettes après celles des animaux : remises (vierges) aux élevages A et B.
            spare = list(Label.objects.filter(short_code__in=codes[8:12]).order_by("short_code"))
            identity_services.issue_labels(spare[:2], centers["A"], issued_by=agent)
            identity_services.issue_labels(spare[2:], centers["B"], issued_by=agent)
            self._count(f"{DEMO_LABEL_COUNT} étiquettes", True)
        return {code: Label.objects.get(short_code=code) for code in codes}

    def _demo_units(self, users, centers, species, labels):
        codes = list(labels)
        holders = {key: users[holder] for key, _n, _t, _z, holder, _o, _s in DEMO_CENTERS}
        label_index = 0
        for number, center_key, species_code, sex, breed, tagged in DEMO_ANIMALS:
            label = None
            if tagged:
                label = labels[codes[label_index]]
                label_index += 1
            unit_id = demo_id("animal", number)
            if TrackedUnit.objects.filter(id=unit_id).exists():
                continue
            identity_services.register_animal(
                unit_id=unit_id, species=species[species_code], center=centers[center_key],
                created_by=holders[center_key], local_name=f"Animal {number} (simulé)",
                sex=sex, breed=breed, label=label, is_simulated=True,
            )
            self._count(f"animal {number}", True)
        for number, center_key, species_code, size in DEMO_LOTS:
            unit_id = demo_id("lot", number)
            if TrackedUnit.objects.filter(id=unit_id).exists():
                continue
            identity_services.register_lot(
                unit_id=unit_id, species=species[species_code], center=centers[center_key],
                size=size, created_by=holders[center_key], local_name=f"Lot {number} (simulé)",
                description="Volaille (simulée)", is_simulated=True,
            )
            self._count(f"lot {number}", True)
