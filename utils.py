# ============================================================
# FICHIER : utils.py (Version Finale - Tout inclus)
# ============================================================
import hashlib
import os
import re
import unicodedata
from functools import wraps
from datetime import datetime, timedelta

# Imports Flask
from flask import session, flash, redirect, url_for, request, current_app

# Imports SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

# Imports Locaux
from db import db, Utilisateur, Parametre, Objet, Reservation, AuditLog, MaintenanceLog, EquipementSecurite, Suggestion
from extensions import cache

# -----------------------------------------------------------------------------
# 1. VALIDATION & SANITIZATION (C'est ce qu'il manquait !)
# -----------------------------------------------------------------------------

# Regex Email conforme RFC 5321 (simplifiée mais robuste)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_email(email):
    """Valide le format d'un email."""
    if not email or len(email) > 254:
        return False
    return EMAIL_REGEX.match(email.strip().lower()) is not None

def validate_password_strength(password):
    """
    Vérifie la force du mot de passe.
    Retourne (bool, message_erreur).
    """
    if len(password) < 12:
        return False, "Le mot de passe doit contenir au moins 12 caractères."
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une minuscule."
    if not re.search(r'[0-9]', password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r'[^a-zA-Z0-9]', password):
        return False, "Le mot de passe doit contenir au moins un caractère spécial."
    return True, ""

def sanitize_input(text, max_length=100):
    """Nettoie une entrée utilisateur (supprime caractères de contrôle)."""
    if not text: return ""
    text = text.strip()[:max_length]
    # Retire les caractères non imprimables
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

# -----------------------------------------------------------------------------
# 2. LOGIQUE DE LICENCE
# -----------------------------------------------------------------------------
def calculate_license_key(instance_id):
    """
    Génère une clé basée uniquement sur l'ID unique de l'installation.
    """
    secret = os.environ.get('GMLCL_PRO_KEY')
    if not secret or not instance_id: return None
    
    # Signature simple : ID + Secret
    raw_string = f"{instance_id}-{secret}"
    return hashlib.sha256(raw_string.encode()).hexdigest()[:16].upper()

# -----------------------------------------------------------------------------
# 3. FONCTIONS DE VÉRIFICATION SYSTÈME
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
# 4. LOGGING (AUDIT)
# -----------------------------------------------------------------------------
def log_action(action, details=None):
    """Enregistre une action dans l'Audit Log."""
    try:
        user_id = session.get('user_id')
        etablissement_id = session.get('etablissement_id')
        
        if not user_id or not etablissement_id:
            return 

        # On récupère l'IP réelle
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Hashage MD5 pour compatibilité DB (32 chars)
        if ip:
            ip_safe = hashlib.md5(ip.encode()).hexdigest()
        else:
            ip_safe = 'unknown'

        log = AuditLog(
            id_utilisateur=user_id,
            ip_address=ip_safe,
            action=action,
            details=str(details) if details else None,
            etablissement_id=etablissement_id,
            table_cible="GENERAL"
        )
        
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"⚠️ ERREUR AUDIT LOG: {e}")
        db.session.rollback()

# -----------------------------------------------------------------------------
# 5. GESTION DU CACHE
# -----------------------------------------------------------------------------
@cache.memoize(timeout=300)
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
# 6. DÉCORATEURS DE SÉCURITÉ
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

        params = get_etablissement_params(etablissement_id)
        is_pro = params.get('licence_statut') == 'PRO'
        
        if not is_pro:
            count = db.session.query(Objet).filter_by(etablissement_id=etablissement_id).count()
            if count >= 50:
                flash("La version gratuite est limitée à 50 objets. Passez à la version Pro.", "warning")
                return redirect(request.referrer or url_for('inventaire.index'))
        
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
# 7. LOGIQUE MÉTIER (ALERTES)
# -----------------------------------------------------------------------------
def get_alerte_info():
    """Calcule les alertes. Chaque bloc est isolé pour éviter un crash global."""
    etablissement_id = session.get('etablissement_id')
    
    # Valeurs par défaut
    alerts = {
        "alertes_stock": 0,
        "alertes_peremption": 0,
        "alertes_securite": 0,
        "alertes_suggestions": 0,
        "alertes_total": 0
    }

    if not etablissement_id:
        return alerts

    now = datetime.now()

    # A. Calcul Stock & Péremption
    try:
        all_objets = db.session.execute(
            db.select(Objet).filter_by(etablissement_id=etablissement_id)
        ).scalars().all()

        count_stock = 0
        count_peremption = 0
        date_limite_peremption = (now + timedelta(days=30)).date()

        for objet in all_objets:
            try:
                # Stock
                total_reserve = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                    Reservation.objet_id == objet.id,
                    Reservation.fin_reservation > now
                ).scalar() or 0
                
                quantite_disponible = objet.quantite_physique - total_reserve
                seuil_numeric = int(objet.seuil) if objet.seuil is not None else 0
                
                if objet.en_commande == 0 and int(quantite_disponible) <= seuil_numeric:
                    count_stock += 1
                
                # Péremption
                if objet.date_peremption and objet.traite == 0:
                    d_perim = objet.date_peremption if isinstance(objet.date_peremption, datetime) else datetime.strptime(str(objet.date_peremption), '%Y-%m-%d').date()
                    if d_perim < date_limite_peremption:
                        count_peremption += 1
            except Exception:
                continue 

        alerts["alertes_stock"] = count_stock
        alerts["alertes_peremption"] = count_peremption

    except Exception as e:
        current_app.logger.error(f"Erreur calcul stock/péremption: {e}")

    # B. Calcul Sécurité (Signalements)
    try:
        count_securite = db.session.query(MaintenanceLog).join(EquipementSecurite).filter(
            EquipementSecurite.etablissement_id == etablissement_id,
            MaintenanceLog.resultat == 'signalement'
        ).count()
        alerts["alertes_securite"] = count_securite
    except Exception as e:
        current_app.logger.error(f"Erreur calcul sécurité: {e}")

    # C. Calcul Suggestions
    try:
        count_suggestions = db.session.query(Suggestion).filter_by(
            etablissement_id=etablissement_id, 
            statut='En attente'
        ).count()
        alerts["alertes_suggestions"] = count_suggestions
    except Exception as e:
        current_app.logger.error(f"Erreur calcul suggestions: {e}")

    # Total
    alerts["alertes_total"] = (
        alerts["alertes_stock"] + 
        alerts["alertes_peremption"] + 
        alerts["alertes_securite"] + 
        alerts["alertes_suggestions"]
    )

    return alerts

def annee_scolaire_format(year):
    if isinstance(year, int): return f"{year}-{year + 1}"
    return year

# ===============================================
#  VERIFICATION DES UPLOADS
# ===============================================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'json', 'csv', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS