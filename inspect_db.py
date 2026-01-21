import os
from sqlalchemy import create_engine, inspect, text

# --- CONFIGURATION ---
# Colle ton URL EXTERNE ici entre les guillemets
DB_URL = "postgresql://laboflw_db_v2_user:1ypCucniWaQKh1rq0LlxOWf0ZluztN93@dpg-d5ijmn14tr6s73ak5gpg-a.frankfurt-postgres.render.com/laboflw_db_v2" 

def inspecter_base():
    if "COLLE_TON_URL" in DB_URL:
        print("❌ ERREUR : Tu as oublié de coller l'URL dans le script !")
        return

    print(f"🔌 Connexion à la base Render en cours...")
    
    try:
        engine = create_engine(DB_URL)
        inspector = inspect(engine)
        
        # Récupérer les tables
        tables = inspector.get_table_names()
        
        if not tables:
            print("⚠️  La base de données est VIDE (aucune table trouvée).")
            return

        print(f"✅ Connexion réussie. {len(tables)} tables trouvées.\n")

        for table in tables:
            print(f"📄 TABLE : {table.upper()}")
            print("-" * 40)
            columns = inspector.get_columns(table)
            for col in columns:
                # On affiche le nom et le type de la colonne
                col_str = f"  - {col['name']} ({col['type']})"
                
                # Vérification spécifique pour tes nouvelles colonnes
                if col['name'] in ['description', 'photo_url']:
                    col_str += "  <-- ✨ NOUVELLE COLONNE PRÉSENTE"
                
                print(col_str)
            print("\n")
            
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")

if __name__ == "__main__":
    inspecter_base()