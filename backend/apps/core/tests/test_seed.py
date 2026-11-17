"""manage.py seed : idempotence, contenu, et périmètre (aucune donnée hors de nos modules)."""

import os
from io import StringIO
from unittest import mock

from django.apps import apps
from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.accounts import services as accounts_services
from apps.accounts.models import Habilitation, Membership, Organization, Role, User
from apps.audit.models import AuditLog
from apps.core.models import Species
from apps.geo.models import Zone
from apps.identity.models import (
    Animal, Center, CenterMember, IdentitySupport, Label, LabelBatch, Lot, TrackedUnit,
)
from apps.identity.services import accessible_centers, is_valid_short_code

DEMO_PASSWORD = "Demo-baobia-2026"
MODELS = (Role, Species, Zone, Organization, User, Membership, Habilitation, Center,
          CenterMember, TrackedUnit, Animal, Lot, LabelBatch, Label, IdentitySupport, AuditLog)
DEMO_PHONES = [f"+225000000000{i}" for i in range(1, 7)]


def seed(*args, password=DEMO_PASSWORD):
    env = {"SEED_DEMO_PASSWORD": password} if password is not None else {}
    with mock.patch.dict(os.environ, env, clear=False):
        if password is None:
            os.environ.pop("SEED_DEMO_PASSWORD", None)
        out = StringIO()
        call_command("seed", *args, stdout=out)
        return out.getvalue()


def snapshot():
    return {m.__name__: sorted(str(pk) for pk in m.objects.values_list("pk", flat=True)) for m in MODELS}


class SeedReferenceTests(TestCase):
    def test_reference_only_without_demo(self):
        seed(password=None)
        self.assertEqual(set(Role.objects.values_list("code", flat=True)),
                         {"breeder", "field_agent", "veterinarian", "authority", "trader"})
        modes = dict(Species.objects.values_list("code", "tracking_mode"))
        self.assertEqual(modes, {"cattle": "animal", "sheep": "animal", "goat": "animal",
                                 "pig": "animal", "poultry": "lot"})
        for model in (User, Zone, Center, TrackedUnit, Label):
            self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_reference_is_idempotent(self):
        seed(password=None)
        before = snapshot()
        self.assertIn("Rien à créer", seed(password=None))
        self.assertEqual(snapshot(), before)


class SeedDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed("--demo")

    def test_second_run_creates_nothing_and_keeps_same_accounts(self):
        before = snapshot()
        hashes = dict(User.objects.values_list("phone", "password"))
        output = seed("--demo")
        self.assertIn("Rien à créer", output)
        self.assertEqual(snapshot(), before)  # mêmes lignes, mêmes identifiants, audit inchangé
        self.assertEqual(dict(User.objects.values_list("phone", "password")), hashes)

    def test_expected_demo_content(self):
        self.assertEqual(sorted(User.objects.values_list("phone", flat=True)), DEMO_PHONES)
        self.assertEqual(Zone.objects.filter(parent__isnull=True).count(), 1)
        self.assertEqual(Zone.objects.filter(parent__code="DEMO-CI").count(), 2)
        self.assertEqual(Organization.objects.filter(kind="veterinary_service").count(), 1)
        self.assertEqual(Center.objects.count(), 4)
        members = [CenterMember.objects.filter(center=c, ends_at__isnull=True).count()
                   for c in Center.objects.all()]
        self.assertEqual(sorted(members), [1, 1, 1, 2])
        self.assertEqual(Animal.objects.count(), 10)
        self.assertEqual(Lot.objects.count(), 2)
        self.assertEqual(LabelBatch.objects.count(), 1)
        self.assertEqual(Label.objects.count(), LabelBatch.objects.get().quantity)
        self.assertEqual(IdentitySupport.objects.filter(unbound_at__isnull=True).count(), 8)
        self.assertTrue(all(is_valid_short_code(c) for c in Label.objects.values_list("short_code", flat=True)))
        self.assertEqual(set(Label.objects.filter(identitysupport__isnull=False)
                             .values_list("status", flat=True)), {"active"})
        for unit in TrackedUnit.objects.all():
            self.assertIsNotNone(unit.current_center_id)

    def test_roles_and_vet_habilitation(self):
        expected = {"+2250000000001": "breeder", "+2250000000002": "breeder",
                    "+2250000000003": "breeder", "+2250000000004": "veterinarian",
                    "+2250000000005": "field_agent", "+2250000000006": "authority"}
        for phone, code in expected.items():
            user = User.objects.get(phone=phone)
            self.assertEqual([r.code for r in accounts_services.active_roles(user)], [code], phone)
        vet = User.objects.get(phone="+2250000000004")
        self.assertTrue(accounts_services.user_has_valid_habilitation(vet))
        self.assertEqual(AuditLog.objects.filter(action="habilitation.verify").count(), 1)
        agent = User.objects.get(phone="+2250000000005")
        self.assertEqual([c["access"] for c in accessible_centers(agent)], ["mandate"])

    def test_everything_is_simulated(self):
        for model in (User, Organization, Habilitation, Center, TrackedUnit):
            self.assertFalse(model.objects.filter(is_simulated=False).exists(), model.__name__)
        self.assertFalse(Zone.objects.exclude(code__startswith="DEMO-").exists())

    def test_password_from_env_works(self):
        self.assertTrue(User.objects.get(phone="+2250000000004").check_password(DEMO_PASSWORD))

    def test_nothing_written_for_other_modules(self):
        for label in ("traceability", "health", "alerts", "sync", "notifications"):
            for model in apps.get_app_config(label).get_models():
                self.assertEqual(model.objects.count(), 0, model.__name__)


class SeedSafetyTests(TestCase):
    def test_demo_requires_password_env(self):
        with self.assertRaisesMessage(CommandError, "SEED_DEMO_PASSWORD"):
            seed("--demo", password=None)
        self.assertEqual(User.objects.count(), 0)

    def test_weak_demo_password_is_refused(self):
        with self.assertRaises(CommandError):
            seed("--demo", password="1234")
        self.assertEqual(User.objects.count(), 0)

    def test_refuses_to_touch_a_non_simulated_account(self):
        User.objects.create_user("+2250000000004", "Un-vrai-compte-1", full_name="Compte réel")
        with self.assertRaisesMessage(CommandError, "non simulé"):
            seed("--demo")
        self.assertEqual(Center.objects.count(), 0)  # transaction annulée
