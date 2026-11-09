from datetime import datetime, timezone

from django.db import connection
from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog


class AuditLogProtectionTests(TestCase):
    def test_audit_log_is_append_only_in_sql(self):
        user = User.objects.create_user("+2250102030405", "secret", full_name="Test")
        entry = AuditLog.objects.create(
            actor_user=user,
            action="test",
            entity_table="app_user",
            at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(RuntimeError):
            entry.save()
        with self.assertRaises(RuntimeError):
            entry.delete()
        with connection.cursor() as cursor, self.assertRaises(Exception):
            cursor.execute("UPDATE audit_log SET action = 'changed' WHERE id = %s", [entry.id])
        with connection.cursor() as cursor, self.assertRaises(Exception):
            cursor.execute("DELETE FROM audit_log WHERE id = %s", [entry.id])
