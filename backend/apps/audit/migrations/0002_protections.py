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


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
