"""Protections de la base pour health (docs/BAOBIA_DB_SPEC.md, section 7.1).

health_event et health_report_review sont en ajout seul : tout UPDATE ou DELETE
est refusé par la base, même par du SQL direct.

La fonction forbid_update_delete() est partagée avec d'autres applications :
elle est (re)créée ici avec CREATE OR REPLACE mais jamais supprimée au retour
arrière (seuls les triggers de cette application le sont).
"""

from django.db import migrations

APPEND_ONLY_TABLES = ("health_event", "health_report_review")

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;
""" + "".join(
    f"""
CREATE TRIGGER trg_{table}_append_only
BEFORE UPDATE OR DELETE ON {table}
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();
"""
    for table in APPEND_ONLY_TABLES
)

REVERSE_SQL = "".join(
    f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table};\n"
    for table in APPEND_ONLY_TABLES
)


class Migration(migrations.Migration):
    dependencies = [
        ("health", "0001_initial"),
        ("identity", "0002_protections"),
    ]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
