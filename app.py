# -----------------------------------------------------------------------------
# 1. IMPORTS
# -----------------------------------------------------------------------------
import os
from datetime import date, datetime, timedelta
from flask import Flask, redirect, request, session, url_for, current_app
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import SQLAlchemyError

# On importe l'objet db et les modèles nécessaires pour le context_processor
from db import db, Parametre, Armoire, Categorie, init_app as init_db_app
from utils import get_alerte_info, is_setup_needed
from views.auth import auth_bp
from views.inventaire import inventaire_bp
from views.admin import admin_bp
from views.main import main_bp
from views.api import api_bp

# -----------------------------------------------------------------------------
# 2. LA FONCTION "FACTORY" QUI CRÉE ET CONFIGURE L'APPLICATION
# -----------------------------------------------------------------------------
def create_app():
    app = Flask(__name__)

    # --- CONFIGURATION DE BASE ET SECRETS ---
    app.config.from_object('config') # Charge config.py (pour les configs non secrètes)

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("Erreur: La variable d'environnement SECRET_KEY n'est pas définie !")
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    # --- CONFIGURATION DE LA BASE DE DONNÉES ---
    local_db_url = 'postgresql://user:password@localhost:5432/gestionlabo_db'
    db_url = os.environ.get('DATABASE_URL', local_db_url).replace("postgres://", "postgresql://")
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- INITIALISATION DES EXTENSIONS ---
    init_db_app(app)
    CSRFProtect(app)

    # --- ENREGISTREMENT DES BLUEPRINTS ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(inventaire_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # --- FILTRES JINJA2 PERSONNALISÉS ---
    @app.template_filter('strftime')
    def format_datetime_filter(value, fmt='%d/%m/%Y %H:%M'):
        if isinstance(value, str):
            try: value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                try: value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                except (ValueError, TypeError):
                    try: value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError): return value
        if isinstance(value, (datetime, date)): return value.strftime(fmt)
        return value

    @app.template_filter('strftime_fr')
    def format_datetime_fr_filter(value, fmt):
        if isinstance(value, str):
            try: value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                try: value = datetime.fromisoformat(value)
                except (ValueError, TypeError): return value
        if not isinstance(value, (datetime, date)): return value
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        format_fr = fmt.replace('%A', jours[value.weekday()].capitalize())
        format_fr = format_fr.replace('%B', mois[value.month - 1])
        return value.strftime(format_fr)

    from utils import annee_scolaire_format
    app.jinja_env.filters['annee_scolaire'] = annee_scolaire_format

    # --- HOOKS ET PROCESSEURS DE CONTEXTE ---
    @app.before_request
    def check_setup():
        if is_setup_needed(current_app) and request.endpoint not in ['auth.setup', 'static']:
            return redirect(url_for('auth.setup'))

    @app.context_processor
    def inject_global_data():
        context = {
            'all_armoires': [], 'all_categories': [], 'alertes_total': 0,
            'licence': {'statut': 'FREE', 'is_pro': False, 'instance_id': 'N/A'},
            'nom_etablissement': None
        }
        etablissement_id = session.get('etablissement_id')
        if not etablissement_id: return context
        try:
            context['all_armoires'] = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
            context['all_categories'] = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()
            alert_info = get_alerte_info()
            context['alertes_total'] = alert_info.get('alertes_total', 0)
            
            params = db.session.execute(db.select(Parametre).filter_by(etablissement_id=etablissement_id).where(Parametre.cle.in_(['licence_statut', 'instance_id']))).scalars().all()
            params_dict = {p.cle: p.valeur for p in params}
            if params_dict.get('licence_statut') == 'PRO':
                context['licence']['statut'] = 'PRO'
                context['licence']['is_pro'] = True
            if params_dict.get('instance_id'):
                context['licence']['instance_id'] = params_dict.get('instance_id')

            context['nom_etablissement'] = session.get('nom_etablissement')
            return context
        except SQLAlchemyError as e:
            current_app.logger.error(f"Erreur de base de données dans le context_processor : {e}")
            return context
            
    return app

# -----------------------------------------------------------------------------
# 3. CRÉATION DE L'INSTANCE DE L'APPLICATION
# -----------------------------------------------------------------------------
app = create_app()

# -----------------------------------------------------------------------------
# 4. POINT D'ENTRÉE POUR LE DÉVELOPPEMENT LOCAL
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)