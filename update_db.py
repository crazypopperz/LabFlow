# update_db.py
from app import create_app, db  # <--- On importe la factory, pas 'app'
from sqlalchemy import text

# 1. On crée l'application manuellement
app = create_app()

with app.app_context():
    print("🔌 Connexion à la base de données...")
    
    # 2. Création des nouvelles tables (Paniers, Audit, etc.)
    print("🛠️  Création des tables manquantes...")
    db.create_all()
    
    # 3. Patch manuel pour la table Reservation
    try:
        print("🔄 Vérification de la table 'reservations'...")
        with db.engine.connect() as conn:
            # On vérifie si la colonne groupe_id existe
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='reservations' AND column_name='groupe_id'"))
            
            if not result.scalar():
                print("⚠️  Colonne 'groupe_id' manquante. Ajout en cours...")
                
                # A. Ajout de la colonne (nullable au début)
                conn.execute(text("ALTER TABLE reservations ADD COLUMN groupe_id VARCHAR(36)"))
                
                # B. Migration des anciennes données (UUID bidon pour ne pas casser)
                conn.execute(text("UPDATE reservations SET groupe_id = 'legacy_' || id WHERE groupe_id IS NULL"))
                
                # C. Application de la contrainte NOT NULL
                conn.execute(text("ALTER TABLE reservations ALTER COLUMN groupe_id SET NOT NULL"))
                
                conn.commit()
                print("✅ Colonne 'groupe_id' ajoutée avec succès.")
            else:
                print("✅ La table 'reservations' est déjà à jour.")
                
    except Exception as e:
        print(f"❌ Erreur lors du patch SQL : {e}")

    print("🚀 Base de données prête pour le nouveau système !")