from app import create_app
from db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Début de la mise à jour de la table 'armoires'...")
    
    try:
        # 1. Ajout de la colonne description
        print("- Ajout de la colonne 'description'...")
        db.session.execute(text("ALTER TABLE armoires ADD COLUMN description TEXT;"))
        
        # 2. Ajout de la colonne photo_url
        print("- Ajout de la colonne 'photo_url'...")
        db.session.execute(text("ALTER TABLE armoires ADD COLUMN photo_url VARCHAR(255);"))
        
        db.session.commit()
        print("✅ Succès ! La base de données est à jour.")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur (ou colonnes déjà existantes) : {e}")