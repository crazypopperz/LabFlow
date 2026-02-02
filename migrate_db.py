# migrate_db.py
from app import app, db
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column_if_not_exists(table_name, column_name, column_type):
    """Ajoute une colonne si elle n'existe pas"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        if column_name not in columns:
            logger.info(f"Ajout de la colonne {column_name} à {table_name}")
            with db.engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'))
                conn.commit()
            logger.info(f"✓ Colonne {column_name} ajoutée")
        else:
            logger.info(f"✓ Colonne {column_name} existe déjà")

def migrate():
    """Exécute toutes les migrations nécessaires"""
    try:
        logger.info("Début de la migration...")
        
        # Migration pour la table utilisateurs
        add_column_if_not_exists('utilisateurs', 'niveau_enseignement', 'VARCHAR(50)')
        
        # Migration pour la table objets
        add_column_if_not_exists('objets', 'type_objet', 'VARCHAR(50)')
        
        logger.info("✓ Migration terminée avec succès!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == '__main__':
    migrate()