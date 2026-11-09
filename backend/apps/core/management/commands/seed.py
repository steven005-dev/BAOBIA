import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Habilitation, Membership, Organization, Role, User
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import (
    Animal,
    Center,
    CenterMember,
    CenterSpecies,
    IdentitySupport,
    Label,
    LabelBatch,
    Lot,
    TrackedUnit,
)


class Command(BaseCommand):
    help = "Charge les catalogues BAOBIA et, avec --demo, des données simulées."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute les données simulées.")

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {
            code: Role.objects.get_or_create(
                code=code, defaults={"label_fr": label}
            )[0]
            for code, label in (
                ("breeder", "Éleveur"),
                ("field_agent", "Agent de terrain"),
                ("veterinarian", "Vétérinaire"),
                ("authority", "Autorité"),
                ("trader", "Commerçant"),
            )
        }
        species = {
            code: Species.objects.get_or_create(
                code=code, defaults={"label_fr": label, "tracking_mode": mode}
            )[0]
            for code, label, mode in (
                ("cattle", "Bovin", "animal"),
                ("sheep", "Ovin", "animal"),
                ("goat", "Caprin", "animal"),
                ("pig", "Porcin", "animal"),
                ("poultry", "Volaille", "lot"),
            )
        }
        if options["demo"]:
            password = os.environ.get("SEED_DEMO_PASSWORD")
            if not password:
                raise CommandError("SEED_DEMO_PASSWORD est requis avec --demo.")
            self._seed_demo(roles, species, password)
        self.stdout.write(self.style.SUCCESS("Seed terminé."))

    def _seed_demo(self, roles, species, password):
        now = timezone.now()
        root, _ = Zone.objects.get_or_create(
            code="DEMO-CI", defaults={"level": 0, "name": "Zone démonstration"}
        )
        zones = []
        for code, name in (("DEMO-NORD", "Sous-zone Nord"), ("DEMO-SUD", "Sous-zone Sud")):
            zone, _ = Zone.objects.get_or_create(
                code=code, defaults={"level": 1, "name": name, "parent": root}
            )
            zones.append(zone)

        def user(phone, name):
            obj, created = User.objects.get_or_create(
                phone=phone,
                defaults={"full_name": name, "is_simulated": True, "is_active": True},
            )
            if created:
                obj.set_password(password)
                obj.save(update_fields=["password"])
            return obj

        breeders = [user(f"+225000000000{i}", f"Éleveur démo {i}") for i in range(1, 4)]
        veterinarian = user("+2250000000004", "Vétérinaire démo")
        field_agent = user("+2250000000005", "Agent terrain démo")
        authority = user("+2250000000006", "Autorité démo")
        organization, _ = Organization.objects.get_or_create(
            name="Service vétérinaire démo",
            kind="veterinary_service",
            defaults={"zone": zones[0], "is_simulated": True},
        )

        for person, role in (
            [(item, roles["breeder"]) for item in breeders]
            + [(veterinarian, roles["veterinarian"]), (field_agent, roles["field_agent"]), (authority, roles["authority"])]
        ):
            Membership.objects.get_or_create(
                user=person,
                role=role,
                organization=organization,
                defaults={"zone": zones[0], "starts_at": now},
            )
        Habilitation.objects.get_or_create(
            user=veterinarian,
            kind="vet_order",
            reference_number="DEMO-HAB-001",
            defaults={
                "valid_from": now.date() - timedelta(days=1),
                "valid_to": now.date() + timedelta(days=365),
                "status": "verified",
                "verified_by": authority,
                "verified_at": now,
                "is_simulated": True,
            },
        )

        centers = []
        for index, owner in enumerate(breeders + [veterinarian], 1):
            center, _ = Center.objects.get_or_create(
                name=f"Centre démo {index}",
                defaults={
                    "zone": zones[(index - 1) % 2],
                    "center_type": "farm",
                    "location_source": "none",
                    "created_by": authority,
                    "is_simulated": True,
                },
            )
            centers.append(center)
            CenterMember.objects.get_or_create(
                center=center,
                user=owner,
                defaults={"member_role": "holder", "starts_at": now},
            )
            if index == 1:
                CenterMember.objects.get_or_create(
                    center=center,
                    user=field_agent,
                    defaults={"member_role": "worker", "starts_at": now},
                )
            CenterSpecies.objects.get_or_create(center=center, species=species["cattle"])

        units = []
        for index in range(10):
            unit, _ = TrackedUnit.objects.get_or_create(
                kind="animal",
                species=species["cattle"],
                local_name=f"Animal démo {index + 1}",
                defaults={"current_center": centers[index % 4], "created_by": breeders[index % 3], "is_simulated": True},
            )
            Animal.objects.get_or_create(unit=unit, defaults={"sex": "unknown"})
            units.append(unit)
        for index in range(2):
            unit, _ = TrackedUnit.objects.get_or_create(
                kind="lot",
                species=species["poultry"],
                local_name=f"Lot volaille démo {index + 1}",
                defaults={"current_center": centers[index], "created_by": breeders[index], "is_simulated": True},
            )
            Lot.objects.get_or_create(unit=unit, defaults={"current_size": 100 + index * 25})

        batch, _ = LabelBatch.objects.get_or_create(
            note="Étiquettes démo",
            defaults={"quantity": 12, "created_by": field_agent},
        )
        codes = ("23456789A", "23456789B", "23456789C", "23456789D", "23456789E", "23456789F")
        for index, code in enumerate(codes):
            label, _ = Label.objects.get_or_create(
                short_code=code,
                defaults={"batch": batch, "status": "active", "issued_to_center": centers[index % 4]},
            )
            if index < len(units):
                IdentitySupport.objects.get_or_create(
                    unit=units[index],
                    support_type="qr_label",
                    defaults={"label": label, "bound_at": now, "bound_by": field_agent},
                )
