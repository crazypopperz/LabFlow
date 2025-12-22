# ============================================================
# FICHIER : utils.py (Version Finale Corrigée)
# ============================================================
import hashlib
import os
from functools import wraps
from datetime import datetime, timedelta

# Imports Flask
from flask import session, flash, redirect, url_for, request, current_app

# Imports SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

# Imports Locaux
from db import db, Utilisateur, Parametre, Objet, Reservation, AuditLog
from extensions import cache

# -----------------------------------------------------------------------------
# FONCTIONS DE VÉRIFICATION
# -----------------------------------------------------------------------------
def is_setup_needed(app):
    """Vérifie si l'application a besoin d'être configurée (aucun admin)."""
    with app.app_context():
        try:
            admin_count = db.session.query(Utilisateur).filter_by(role='admin').count()
            return admin_count == 0
        except Exception:
            return True

# -----------------------------------------------------------------------------
# FONCTION HELPER (LOGGING)
# -----------------------------------------------------------------------------
def log_action(action, details=None):
    """Enregistre une action dans l'Audit Log avec anonymisation."""
    try:
        user_id = session.get('user_id')
        etablissement_id = session.get('etablissement_id')
        
        if not user_id or not etablissement_id:
            return # Pas de log si hors session

        # Hachage (Anonymisation GDPR)
        user_hash = hashlib.sha256(str(user_id).encode()).hexdigest()
        
        # On récupère l'IP réelle
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        ip_hash = hashlib.sha256(str(ip).encode()).hexdigest()

        log = AuditLog(
            user_id_hash=user_hash,
            ip_address_hash=ip_hash,
            action=action,
            details=str(details) if details else None,
            etablissement_id=etablissement_id
        )
        
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"⚠️ ERREUR AUDIT LOG: {e}")
        db.session.rollback()

# -----------------------------------------------------------------------------
# GESTION DU CACHE (Placé avant les décorateurs pour être utilisé dedans)
# -----------------------------------------------------------------------------
@cache.memoize(timeout=300)  # Cache pendant 5 minutes
def get_etablissement_params(etablissement_id):
    """Récupère les paramètres critiques (Licence) avec mise en cache."""
    if not etablissement_id:
        return {}

    try:
        params = db.session.execute(
            db.select(Parametre)
            .filter_by(etablissement_id=etablissement_id)
            .where(Parametre.cle.in_(['licence_statut', 'instance_id']))
        ).scalars().all()
        
        return {p.cle: p.valeur for p in params}
    except SQLAlchemyError:
        return {}

# -----------------------------------------------------------------------------
# DÉCORATEURS DE SÉCURITÉ
# -----------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash("Accès réservé aux administrateurs.", "error")
            return redirect(url_for('inventaire.index'))
        return f(*args, **kwargs)
    return decorated_function

def limit_objets_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        etablissement_id = session.get('etablissement_id')
        if not etablissement_id:
            flash("Session invalide. Veuillez vous reconnecter.", "error")
            return redirect(url_for('auth.login'))

        # OPTIMISATION : Utilisation du cache au lieu d'une requête DB brute
        params = get_etablissement_params(etablissement_id)
        is_pro = params.get('licence_statut') == 'PRO'
        
        if not is_pro:
            # On compte les objets seulement si pas PRO
            count = db.session.query(Objet).filter_by(etablissement_id=etablissement_id).count()
            if count >= 50:
                flash("La version gratuite est limitée à 50 objets. Passez à la version Pro.", "warning")
                return redirect(request.referrer or url_for('inventaire.index'))
        
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
# LOGIQUE MÉTIER
# -----------------------------------------------------------------------------
def get_alerte_info():
    """Calcule les alertes de stock et de péremption."""
    etablissement_id = session.get('etablissement_id')
    if not etablissement_id:
        return {'alertes_total': 0, 'alertes_stock': 0, 'alertes_peremption': 0}

    try:
        now = datetime.now()
        
        all_objets = db.session.execute(
            db.select(Objet).filter_by(etablissement_id=etablissement_id)
        ).scalars().all()

        count_stock = 0
        count_peremption = 0
        date_limite_peremption = (now + timedelta(days=30)).date()

        for objet in all_objets:
            try:
                # Calcul quantité dispo
                total_reserve = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                    Reservation.objet_id == objet.id,
                    Reservation.fin_reservation > now
                ).scalar() or 0
                
                quantite_disponible = objet.quantite_physique - total_reserve
                
                # Conversion sécurisée
                seuil_numeric = int(objet.seuil) if objet.seuil is not None else 0
                disponible_numeric = int(quantite_disponible)

                # Alerte de stock
                if objet.en_commande == 0 and disponible_numeric <= seuil_numeric:
                    count_stock += 1
                
                # Alerte de péremption
                if objet.date_peremption and objet.traite == 0:
                    # Gestion robuste du format de date
                    if isinstance(objet.date_peremption, str):
                        d_peremption = datetime.strptime(objet.date_peremption, '%Y-%m-%d').date()
                    else:
                        d_peremption = objet.date_peremption # Si déjà date object

                    if d_peremption < date_limite_peremption:
                        count_peremption += 1

            except (ValueError, TypeError) as e:
                # Log warning sans crasher (current_app est maintenant importé)
                current_app.logger.warning(f"Skip objet {objet.id} alert check: {e}")
                pass

        return {
            "alertes_stock": count_stock,
            "alertes_peremption": count_peremption,
            "alertes_total": count_stock + count_peremption
        }

    except SQLAlchemyError as e:
        current_app.logger.error(f"ERREUR DB dans get_alerte_info: {e}")
        return {'alertes_total': 0, 'alertes_stock': 0, 'alertes_peremption': 0}

def annee_scolaire_format(year):
    if isinstance(year, int):
        return f"{year}-{year + 1}"
    return year

# ===============================================
#  ACTIVATION CLE LICENCE
# ===============================================
def calculate_license_key(instance_id):
    secret = os.environ.get('GMLCL_PRO_KEY')
    if not secret: return None
    raw_string = f"{instance_id}-{secret}"
    return hashlib.sha256(raw_string.encode()).hexdigest()[:16].upper()

# ===============================================
#  VERIFICATION DES UPLOADS
# ===============================================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'json', 'csv'}

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS