"""GET /api/auth/me/ : uniquement l'utilisateur connecté."""

import json
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Mandate
from apps.identity import services as identity_services

from .helpers import give_role, make_center, make_habilitation, make_user

ME = "/api/auth/me/"


class MeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.vet = make_user("+2250000000041", "Vétérinaire test")
        self.other = make_user("+2250000000042", "Autre éleveur secret")
        self.agent = make_user("+2250000000043", "Agent test")
        verifier = make_user("+2250000000044", "Vérificateur")

        give_role(self.vet, "veterinarian")
        give_role(self.vet, "authority", ends_at=timezone.now() - timedelta(hours=1),
                  starts_at=timezone.now() - timedelta(days=5))  # rôle terminé
        give_role(self.other, "breeder")
        make_habilitation(self.vet, verifier=verifier)
        make_habilitation(self.other, verifier=verifier, ref="OTHER-1")

        self.vet_center = make_center(self.vet, name="Élevage du vétérinaire")
        self.other_center = make_center(self.other, name="Élevage privé de l'autre")
        self.mandated = make_center(self.other, name="Élevage sous mandat")

    def me(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = self.client.get(ME)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(ME).status_code, 401)

    def test_vet_profile(self):
        data = self.me(self.vet)
        self.assertEqual(data["id"], str(self.vet.id))
        self.assertEqual([r["code"] for r in data["roles"]], ["veterinarian"])
        self.assertTrue(data["has_valid_habilitation"])
        self.assertEqual([c["name"] for c in data["accessible_centers"]], ["Élevage du vétérinaire"])
        self.assertEqual(data["accessible_centers"][0]["access"], "holder")
        self.assertNotIn("password", data)

    def test_me_reveals_nothing_about_another_user(self):
        text = json.dumps(self.me(self.vet))
        for leak in (str(self.other.id), self.other.phone, self.other.full_name,
                     str(self.other_center.id), self.other_center.name, "OTHER-1"):
            self.assertNotIn(leak, text)

    def test_mandate_gives_center_until_revoked(self):
        mandate = identity_services.grant_mandate(self.agent, self.other, [self.mandated], "move")
        centers = self.me(self.agent)["accessible_centers"]
        self.assertEqual([(c["name"], c["access"], c["mandate_scope"]) for c in centers],
                         [("Élevage sous mandat", "mandate", "move")])
        Mandate.objects.filter(pk=mandate.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.me(self.agent)["accessible_centers"], [])
        self.assertFalse(self.me(self.agent)["has_valid_habilitation"])
