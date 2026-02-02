# fix_db.py
import os
os.environ['FLASK_ENV'] = 'production'  # Important !

from app import create_app, db
from sqlalchemy import text

print("🔧 Démarrage correction BDD...")

app = create_app()  # ← Créer l'app avec votre factory

with app.app_context():
    try:
        # Colonnes utilisateurs
        db.session.execute(text("""
            ALTER TABLE utilisateurs 
            ADD COLUMN IF NOT EXISTS niveau_enseignement VARCHAR(50) DEFAULT 'lycee';
        """))
        print("✅ niveau_enseignement")
        
        db.session.execute(text("""
            ALTER TABLE utilisateurs 
            ADD COLUMN IF NOT EXISTS statut_compte VARCHAR(20) DEFAULT 'actif';
        """))
        print("✅ statut_compte")
        
        # Colonne objets
        db.session.execute(text("""
            ALTER TABLE objets 
            ADD COLUMN IF NOT EXISTS type_objet VARCHAR(20) DEFAULT 'materiel';
        """))
        print("✅ type_objet")
        
        db.session.commit()
        print("🎉 BDD corrigée avec succès !")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur : {e}")
        raise