# ============================================================
# FICHIER : app.py (Version Compatible Système Maison)
# ============================================================
import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from datetime import date, datetime, timedelta
from flask import Flask, redirect, request, session, url_for, current_app, render_template
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

# Extensions (Cache & Rate Limit) - PAS DE LOGIN_MANAGER
from extensions import limiter, cache, mail
from flask_migrate import Migrate

# Imports locaux
from db import db, Parametre, Armoire, Notification, Categorie, init_app as init_db_app
from utils import get_alerte_info, is_setup_needed, annee_scolaire_format, get_etablissement_params

# Imports des Blueprints
from views.auth import auth_bp
from views.inventaire import inventaire_bp
from views.admin import admin_bp
from views.main import main_bp
from views.api import api_bp
from views.securite import securite_bp

# Chargement .env
load_dotenv()

def configure_logging(app):
    """Configure les logs pour la production et le développement."""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('LabFlow startup')

def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    # ============================================================
    # 0. VÉRIFICATION ENVIRONNEMENT (FAIL FAST)
    # ============================================================
    is_production = os.environ.get('FLASK_ENV') == 'production'
    REQUIRED_VARS = ['DATABASE_URL', 'GMLCL_PRO_KEY']
    
    if is_production:
        REQUIRED_VARS.append('SECRET_KEY')

    missing_vars = [var for var in REQUIRED_VARS if not os.environ.get(var)]
    if missing_vars:
        raise RuntimeError(f"ERREUR CRITIQUE : Variables d'environnement manquantes : {', '.join(missing_vars)}")

    # ============================================================
    # 1. CONFIGURATION
    # ============================================================
    app.config.from_object('config') 

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        secret_key = 'dev-key-stable-pour-eviter-deconnexion'
        if not is_production:
            print("⚠️  MODE DEV : Utilisation d'une SECRET_KEY fixe par défaut.")
    app.config['SECRET_KEY'] = secret_key
    
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 
    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    if is_production:
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    if os.environ.get('FLASK_ENV') == 'testing':
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        logging.warning("⚠️  MODE TESTING ACTIVÉ : Base de données en mémoire.")

    # ============================================================
    # 2. INITIALISATION DES EXTENSIONS
    # ============================================================
    init_db_app(app)
    migrate = Migrate(app, db)
    with app.app_context():
        db.create_all()
    CSRFProtect(app)
    mail.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    configure_logging(app)

    # ============================================================
    # 3. SÉCURITÉ HTTP (TALISMAN)
    # ============================================================
    if is_production:
        csp = {
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
            'style-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"],
            'font-src': ["'self'", "data:", "cdn.jsdelivr.net", "fonts.gstatic.com"],
            'img-src': ["'self'", "data:", "blob:", "https:", "images.pexels.com", "*.pexels.com"],
            'connect-src': ["'self'", "cdn.jsdelivr.net"]
        }

        Talisman(app, 
            force_https=True,
            content_security_policy=csp,
            strict_transport_security=True,
            session_cookie_secure=True,
            frame_options='DENY' 
        )

    # ============================================================
    # 4. BLUEPRINTS
    # ============================================================
    app.register_blueprint(auth_bp)
    app.register_blueprint(inventaire_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(securite_bp)

    # ============================================================
    # 5. GESTION ERREURS
    # ============================================================
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Server Error: {error}")
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        if request.is_json or request.path.startswith('/api/'):
            return {"error": "Trop de requêtes. Veuillez patienter."}, 429
        return render_template("errors/429.html"), 429

    # ============================================================
    # 6. FILTRES JINJA
    # ============================================================
    @app.template_filter('strftime')
    def format_datetime_filter(value, fmt='%d/%m/%Y %H:%M'):
        if isinstance(value, str):
            try: value = datetime.fromisoformat(value)
            except (ValueError, TypeError): return value
        if isinstance(value, (datetime, date)): return value.strftime(fmt)
        return value

    @app.template_filter('strftime_fr')
    def format_datetime_fr_filter(value, fmt):
        if isinstance(value, str):
            try: value = datetime.fromisoformat(value)
            except (ValueError, TypeError): return value
        if not isinstance(value, (datetime, date)): return value
        
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        
        format_fr = fmt.replace('%A', jours[value.weekday()].capitalize())
        format_fr = format_fr.replace('%B', mois[value.month - 1])
        return value.strftime(format_fr)

    app.jinja_env.filters['annee_scolaire'] = annee_scolaire_format

    # ============================================================
    # 7. CONTEXT PROCESSORS (GLOBAL DATA)
    # ============================================================
    @app.context_processor
    def inject_global_data():
        context = {
            'all_armoires': [], 'all_categories': [], 'alertes_total': 0,
            'licence': {'statut': 'FREE', 'is_pro': False, 'instance_id': 'N/A'},
            'nom_etablissement': None,
            'notifs_count': 0,      # <--- AJOUT
            'notifications_list': [] # <--- AJOUT
        }
        
        etablissement_id = session.get('etablissement_id')
        user_id = session.get('user_id') # <--- AJOUT
        
        if not etablissement_id: return context
            
        try:
            context['all_armoires'] = db.session.execute(
                db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)
            ).scalars().all()
            
            context['all_categories'] = db.session.execute(
                db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)
            ).scalars().all()
            
            if user_id:
                notifs = db.session.execute(
                    db.select(Notification)
                    .filter_by(utilisateur_id=user_id, lu=False)
                    .order_by(Notification.date_creation.desc())
                ).scalars().all()
                
                context['notifs_count'] = len(notifs)
                context['notifications_list'] = notifs
            
            alert_info = get_alerte_info()
            context['alertes_total'] = alert_info.get('alertes_total', 0)
            
            params_dict = get_etablissement_params(etablissement_id)
            
            if params_dict.get('licence_statut') == 'PRO':
                context['licence']['statut'] = 'PRO'
                context['licence']['is_pro'] = True
            
            if params_dict.get('instance_id'):
                context['licence']['instance_id'] = params_dict.get('instance_id')

            context['nom_etablissement'] = session.get('nom_etablissement')
            
            return context
            
        except SQLAlchemyError as e:
            current_app.logger.error(f"Erreur context_processor : {e}")
            return context
        except Exception as e:
            current_app.logger.error(f"Erreur inattendue context_processor : {e}")
            return context
            
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)