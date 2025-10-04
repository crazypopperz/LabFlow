# -----------------------------------------------------------------------------
# 1. IMPORTS DE LA BIBLIOTHÈQUE STANDARD PYTHON
# -----------------------------------------------------------------------------
import logging
import os
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler

# -----------------------------------------------------------------------------
# 2. IMPORTS DES BIBLIOTHÈQUES TIERCES (PIP)
# -----------------------------------------------------------------------------
from flask import (Flask, redirect, request, send_from_directory, session, url_for)
from flask_wtf.csrf import CSRFProtect

# -----------------------------------------------------------------------------
# 3. IMPORTS DES MODULES LOCAUX
# -----------------------------------------------------------------------------
from db import get_db
from db import init_app as init_db_app
from utils import (admin_required, get_alerte_info, is_setup_needed,
                   limit_objets_required, login_required, annee_scolaire_format)
from views.auth import auth_bp
from views.inventaire import inventaire_bp
from views.admin import admin_bp
from views.main import main_bp
from views.api import api_bp

# --- CONFIGURATION DE L'APPLICATION ---
app = Flask(__name__)
app.config.from_object('config')
init_db_app(app)
app.config['SECRET_KEY'] = os.environ.get('GMLCL_SECRET_KEY', 'une-cle-temporaire-pour-le-developpement-a-changer')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
csrf = CSRFProtect(app)

# ENREGISTREMENT DES BLUEPRINTS
app.register_blueprint(auth_bp)
app.register_blueprint(inventaire_bp)
USER_DATA_PATH = os.path.join(os.environ.get('APPDATA'), 'GMLCL')
os.makedirs(USER_DATA_PATH, exist_ok=True)
app.config['UPLOAD_FOLDER'] = os.path.join(USER_DATA_PATH, 'uploads', 'images')
app.config['FDS_UPLOAD_FOLDER'] = os.path.join(USER_DATA_PATH, 'uploads', 'fds')
DATABASE = os.path.join(USER_DATA_PATH, 'base.db')
app.config['DATABASE'] = DATABASE
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['FDS_UPLOAD_FOLDER'], exist_ok=True)
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if not app.debug:
    log_file_path = os.path.join(USER_DATA_PATH, 'app.log')
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        handlers=[
            RotatingFileHandler(
                log_file_path, maxBytes=1024000, backupCount=5
            )
        ]
    )
    app.logger.info('Logging configuré pour écrire dans %s', log_file_path)

CLE_PRO_SECRETE = os.environ.get('GMLCL_PRO_KEY', 'valeur-par-defaut-si-non-definie')
app.config['CLE_PRO_SECRETE'] = CLE_PRO_SECRETE


# --- FILTRES JINJA2 PERSONNALISÉS ---
def format_datetime(value, fmt='%d/%m/%Y %H:%M'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
            except (ValueError, TypeError):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return value
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return value

app.jinja_env.filters['strftime'] = format_datetime

def format_datetime_fr(value, fmt):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
    if not isinstance(value, (datetime, date)):
        return value
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    format_fr = fmt.replace('%A', jours[value.weekday()].capitalize())
    format_fr = format_fr.replace('%B', mois[value.month - 1])
    return value.strftime(format_fr)

app.jinja_env.filters['strftime_fr'] = format_datetime_fr

app.jinja_env.filters['annee_scolaire'] = annee_scolaire_format

# --- GESTION DE L'INITIALISATION AU PREMIER LANCEMENT ---
@app.before_request
def check_setup():
    if not os.path.exists(DATABASE):
        return
    allowed_endpoints = ['static', 'setup', 'login', 'register']
    if request.endpoint and request.endpoint not in allowed_endpoints:
        if is_setup_needed(app):
            return redirect(url_for('auth.setup'))

# --- FONCTIONS COMMUNES ET PROCESSEUR DE CONTEXTE ---
@app.context_processor
def inject_alert_info():
    # Si l'application n'est pas encore configurée ou si l'utilisateur n'est pas connecté,
    # on renvoie des valeurs par défaut sans interroger la base de données.
    if 'user_id' not in session or is_setup_needed(app):
        return {'alertes_total': 0, 'alertes_stock': 0, 'alertes_peremption': 0}
    
    # Ce bloc ne s'exécute que si l'app est configurée ET l'utilisateur connecté.
    try:
        db = get_db()
        return get_alerte_info(db)
    except sqlite3.Error:
        # En cas d'erreur de base de données inattendue, on évite de planter l'application.
        return {'alertes_total': '!', 'alertes_stock': '!', 'alertes_peremption': '!'}


@app.context_processor
def inject_licence_info():
    """
    Injecte le statut de la licence dans le contexte de tous les templates.
    Rend la variable 'licence' disponible globalement.
    """
    licence_info = {'statut': 'FREE', 'is_pro': False, 'instance_id': 'N/A'}

    # On ne fait rien si la session n'est pas active ou si l'app n'est pas configurée.
    if 'user_id' not in session or is_setup_needed(app):
        return {'licence': licence_info}

    try:
        db = get_db()
        params = db.execute(
            "SELECT cle, valeur FROM parametres "
            "WHERE cle IN ('licence_statut', 'instance_id')").fetchall()
        params_dict = {row['cle']: row['valeur'] for row in params}

        if params_dict.get('licence_statut') == 'PRO':
            licence_info['statut'] = 'PRO'
            licence_info['is_pro'] = True

        if params_dict.get('instance_id'):
            licence_info['instance_id'] = params_dict.get('instance_id')

    except sqlite3.Error as e:
        app.logger.warning(
            f"Impossible de lire les informations de licence. Erreur : {e}"
        )
    
    return {'licence': licence_info}


# --- ROUTE POUR SERVIR LES IMAGES UPLOADÉES ---
from flask import send_from_directory
