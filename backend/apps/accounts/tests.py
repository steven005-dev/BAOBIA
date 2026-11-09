import os
from datetime import date, timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog
from apps.identity.models import Center, CenterMember

from .models import Habilitation, User
from .permissions import HasValidHabilitation
from apps.geo.models import Zone


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "DemoPassword-42"
        self.user = User.objects.create_user(
            "+2250000000099", self.password, full_name="Utilisateur test"
        )

    def test_login_refresh_logout_and_me(self):
        response = self.client.post(
            "/api/auth/login/",
            {"phone": "2250000000099", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        tokens = response.json()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["phone"], self.user.phone)
        self.assertNotIn("password", me.json())
        self.assertTrue(
            AuditLog.objects.filter(action="login_succeeded", actor_user=self.user).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="habilitation_checked", actor_user=self.user).exists()
        )
        refresh = self.client.post(
            "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(refresh.status_code, 200)
        logout = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(logout.status_code, 204)
        self.assertTrue(AuditLog.objects.filter(action="logout", actor_user=self.user).exists())
        self.assertEqual(
            self.client.post(
                "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
            ).status_code,
            401,
        )

    def test_invalid_and_inactive_login_are_neutral(self):
        for password in ("wrong", self.password):
            if password == self.password:
                self.user.is_active = False
                self.user.save(update_fields=["is_active"])
            response = self.client.post(
                "/api/auth/login/",
                {"phone": self.user.phone, "password": password},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["non_field_errors"], ["Identifiants invalides."])
        self.assertFalse(AuditLog.objects.filter(details__has_key="password").exists())

    @override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"login": "2/minute"}})
    def test_login_throttle(self):
        for _ in range(2):
            self.client.post(
                "/api/auth/login/",
                {"phone": self.user.phone, "password": "wrong"},
                format="json",
            )
        response = self.client.post(
            "/api/auth/login/",
            {"phone": self.user.phone, "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 429)

    def test_expired_revoked_and_unverified_habilitation_are_rejected(self):
        permission = HasValidHabilitation()
        request = type("Request", (), {"user": self.user})()
        verifier = User.objects.create_user("+2250000000097", self.password, full_name="Vérificateur")
        for status, valid_to, verified_by in (
            ("verified", date.today() - timedelta(days=1), verifier),
            ("revoked", date.today() + timedelta(days=1), verifier),
            ("pending", date.today() + timedelta(days=1), None),
        ):
            Habilitation.objects.create(
                user=self.user,
                kind="vet_order",
                reference_number=f"REF-{status}",
                valid_from=date.today() - timedelta(days=2),
                valid_to=valid_to,
                status=status,
                verified_by=verified_by,
            )
            self.assertFalse(permission.has_permission(request, None))

    def test_me_only_returns_authenticated_user_centers(self):
        other = User.objects.create_user("+2250000000098", self.password, full_name="Autre")
        center = Center.objects.create(
            name="Centre privé",
            zone=Zone.objects.create(code="TEST", level=0, name="Zone test"),
            center_type="farm",
            location_source="none",
            created_by=self.user,
        )
        CenterMember.objects.create(
            center=center,
            user=other,
            member_role="holder",
            starts_at=timezone.now(),
        )
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.json()["accessible_centers"], [])
