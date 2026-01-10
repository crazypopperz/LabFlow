from app import create_app
from db import db

app = create_app()

with app.app_context():
    print("🔄 Création des tables de sécurité...")
    # Cela ne touche pas aux tables existantes, ça crée juste les nouvelles
    db.create_all()
    print("✅ Tables 'equipements_securite', 'maintenance_plans', 'maintenance_logs' créées avec succès !")