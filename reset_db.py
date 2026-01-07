from app import create_app
from db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("☢️  INITIATION DU PROTOCOLE ZÉRO...")
    
    try:
        # Force la déconnexion des autres sessions (PostgreSQL uniquement)
        # Utile si DBeaver ou pgAdmin est ouvert et bloque le drop
        db.session.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = current_database()
            AND pid <> pg_backend_pid();
        """))
        
        # Suppression radicale
        db.session.execute(text('DROP SCHEMA public CASCADE;'))
        db.session.execute(text('CREATE SCHEMA public;'))
        db.session.commit()
        print("✅ Base de données pulvérisée.")
    except Exception as e:
        print(f"⚠️ Avertissement (Drop) : {e}")
        print("Tentative de drop_all() classique...")
        db.drop_all()
    
    print("🏗️  Reconstruction de l'infrastructure...")
    db.create_all()
    
    print("🚀 Base de données vierge prête.")
    print("👉 Lance le serveur et va sur http://127.0.0.1:5000/")
    print("👉 Tu devrais être redirigé vers l'écran de 'Première Installation'.")