from django.db import migrations


FORWARD_SQL = """
-- Fonction générique forbid_update_delete si non existante
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table % en ajout seul : % interdit', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

-- 7.1 Triggers append-only pour les événements immuables
CREATE TRIGGER trg_movement_confirmation_append_only
BEFORE UPDATE OR DELETE ON movement_confirmation
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();

CREATE TRIGGER trg_movement_status_event_append_only
BEFORE UPDATE OR DELETE ON movement_status_event
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();

CREATE TRIGGER trg_status_event_append_only
BEFORE UPDATE OR DELETE ON status_event
FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();

-- 7.3 Quantité d'un animal (movement_item)
CREATE OR REPLACE FUNCTION check_movement_item_animal_quantity() RETURNS trigger AS $$
DECLARE
  unit_kind varchar(6);
BEGIN
  SELECT kind INTO unit_kind FROM tracked_unit WHERE id = NEW.unit_id;
  IF unit_kind = 'animal' THEN
    IF NEW.quantity_sent <> 1 THEN
      RAISE EXCEPTION 'Pour un animal individuel, quantity_sent doit être égal à 1';
    END IF;
    IF NEW.quantity_received IS NOT NULL AND NEW.quantity_received NOT IN (0, 1) THEN
      RAISE EXCEPTION 'Pour un animal individuel, quantity_received doit être 0 ou 1';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_movement_item_animal_quantity
BEFORE INSERT OR UPDATE ON movement_item
FOR EACH ROW EXECUTE FUNCTION check_movement_item_animal_quantity();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_movement_confirmation_append_only ON movement_confirmation;
DROP TRIGGER IF EXISTS trg_movement_status_event_append_only ON movement_status_event;
DROP TRIGGER IF EXISTS trg_status_event_append_only ON status_event;
DROP TRIGGER IF EXISTS trg_movement_item_animal_quantity ON movement_item;
DROP FUNCTION IF EXISTS check_movement_item_animal_quantity();
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
    dependencies = [("traceability", "0001_initial")]
    operations = [migrations.RunPython(apply_protection, revert_protection)]
