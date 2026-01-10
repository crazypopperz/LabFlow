# ============================================================
# FICHIER : views/auth.py (SÉCURISÉ & VALIDÉ)
# ============================================================
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from db import db, Utilisateur, Etablissement, Parametre
from utils import get_etablissement_params, login_required, validate_password_strength, validate_email
from extensions import limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.session.execute(db.select(Utilisateur).filter_by(nom_utilisateur=username)).scalar_one_or_none()
        
        if user and check_password_hash(user.mot_de_passe, password):
            if user.role == 'desactive':
                flash("Ce compte a été désactivé.", "error")
                return redirect(url_for('auth.login'))

            session.clear()
            
            session['user_id'] = user.id
            session['user_name'] = user.nom_utilisateur
            session['user_role'] = user.role
            session['etablissement_id'] = user.etablissement_id
            
            etab = db.session.get(Etablissement, user.etablissement_id)
            session['nom_etablissement'] = etab.nom if etab else "Mon Labo"
            
            return redirect(url_for('inventaire.index'))
        else:
            flash("Identifiants incorrects.", "error")
            
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        code_invitation = request.form.get('code_invitation', '').strip().upper()
        
        # 1. Validation Email
        if not validate_email(email):
            flash("Format d'email invalide.", "error")
            return redirect(url_for('auth.register'))

        # 2. Validation Mot de passe (AJOUTÉ)
        is_valid_pass, msg_pass = validate_password_strength(password)
        if not is_valid_pass:
            flash(msg_pass, "error")
            return redirect(url_for('auth.register'))

        # 3. Vérification du code d'invitation
        etablissement = db.session.execute(db.select(Etablissement).filter_by(code_invitation=code_invitation)).scalar_one_or_none()
        
        if not etablissement:
            flash("Code d'invitation invalide.", "error")
            return redirect(url_for('auth.register'))
            
        # 4. Vérification existence utilisateur
        existing_user = db.session.execute(db.select(Utilisateur).filter_by(nom_utilisateur=username)).scalar_one_or_none()
        existing_email = db.session.execute(db.select(Utilisateur).filter_by(email=email)).scalar_one_or_none()
        
        if existing_user or existing_email:
            flash("Impossible de créer le compte avec ces informations.", "error")
            return redirect(url_for('auth.register'))

        # 5. Création
        try:
            nouvel_utilisateur = Utilisateur(
                nom_utilisateur=username,
                email=email,
                mot_de_passe=generate_password_hash(password, method='pbkdf2:sha256'),
                role='utilisateur',
                etablissement_id=etablissement.id
            )
            
            db.session.add(nouvel_utilisateur)
            db.session.commit()
            
            flash("Compte créé avec succès ! Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur register: {e}")
            flash("Erreur technique lors de l'inscription.", "error")
            
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def setup():
    """Installation initiale (Premier Admin)."""
    user_exist = db.session.execute(db.select(Utilisateur)).first()
    if user_exist:
        flash("L'application est déjà installée.", "warning")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nom_etablissement = request.form.get('nom_etablissement')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation Email
        if not validate_email(email):
            flash("Format d'email invalide.", "error")
            return render_template('setup.html')

        # Validation Mot de passe (AJOUTÉ)
        is_valid_pass, msg_pass = validate_password_strength(password)
        if not is_valid_pass:
            flash(msg_pass, "error")
            return render_template('setup.html')

        try:
            code_temp = f"LAB-{secrets.token_hex(6).upper()}"
            
            etab = Etablissement(nom=nom_etablissement, code_invitation=code_temp)
            db.session.add(etab)
            db.session.flush()
            
            admin_user = Utilisateur(
                nom_utilisateur=username,
                email=email,
                mot_de_passe=generate_password_hash(password, method='pbkdf2:sha256'),
                role='admin',
                etablissement_id=etab.id
            )
            db.session.add(admin_user)
            
            db.session.add(Parametre(cle='licence_statut', valeur='FREE', etablissement_id=etab.id))
            instance_id = secrets.token_hex(8).upper()
            db.session.add(Parametre(cle='instance_id', valeur=instance_id, etablissement_id=etab.id))
            
            db.session.commit()
            
            flash("Installation terminée ! Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur setup: {e}")
            flash(f"Erreur d'installation.", "error")

    return render_template('setup.html')

@auth_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    user_id = session.get('user_id')
    user = db.session.get(Utilisateur, user_id)
    
    if not user:
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        ancien_mdp = request.form.get('ancien_mot_de_passe')
        nouveau_mdp = request.form.get('nouveau_mot_de_passe')
        confirm_mdp = request.form.get('confirmation_mot_de_passe')

        if not ancien_mdp or not nouveau_mdp:
            flash("Veuillez remplir tous les champs.", "error")
        elif not check_password_hash(user.mot_de_passe, ancien_mdp):
            flash("Mot de passe actuel incorrect.", "error")
        elif nouveau_mdp != confirm_mdp:
            flash("Les nouveaux mots de passe ne correspondent pas.", "error")
        else:
            is_valid, msg = validate_password_strength(nouveau_mdp)
            if not is_valid:
                flash(msg, "error")
            else:
                try:
                    user.mot_de_passe = generate_password_hash(nouveau_mdp, method='pbkdf2:sha256')
                    db.session.commit()
                    
                    session.clear()
                    session.modified = True
                    flash("Mot de passe modifié avec succès. Veuillez vous reconnecter.", "success")
                    return redirect(url_for('auth.login'))
                    
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Erreur profil: {e}")
                    flash("Erreur lors de la mise à jour.", "error")
                
    return render_template('profil.html', user=user)