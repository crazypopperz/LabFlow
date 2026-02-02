# migrate_db.py
from app import app, db
from sqlalchemy import text

def migrate():
    """Ajoute les colonnes manquantes à la base de données"""
    with app.app_context():
        try:
            print("🔧 Début de la migration...")
            
            # Ajouter les colonnes manquantes à utilisateurs
            db.session.execute(text("""
                ALTER TABLE utilisateurs 
                ADD COLUMN IF NOT EXISTS niveau_enseignement VARCHAR(50) DEFAULT 'lycee';
            """))
            print("✅ Colonne niveau_enseignement ajoutée")
            
            db.session.execute(text("""
                ALTER TABLE utilisateurs 
                ADD COLUMN IF NOT EXISTS statut_compte VARCHAR(20) DEFAULT 'actif';
            """))
            print("✅ Colonne statut_compte ajoutée")
            
            # Ajouter la colonne type_objet aussi
            db.session.execute(text("""
                ALTER TABLE objets 
                ADD COLUMN IF NOT EXISTS type_objet VARCHAR(20) DEFAULT 'materiel';
            """))
            print("✅ Colonne type_objet ajoutée")
            
            db.session.commit()
            print("🎉 Migration réussie !")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur migration : {e}")
            raise

if __name__ == "__main__":
    migrate()