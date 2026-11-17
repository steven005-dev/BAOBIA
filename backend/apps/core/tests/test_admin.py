"""Les pages d'administration de nos modules s'ouvrent ; les tables protégées sont en lecture seule."""

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

OUR_APPS = ("core", "accounts", "identity", "notifications", "audit")


class AdminPagesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("+2250000000900", "Admin-test-2026", full_name="Admin")
        self.client.force_login(self.admin)

    def test_every_changelist_opens(self):
        models = [m for m in admin.site._registry if m._meta.app_label in OUR_APPS]
        self.assertGreaterEqual(len(models), 15)
        for model in models:
            url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_audit_is_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:audit_auditlog_add")).status_code, 403)
