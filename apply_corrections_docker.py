import psycopg2

DOCKER = "postgresql://crazypopperz:Xav-Docker-Desktop-2025@localhost:5432/labflow_db"

corrections = [
    "ALTER TABLE documents_reglementaires ADD COLUMN IF NOT EXISTS fichier_pdf bytea;",
    "ALTER TABLE inventaires_archives ADD COLUMN IF NOT EXISTS fichier_pdf bytea;",
    "ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS salle_id integer;",
    "ALTER TABLE panier_items ADD COLUMN IF NOT EXISTS recurrence_data text;",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS salle_id integer;",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS recurrence_id integer;",
    "ALTER TABLE echeances ALTER COLUMN traite TYPE boolean USING traite::boolean;",
    "ALTER TABLE objets ALTER COLUMN en_commande TYPE boolean USING en_commande::boolean;",
    "ALTER TABLE objets ALTER COLUMN traite TYPE boolean USING traite::boolean;",
]

print("Connexion à la base Docker locale...")
conn = psycopg2.connect(DOCKER)
conn.autocommit = False
cur = conn.cursor()

try:
    for sql in corrections:
        print(f"  ▶ {sql}")
        cur.execute(sql)
    conn.commit()
    print("\n✅ Toutes les corrections ont été appliquées sur Docker !")
except Exception as e:
    conn.rollback()
    print(f"\n❌ Erreur : {e}")
    print("⚠️  Rollback effectué, aucune modification appliquée.")
finally:
    cur.close()
    conn.close()