# migrate_db.py
from app import app, db
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_column_if_not_exists(table_name, column_name, column_definition):
    """Ajoute une colonne si elle n'existe pas"""
    inspector = inspect(db.engine)
    
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        logger.warning(f"Table {table_name} n'existe pas encore")
        return False
    
    if column_name not in columns:
        logger.info(f"Ajout de {table_name}.{column_name}")
        try:
            with db.engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}'))
                conn.commit()
            logger.info(f"✓ {column_name} ajoutée")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur ajout {column_name}: {e}")
            return False
    else:
        logger.info(f"✓ {column_name} existe déjà")
        return False

def migrate():
    """Exécute toutes les migrations"""
    try:
        logger.info("=" * 50)
        logger.info("DÉBUT MIGRATION BASE DE DONNÉES")
        logger.info("=" * 50)
        
        # Table utilisateurs
        logger.info("Migration table UTILISATEURS...")
        add_column_if_not_exists('utilisateurs', 'niveau_enseignement', 'VARCHAR(50)')
        
        # Table objets - TOUTES les colonnes
        logger.info("Migration table OBJETS...")
        add_column_if_not_exists('objets', 'type_objet', 'VARCHAR(50)')
        add_column_if_not_exists('objets', 'unite', 'VARCHAR(20)')
        add_column_if_not_exists('objets', 'capacite_initiale', 'FLOAT')
        add_column_if_not_exists('objets', 'niveau_actuel', 'FLOAT')
        add_column_if_not_exists('objets', 'seuil_pourcentage', 'FLOAT')
        add_column_if_not_exists('objets', 'niveau_requis', 'FLOAT')
        add_column_if_not_exists('objets', 'quantite_physique', 'INTEGER')
        add_column_if_not_exists('objets', 'seuil', 'INTEGER')
        add_column_if_not_exists('objets', 'date_peremption', 'DATE')
        add_column_if_not_exists('objets', 'image_url', 'TEXT')
        add_column_if_not_exists('objets', 'fds_url', 'TEXT')
        add_column_if_not_exists('objets', 'is_cmr', 'BOOLEAN DEFAULT FALSE')
        add_column_if_not_exists('objets', 'armoire_id', 'INTEGER')
        add_column_if_not_exists('objets', 'categorie_id', 'INTEGER')
        add_column_if_not_exists('objets', 'etablissement_id', 'INTEGER')
        add_column_if_not_exists('objets', 'en_commande', 'BOOLEAN DEFAULT FALSE')
        add_column_if_not_exists('objets', 'traite', 'BOOLEAN DEFAULT FALSE')
        
        logger.info("=" * 50)
        logger.info("✓ MIGRATION TERMINÉE AVEC SUCCÈS")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"❌ ERREUR CRITIQUE MIGRATION: {e}")
        logger.error("=" * 50)
        raise

if __name__ == '__main__':
    with app.app_context():
        migrate()