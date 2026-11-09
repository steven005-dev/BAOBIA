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
