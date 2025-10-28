# Fichier : utils.py (Version Finale et Définitive)

from flask import session, flash, redirect, url_for, request
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

# On met TOUS les imports de DB ici, en haut du fichier
from db import db, Utilisateur, Parametre, Objet, Reservation
from sqlalchemy import func

# -----------------------------------------------------------------------------
# FONCTIONS DE VÉRIFICATION
# -----------------------------------------------------------------------------
def is_setup_needed(app):
    with app.app_context():
        try:
            admin_count = db.session.query(Utilisateur).filter_by(role='admin').count()
            return admin_count == 0
        except Exception:
            return True

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

        licence_param = db.session.execute(
            db.select(Parametre).filter_by(cle='licence_statut', etablissement_id=etablissement_id)
        ).scalar_one_or_none()

        is_pro = licence_param and licence_param.valeur == 'PRO'
        
        if not is_pro:
            count = db.session.query(Objet).filter_by(etablissement_id=etablissement_id).count()
            if count >= 50:
                flash("La version gratuite est limitée à 50 objets. Passez à la version Pro pour en ajouter davantage.", "warning")
                return redirect(request.referrer or url_for('inventaire.index'))
        
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
# LOGIQUE MÉTIER
# -----------------------------------------------------------------------------
def get_alerte_info():
    """Calcule les alertes de stock et de péremption (Version Finale et Corrigée)."""
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

        # LA CORRECTION EST ICI : On boucle sur la bonne variable "all_objets"
        for objet in all_objets:
            try:
                # On calcule la disponibilité pour CET objet
                total_reserve = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                    Reservation.objet_id == objet.id,
                    Reservation.fin_reservation > now
                ).scalar() or 0
                
                quantite_disponible = objet.quantite_physique - total_reserve
                seuil_numeric = int(objet.seuil)
                disponible_numeric = int(quantite_disponible)

                # Alerte de stock
                if objet.en_commande == 0 and disponible_numeric <= seuil_numeric:
                    count_stock += 1
                
                # Alerte de péremption
                if objet.date_peremption and objet.traite == 0:
                    date_peremption_obj = datetime.strptime(objet.date_peremption, '%Y-%m-%d').date()
                    if date_peremption_obj < date_limite_peremption:
                        count_peremption += 1

            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Impossible de traiter l'objet ID {objet.id} pour les alertes. Erreur : {e}")
                pass

        total_alertes = count_stock + count_peremption
        
        return {
            "alertes_stock": count_stock,
            "alertes_peremption": count_peremption,
            "alertes_total": total_alertes
        }

    except SQLAlchemyError as e:
        current_app.logger.error(f"ERREUR DB dans get_alerte_info: {e}")
        return {'alertes_total': 0, 'alertes_stock': 0, 'alertes_peremption': 0}

def annee_scolaire_format(year):
    if isinstance(year, int):
        return f"{year}-{year + 1}"
    return year