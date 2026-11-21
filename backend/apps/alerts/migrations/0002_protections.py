"""Protections de la base pour alerts (docs/BAOBIA_DB_SPEC.md, sections 7.1 et 7.4).

- alert_review et alert_event : ajout seul (UPDATE et DELETE refusés).
- disease_rule : une règle déjà utilisée par une alerte ne se modifie plus ; on crée
  la version suivante (l'alerte reste explicable après un changement de règle).

forbid_update_delete() est partagée : recréée avec CREATE OR REPLACE, jamais supprimée.
"""

from django.db import migrations

APPEND_ONLY_TABLES = ("alert_review", "alert_event")

FORWARD_SQL = """
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION forbid_used_disease_rule_update() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM alert WHERE rule_id = OLD.id) THEN
    RAISE EXCEPTION 'Règle sanitaire % déjà utilisée par une alerte : créez une nouvelle version', OLD.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_disease_rule_frozen
BEFORE UPDATE ON disease_rule
FOR EACH ROW EXECUTE FUNCTION forbid_used_disease_rule_update();
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
) + """
DROP TRIGGER IF EXISTS trg_disease_rule_frozen ON disease_rule;
DROP FUNCTION IF EXISTS forbid_used_disease_rule_update();
"""


class Migration(migrations.Migration):
    dependencies = [("alerts", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
