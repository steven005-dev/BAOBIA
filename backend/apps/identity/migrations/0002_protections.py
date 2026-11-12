from django.db import migrations


FORBID_FUNCTION = """
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

FORWARD_SQL = FORBID_FUNCTION + """
CREATE TRIGGER trg_identity_verification_append_only
BEFORE UPDATE OR DELETE ON identity_verification
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();

CREATE OR REPLACE FUNCTION check_tracked_unit_subtype() RETURNS trigger AS $$
DECLARE
  unit_kind varchar(6);
BEGIN
  SELECT kind INTO unit_kind FROM tracked_unit WHERE id = NEW.unit_id;
  IF unit_kind IS DISTINCT FROM 'animal' THEN
    RAISE EXCEPTION 'animal.unit_id doit référencer un tracked_unit animal';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_animal_kind
BEFORE INSERT OR UPDATE ON animal
FOR EACH ROW EXECUTE FUNCTION check_tracked_unit_subtype();

CREATE OR REPLACE FUNCTION check_lot_subtype() RETURNS trigger AS $$
DECLARE
  unit_kind varchar(6);
BEGIN
  SELECT kind INTO unit_kind FROM tracked_unit WHERE id = NEW.unit_id;
  IF unit_kind IS DISTINCT FROM 'lot' THEN
    RAISE EXCEPTION 'lot.unit_id doit référencer un tracked_unit lot';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lot_kind
BEFORE INSERT OR UPDATE ON lot
FOR EACH ROW EXECUTE FUNCTION check_lot_subtype();

CREATE OR REPLACE FUNCTION forbid_tracked_unit_kind_change() RETURNS trigger AS $$
BEGIN
  IF NEW.kind IS DISTINCT FROM OLD.kind THEN
    RAISE EXCEPTION 'tracked_unit.kind est immuable';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tracked_unit_kind_immutable
BEFORE UPDATE ON tracked_unit
FOR EACH ROW EXECUTE FUNCTION forbid_tracked_unit_kind_change();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_identity_verification_append_only ON identity_verification;
DROP TRIGGER IF EXISTS trg_animal_kind ON animal;
DROP TRIGGER IF EXISTS trg_lot_kind ON lot;
DROP TRIGGER IF EXISTS trg_tracked_unit_kind_immutable ON tracked_unit;
DROP FUNCTION IF EXISTS forbid_update_delete();
DROP FUNCTION IF EXISTS check_tracked_unit_subtype();
DROP FUNCTION IF EXISTS check_lot_subtype();
DROP FUNCTION IF EXISTS forbid_tracked_unit_kind_change();
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
    dependencies = [("identity", "0001_initial")]
    operations = [migrations.RunPython(apply_protection, revert_protection)]
