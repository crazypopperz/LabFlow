# ============================================================
# FICHIER : views/admin_users.py
# Gestion des utilisateurs (CRUD, droits, mots de passe)
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import limiter
from db import db, Utilisateur, Historique, Notification
from utils import admin_required, log_action, validate_email, validate_password_strength

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')
# ============================================================
# GESTION UTILISATEURS (DURCIE)
# ============================================================
@admin_users_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    etablissement_id = session['etablissement_id']
    utilisateurs = db.session.execute(
        db.select(Utilisateur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Utilisateur.nom_utilisateur)
        .limit(100)
    ).scalars().all()

    return render_template("admin_utilisateurs.html", utilisateurs=utilisateurs, breadcrumbs=[{'text': 'Tableau de Bord', 'url': url_for('inventaire.index')}, {'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Gestion des utilisateurs', 'url': None}])

@admin_users_bp.route("/utilisateurs/ajouter", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def ajouter_utilisateur():
    etablissement_id = session['etablissement_id']
    nom_utilisateur = request.form.get('nom_utilisateur', '').strip()
    email = request.form.get('email', '').strip()
    mot_de_passe = request.form.get('mot_de_passe', '').strip()
    est_admin = 'est_admin' in request.form

    if not nom_utilisateur or not mot_de_passe:
        flash("Champs obligatoires manquants.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    
    if email and not validate_email(email):
        flash("Format d'email invalide.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    is_valid, error_msg = validate_password_strength(mot_de_passe)
    if not is_valid:
        flash(error_msg, "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    try:
        nouvel_utilisateur = Utilisateur(
            nom_utilisateur=nom_utilisateur,
            email=email or None,
            mot_de_passe=generate_password_hash(mot_de_passe, method='pbkdf2:sha256'),
            role='admin' if est_admin else 'utilisateur',
            etablissement_id=etablissement_id
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()
        
        admin_hash = hash_user_id(session['user_id'])
        current_app.logger.info(f"Utilisateur créé par admin_{admin_hash}")
        flash(f"Utilisateur '{nom_utilisateur}' créé.", "success")
        
    except IntegrityError:
        db.session.rollback()
        # ANTI-ENUMERATION : Message générique
        flash("Erreur : Impossible de créer cet utilisateur (nom peut-être déjà pris).", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur création user", exc_info=True)
        flash("Erreur technique.", "danger")

    return redirect(url_for('admin_users.gestion_utilisateurs'))

@admin_users_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    etablissement_id = session['etablissement_id']
    email = request.form.get('email', '').strip()
    
    if email and not validate_email(email):
        flash("Format d'email invalide.", "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    try:
        user.email = email if email else None
        db.session.commit()
        flash("Email mis à jour.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur modif email", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin_users.gestion_utilisateurs'))

@admin_users_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def reinitialiser_mdp(id_user):
    etablissement_id = session['etablissement_id']
    
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    nouveau_mdp = request.form.get('nouveau_mot_de_passe')
    is_valid, error_msg = validate_password_strength(nouveau_mdp)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    try:
        user.mot_de_passe = generate_password_hash(nouveau_mdp, method='pbkdf2:sha256')
        db.session.commit()
        flash(f"Mot de passe réinitialisé pour {user.nom_utilisateur}.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur reset MDP", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin_users.gestion_utilisateurs'))

@admin_users_bp.route("/utilisateurs/supprimer/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("5 per minute") # Rate Limit Strict
def supprimer_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Impossible de supprimer son propre compte.", "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    user = db.session.get(Utilisateur, id_user)
    
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    try:
        has_history = db.session.query(Historique).filter_by(utilisateur_id=user.id).first()
        has_reservations = db.session.query(Reservation).filter_by(utilisateur_id=user.id).first()

        if has_history or has_reservations:
            user.nom_utilisateur = f"Utilisateur_Supprimé_{user.id}_{secrets.token_hex(2)}"
            user.email = None
            user.mot_de_passe = "deleted"
            user.role = "desactive"
            db.session.commit()
            flash("Utilisateur anonymisé et désactivé (historique conservé).", "warning")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("Utilisateur supprimé définitivement.", "success")
            
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur suppression user", exc_info=True)
        flash("Erreur technique.", "error")
        
    return redirect(url_for('admin_users.gestion_utilisateurs'))

@admin_users_bp.route("/utilisateurs/promouvoir/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("3 per minute") # Rate Limit Très Strict
def promouvoir_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    target_user = db.session.get(Utilisateur, id_user)
    current_admin = db.session.get(Utilisateur, session['user_id'])
    
    if not target_user or target_user.etablissement_id != etablissement_id:
        flash("Utilisateur cible introuvable.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    password_confirm = request.form.get('password')
    if not password_confirm or not check_password_hash(current_admin.mot_de_passe, password_confirm):
        flash("Mot de passe incorrect.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))

    try:
        # Limite 3 admins par établissement
        nb_admins = db.session.execute(
            db.select(db.func.count()).select_from(Utilisateur)
            .filter_by(etablissement_id=etablissement_id, role='admin')
        ).scalar()
        if nb_admins >= 3:
            flash("Limite atteinte : 3 administrateurs maximum par établissement.", "warning")
            return redirect(url_for('admin_users.gestion_utilisateurs'))
        if target_user.role == 'admin':
            flash(f"{target_user.nom_utilisateur} est déjà administrateur.", "info")
            return redirect(url_for('admin_users.gestion_utilisateurs'))
        target_user.role = 'admin'
        db.session.commit()
        log_action('promouvoir_admin', f"{target_user.nom_utilisateur} promu administrateur")
        flash(f"{target_user.nom_utilisateur} est maintenant administrateur.", "success")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur promotion", exc_info=True)
        flash("Erreur technique.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))


@admin_users_bp.route("/utilisateurs/retrograder/<int:id_user>", methods=["POST"])
@admin_required
@limiter.limit("3 per minute")
def retrograder_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Impossible de se rétrograder soi-même.", "warning")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    etablissement_id = session['etablissement_id']
    target_user = db.session.get(Utilisateur, id_user)
    if not target_user or target_user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    # Vérifier qu'il reste au moins 1 admin
    nb_admins = db.session.execute(
        db.select(db.func.count()).select_from(Utilisateur)
        .filter_by(etablissement_id=etablissement_id, role='admin')
    ).scalar()
    if nb_admins <= 1:
        flash("Impossible : il doit rester au moins un administrateur.", "warning")
        return redirect(url_for('admin_users.gestion_utilisateurs'))
    try:
        target_user.role = 'utilisateur'
        db.session.commit()
        log_action('retrograder_admin', f"{target_user.nom_utilisateur} rétrogradé en utilisateur")
        flash(f"{target_user.nom_utilisateur} est maintenant simple utilisateur.", "success")
    except Exception:
        db.session.rollback()
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin_users.gestion_utilisateurs'))
