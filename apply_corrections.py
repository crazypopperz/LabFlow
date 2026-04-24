import psycopg2

NOUVELLE = "postgresql://neondb_owner:npg_Z1bLohDN3nmG@ep-late-rain-algv7iht.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

corrections = [
    # Colonnes manquantes
    "ALTER TABLE documents_reglementaires ADD COLUMN IF NOT EXISTS fichier_pdf bytea;",
    "ALTER TABLE inventaires_archives ADD COLUMN IF NOT EXISTS fichier_pdf bytea;",
    "ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS salle_id integer;",
    "ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS recurrence_data text;",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS salle_id integer;",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS recurrence_id integer;",

    # Corrections de types : integer -> boolean
    "ALTER TABLE echeances ALTER COLUMN traite TYPE boolean USING traite::boolean;",
    "ALTER TABLE objets ALTER COLUMN en_commande TYPE boolean USING en_commande::boolean;",
    "ALTER TABLE objets ALTER COLUMN traite TYPE boolean USING traite::boolean;",
]

print("Connexion à la nouvelle base...")
conn = psycopg2.connect(NOUVELLE)
conn.autocommit = False
cur = conn.cursor()

try:
    for sql in corrections:
        print(f"  ▶ {sql}")
        cur.execute(sql)
    conn.commit()
    print("\n✅ Toutes les corrections ont été appliquées avec succès !")
except Exception as e:
    conn.rollback()
    print(f"\n❌ Erreur : {e}")
    print("⚠️  Rollback effectué, aucune modification appliquée.")
finally:
    cur.close()
    conn.close()