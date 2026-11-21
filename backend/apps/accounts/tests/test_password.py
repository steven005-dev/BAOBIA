"""POST /api/auth/password/ : l'utilisateur change son mot de passe."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditLog

from .helpers import make_user

URL = "/api/auth/password/"


class PasswordChangeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = make_user("+2250000000051", "Éleveur test")
        self.user.set_password("48271930")
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_change_password(self):
        resp = self.client.post(URL, {"current_password": "48271930",
                                      "new_password": "Mon-Troupeau-2026"}, format="json")
        self.assertEqual(resp.status_code, 204, resp.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Mon-Troupeau-2026"))
        log = AuditLog.objects.get(action="auth.password_change")
        self.assertNotIn("Mon-Troupeau-2026", str(log.details))

    def test_wrong_current_password(self):
        resp = self.client.post(URL, {"current_password": "faux", "new_password": "Mon-Troupeau-2026"},
                                format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("actuel incorrect", resp.json()["detail"])

    def test_too_simple_refused(self):
        resp = self.client.post(URL, {"current_password": "48271930", "new_password": "123"},
                                format="json")
        self.assertEqual(resp.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("48271930"))

    def test_anonymous_refused(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(URL, {}, format="json").status_code, 401)
