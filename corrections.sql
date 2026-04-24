-- Corrections à appliquer sur la nouvelle base
-- Généré automatiquement par compare_schemas.py

ALTER TABLE documents_reglementaires ADD COLUMN IF NOT EXISTS fichier_pdf bytea;
ALTER TABLE inventaires_archives ADD COLUMN IF NOT EXISTS fichier_pdf bytea;
ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS salle_id integer;
ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS recurrence_data text;
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS salle_id integer;
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS recurrence_id integer;
