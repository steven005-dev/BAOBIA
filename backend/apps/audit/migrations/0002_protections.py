from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION forbid_audit_log_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log est en ajout seul : % interdit', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_append_only
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION forbid_audit_log_update_delete();

REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC;
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log;
DROP FUNCTION IF EXISTS forbid_audit_log_update_delete();
"""


def apply_protection(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(FORWARD_SQL)


def revert_protection(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]
    operations = [migrations.RunPython(apply_protection, revert_protection)]
