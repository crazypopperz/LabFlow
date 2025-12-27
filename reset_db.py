from app import create_app
from db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("☢️  REMISE À ZÉRO (Mode Production)...")
    
    # 1. Suppression radicale (Spécifique PostgreSQL)
    # On supprime le schéma public entier pour être sûr qu'il ne reste rien (types enum, séquences...)
    try:
        db.session.execute(text('DROP SCHEMA public CASCADE;'))
        db.session.execute(text('CREATE SCHEMA public;'))
        db.session.commit()
        print("✅ Base de données entièrement vidée (Drop Schema).")
    except Exception as e:
        # Fallback pour SQLite ou si l'utilisateur n'a pas les droits superuser
        print(f"⚠️ Note : {e}")
        print("🔄 Passage à la méthode standard drop_all()...")
        db.drop_all()
    
    # 2. Création de la structure (Tables vides)
    # Cela va créer les tables Paniers, Audit, et Reservation avec la nouvelle colonne groupe_id
    print("🏗️  Création de la structure des tables...")
    db.create_all()
    
    print("🚀 Base de données prête et 100% VIERGE.")
    print("------------------------------------------------")
    print("👉 Lance le serveur : python app.py")
    print("👉 Va sur : http://127.0.0.1:5000/")
    print("👉 Tu devrais être redirigé automatiquement vers /auth/setup")
    print("------------------------------------------------")