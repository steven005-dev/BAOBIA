"""Connexion, refresh, déconnexion et limitation des essais."""

import json

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.audit.models import AuditLog

from .helpers import PASSWORD, make_user

LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/refresh/"
LOGOUT = "/api/auth/logout/"
ME = "/api/auth/me/"
LOGIN_FAILED = "Numéro ou mot de passe incorrect."


def rates(phone="100/minute", ip="100/minute"):
    return override_settings(REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {"login_phone": phone, "login_ip": ip},
    })


class AuthTestCase(TestCase):
    def setUp(self):
        cache.clear()  # compteurs de limitation remis à zéro entre les tests
        self.client = APIClient()
        self.user = make_user("+2250000000099")

    def login(self, phone="+2250000000099", password=PASSWORD, **extra):
        return self.client.post(LOGIN, {"phone": phone, "password": password}, format="json", **extra)

    def tokens(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()


@rates()
class LoginTests(AuthTestCase):
    def test_login_ok_returns_token_pair(self):
        data = self.tokens()
        self.assertEqual(set(data), {"access", "refresh"})
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_login_accepts_national_and_spaced_formats(self):
        for phone in ("00 00 00 00 99", "+225 00-00-00-00-99", "002250000000099"):
            self.assertEqual(self.login(phone=phone).status_code, 200, phone)

    def test_wrong_password_unknown_phone_inactive_and_garbage_are_neutral(self):
        inactive = make_user("+2250000000098", is_active=False)
        cases = [
            ("+2250000000099", "mauvais-mot"),
            ("+2250000000077", PASSWORD),
            (inactive.phone, PASSWORD),
            ("pas un numéro", PASSWORD),
        ]
        for phone, password in cases:
            response = self.login(phone=phone, password=password)
            self.assertEqual(response.status_code, 401, phone)
            self.assertEqual(response.json(), {"detail": LOGIN_FAILED})

    def test_missing_fields_is_400(self):
        response = self.client.post(LOGIN, {"phone": "+2250000000099"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())

    def test_stale_authorization_header_does_not_block_login(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer jeton-perime")
        self.assertEqual(self.login().status_code, 200)


@rates()
class RefreshLogoutTests(AuthTestCase):
    def test_refresh_gives_new_access_that_works(self):
        tokens = self.tokens()
        response = self.client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
        self.assertEqual(self.client.get(ME).status_code, 200)

    def test_refresh_refused_for_garbage_and_inactive_user(self):
        tokens = self.tokens()
        bad = self.client.post(REFRESH, {"refresh": "abc"}, format="json")
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(bad.json(), {"detail": "Session expirée. Connectez-vous à nouveau."})
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(
            self.client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code, 401
        )

    def test_logout_blacklists_refresh_and_is_replayable(self):
        tokens = self.tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code, 204)
        # Rejouée (file hors ligne) : toujours 204, une seule ligne d'audit.
        self.assertEqual(self.client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code, 204)
        self.assertEqual(AuditLog.objects.filter(action="auth.logout").count(), 1)
        self.assertEqual(
            self.client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code, 401
        )

    def test_logout_refuses_refresh_of_another_user(self):
        other = make_user("+2250000000088")
        other_tokens = self.login(phone=other.phone).json()
        mine = self.tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {mine['access']}")
        response = self.client.post(LOGOUT, {"refresh": other_tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, 400)
        # Le refresh de l'autre utilisateur marche toujours.
        self.assertEqual(
            self.client.post(REFRESH, {"refresh": other_tokens["refresh"]}, format="json").status_code, 200
        )

    def test_logout_requires_authentication(self):
        tokens = self.tokens()
        self.assertEqual(self.client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code, 401)

    def test_access_token_refused_once_account_disabled(self):
        tokens = self.tokens()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.client.get(ME).status_code, 401)


class ThrottleTests(AuthTestCase):
    @rates(phone="3/minute")
    def test_phone_throttle_after_n_attempts_whatever_the_format(self):
        for phone in ("+2250000000099", "00 00 00 00 99", "+225 0000000099"):
            self.assertEqual(self.login(phone=phone, password="mauvais").status_code, 401)
        # 4e essai, même avec le bon mot de passe et une autre IP : bloqué.
        response = self.login(REMOTE_ADDR="10.0.0.9")
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response.json()["detail"].startswith("Trop d'essais."))
        # Un autre numéro n'est pas bloqué.
        make_user("+2250000000066")
        self.assertEqual(self.login(phone="+2250000000066").status_code, 200)

    @rates(ip="3/minute")
    def test_ip_throttle_after_n_attempts_across_numbers(self):
        for i in range(3):
            self.login(phone=f"+22500000001{i}0", password="mauvais", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(self.login(REMOTE_ADDR="10.0.0.1").status_code, 429)
        self.assertEqual(self.login(REMOTE_ADDR="10.0.0.2").status_code, 200)

    @rates(ip="2/minute")
    def test_forged_forwarded_for_header_does_not_bypass_ip_limit(self):
        for i in range(2):
            self.login(password="mauvais", HTTP_X_FORWARDED_FOR=f"1.2.3.{i}")
        self.assertEqual(self.login(HTTP_X_FORWARDED_FOR="9.9.9.9").status_code, 429)


@rates()
class AuditTests(AuthTestCase):
    def test_audit_has_expected_events_and_no_secret(self):
        self.login(password="mauvais-mot")
        tokens = self.tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json")

        actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
        self.assertEqual(actions, ["auth.login_failed", "auth.login", "auth.logout"])
        failed = AuditLog.objects.get(action="auth.login_failed")
        self.assertIsNone(failed.actor_user_id)
        self.assertEqual(failed.details["reason"], "bad_credentials")
        self.assertEqual(AuditLog.objects.get(action="auth.login").actor_user, self.user)

        dump = json.dumps(list(AuditLog.objects.values_list("details", flat=True)))
        for secret in ("mauvais-mot", PASSWORD, tokens["access"], tokens["refresh"]):
            self.assertNotIn(secret, dump)
        self.assertNotIn("password", dump)

    def test_inactive_reason_is_recorded_but_not_returned(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.login().json(), {"detail": LOGIN_FAILED})
        self.assertEqual(AuditLog.objects.get(action="auth.login_failed").details["reason"], "inactive")

    def test_record_event_strips_secret_keys(self):
        from apps.audit.services import record_event

        entry = record_event("test.scrub", details={
            "password": "x", "refresh_token": "y", "nested": {"access": "z", "ok": 1}, "ip": "1.1.1.1",
        })
        self.assertEqual(entry.details, {"nested": {"ok": 1}, "ip": "1.1.1.1"})
