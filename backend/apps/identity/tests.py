import uuid
from datetime import datetime, timezone

from django.db import IntegrityError, connection
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import (
    Center,
    CenterMember,
    IdentitySupport,
    IdentityVerification,
    Label,
    LabelBatch,
    TrackedUnit,
)


class IdentityConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("+2250102030405", "secret", full_name="Test")
        self.zone = Zone.objects.create(level=0, code="CI", name="Cote d'Ivoire")
        self.species = Species.objects.create(
            code="cattle", label_fr="Bovin", tracking_mode="animal"
        )
        self.center = Center.objects.create(
            name="Centre test",
            zone=self.zone,
            center_type="farm",
            location_source="none",
            created_by=self.user,
        )
        self.unit = TrackedUnit.objects.create(
            kind="animal", species=self.species, created_by=self.user
        )
        self.batch = LabelBatch.objects.create(quantity=1, created_by=self.user)
        self.label = Label.objects.create(batch=self.batch, short_code="23456789A")

    def test_only_one_active_holder_per_center(self):
        CenterMember.objects.create(
            center=self.center,
            user=self.user,
            member_role="holder",
            starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(IntegrityError):
            CenterMember.objects.create(
                center=self.center,
                user=User.objects.create_user(
                    "+2250102030406", "secret", full_name="Other"
                ),
                member_role="holder",
                starts_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )

    def test_active_label_cannot_be_bound_to_two_units(self):
        IdentitySupport.objects.create(
            unit=self.unit,
            support_type="qr_label",
            label=self.label,
            bound_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            bound_by=self.user,
        )
        other = TrackedUnit.objects.create(
            kind="animal", species=self.species, created_by=self.user
        )
        with self.assertRaises(IntegrityError):
            IdentitySupport.objects.create(
                unit=other,
                support_type="qr_label",
                label=self.label,
                bound_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                bound_by=self.user,
            )

    def test_identity_verification_is_append_only_in_orm_and_sql(self):
        event = IdentityVerification.objects.create(
            unit=self.unit,
            method="scan",
            result="confirmed",
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            created_by=self.user,
        )
        with self.assertRaises(RuntimeError):
            event.save()
        with self.assertRaises(RuntimeError):
            event.delete()
        with connection.cursor() as cursor, self.assertRaises(Exception):
            cursor.execute(
                "UPDATE identity_verification SET result = 'mismatch' WHERE id = %s",
                [event.id],
            )
        with connection.cursor() as cursor, self.assertRaises(Exception):
            cursor.execute("DELETE FROM identity_verification WHERE id = %s", [event.id])


class IdentityServicesTests(TestCase):
    """Fonctions publiques de identity.services."""

    def setUp(self):
        from apps.identity import services

        self.services = services
        self.user = User.objects.create_user("+2250102030407", "Baobia-test-2026", full_name="Test")
        self.zone = Zone.objects.create(level=0, code="CI-S", name="Zone")
        self.cattle = Species.objects.create(code="cattle", label_fr="Bovin", tracking_mode="animal")
        self.poultry = Species.objects.create(code="poultry", label_fr="Volaille", tracking_mode="lot")
        self.center = services.create_center(
            name="Élevage", zone=self.zone, center_type="farm", created_by=self.user, holder=self.user
        )

    def test_check_char_detects_typos_and_swaps(self):
        code = self.services.make_short_code("23456789")
        self.assertTrue(self.services.is_valid_short_code(code))
        self.assertTrue(self.services.is_valid_short_code(f" {code[:4]}-{code[4:].lower()} "))
        alphabet = self.services.SHORT_CODE_ALPHABET
        for i in range(9):  # toute faute sur un seul caractère est détectée
            for char in alphabet:
                if char != code[i]:
                    self.assertFalse(self.services.is_valid_short_code(code[:i] + char + code[i + 1:]))
        self.assertFalse(self.services.is_valid_short_code("23456789O"))  # O interdit

    def test_label_batch_and_binding(self):
        batch = self.services.create_label_batch(quantity=3, created_by=self.user)
        labels = list(Label.objects.filter(batch=batch))
        self.assertEqual(len(labels), 3)
        self.assertTrue(all(self.services.is_valid_short_code(l.short_code) for l in labels))
        unit = self.services.register_animal(
            species=self.cattle, center=self.center, created_by=self.user, label=labels[0]
        )
        labels[0].refresh_from_db()
        self.assertEqual(labels[0].status, "active")
        self.assertEqual(unit.current_center, self.center)
        other = self.services.register_animal(species=self.cattle, center=self.center, created_by=self.user)
        with self.assertRaises(self.services.IdentityError):
            self.services.bind_label(other, labels[0], self.user)  # déjà posée
        with self.assertRaises(self.services.IdentityError):
            self.services.bind_label(unit, labels[1], self.user)  # l'animal a déjà une étiquette

    def test_species_tracking_mode_is_enforced(self):
        with self.assertRaises(self.services.IdentityError):
            self.services.register_animal(species=self.poultry, center=self.center, created_by=self.user)
        lot = self.services.register_lot(species=self.poultry, center=self.center, size=30, created_by=self.user)
        self.assertEqual(lot.lot.current_size, 30)
