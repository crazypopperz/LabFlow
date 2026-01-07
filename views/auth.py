import re
import uuid
import secrets
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_

# Imports DB
from db import db, Utilisateur, Parametre, Etablissement
from utils import login_required, is_setup_needed

auth_bp = Blueprint('auth', __name__, template_folder='../templates', url_prefix='/auth')

# --- HELPERS DE VALIDATION ---

def validate_email(email):
    """Validation basique du format email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password):
    """
    Vérifie que le mot de passe respecte la politique de sécurité (Aligné avec le HTML) :
    - 12 caractères min
    - 1 Majuscule, 1 Minuscule, 1 Chiffre, 1 Spécial
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
    """Nettoie et limite la longueur des entrées utilisateur"""
    if not text:
        return ""
    text = text.strip()[:max_length]
    # Retire les caractères de contrôle non imprimables
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text

def generer_code_invitation():
    """Génère un code unique comme LABFLOW-ABC123"""
    return f"LABFLOW-{secrets.token_hex(3).upper()}"

# --- ROUTES ---

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Syntaxe SQLAlchemy 2.0
        user = db.session.execute(
            db.select(Utilisateur).filter_by(nom_utilisateur=username)
        ).scalar_one_or_none()

        if user and check_password_hash(user.mot_de_passe, password):
            session.clear() # Protection Fixation de Session
            
            session.permanent = (user.role != 'admin')
            session['user_id'] = user.id
            session['username'] = user.nom_utilisateur
            session['user_role'] = user.role
            session['etablissement_id'] = user.etablissement_id
            
            etablissement = db.session.get(Etablissement, user.etablissement_id)
            if etablissement:
                session['nom_etablissement'] = etablissement.nom
                
            flash(f"Bienvenue, {user.nom_utilisateur} !", "success")
            return redirect(url_for('inventaire.index'))
        else:
            flash("Nom d'utilisateur ou mot de passe invalide.", "error")
            
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
    
    if is_setup_needed(current_app):
        return redirect(url_for('auth.setup'))
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        email = sanitize_input(request.form.get('email', ''))
        code_invitation = request.form.get('code_invitation', '').strip().upper()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if not all([username, email, code_invitation, password, password_confirm]):
            flash("Tous les champs sont requis.", "error")
            return render_template('register.html')
        
        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return render_template('register.html')
        
        # Validation MDP
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            flash(msg, "error")
            return render_template('register.html')

        # Validation Email
        if not validate_email(email):
            flash("Format d'email invalide.", "error")
            return render_template('register.html')
        
        # Vérification Code Invitation
        etablissement = db.session.execute(
            db.select(Etablissement).filter_by(code_invitation=code_invitation)
        ).scalar_one_or_none()
        
        if not etablissement:
            flash("Code d'invitation invalide.", "error")
            return render_template('register.html')

        try:
            new_user = Utilisateur(
                nom_utilisateur=username,
                email=email,
                mot_de_passe=generate_password_hash(password, method='pbkdf2:sha256'),
                role='utilisateur',
                etablissement_id=etablissement.id
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash(f"Compte créé ! Bienvenue dans {etablissement.nom}.", "success")
            return redirect(url_for('auth.login'))
            
        except IntegrityError:
            db.session.rollback()
            flash(f"Le nom d'utilisateur ou l'email est déjà utilisé.", "error")
            return render_template('register.html')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur inscription : {e}")
            flash("Erreur technique.", "error")
            return render_template('register.html')
    
    return render_template('register.html')

@auth_bp.route("/setup", methods=['GET', 'POST'])
def setup():
    """
    Initialisation de l'application : création de l'établissement et du premier admin.
    """
    if not is_setup_needed(current_app):
        flash("L'application est déjà configurée. Connectez-vous.", "warning")
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # Nettoyage
        nom_etablissement = sanitize_input(request.form.get('nom_etablissement', ''), max_length=200)
        username = sanitize_input(request.form.get('username', ''), max_length=50)
        email = sanitize_input(request.form.get('email', ''), max_length=100)
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        errors = []
        
        # Validations
        if not nom_etablissement or len(nom_etablissement) < 3:
            errors.append("Nom de l'établissement invalide (min 3 caractères).")
            
        if not username or len(username) < 3:
            errors.append("Nom d'utilisateur invalide (min 3 caractères).")
            
        if not validate_email(email):
            errors.append("Format d'email invalide.")
            
        if password != password_confirm:
            errors.append("Les mots de passe ne correspondent pas.")
        else:
            is_valid, pwd_msg = validate_password_strength(password)
            if not is_valid:
                errors.append(pwd_msg)
        
        if errors:
            for error in errors: flash(error, "danger")
            return render_template('setup.html')
        
        try:
            # Vérification unicité (Syntaxe SQLAlchemy 2.0)
            existing_user = db.session.execute(
                db.select(Utilisateur).filter(
                    (Utilisateur.nom_utilisateur == username) | 
                    (Utilisateur.email == email)
                )
            ).scalar_one_or_none()
            
            if existing_user:
                flash("Ce nom d'utilisateur ou cet email existe déjà.", "danger")
                return render_template('setup.html')
            
            # Création Etablissement
            code_invit = f"LABFLOW-{secrets.token_hex(3).upper()}"
            nouvel_etablissement = Etablissement(
                nom=nom_etablissement,
                code_invitation=code_invit
            )
            db.session.add(nouvel_etablissement)
            db.session.flush()
            
            # Création Admin
            admin_user = Utilisateur(
                nom_utilisateur=username,
                mot_de_passe=generate_password_hash(password, method='scrypt'),
                role='admin',
                email=email,
                etablissement_id=nouvel_etablissement.id
            )
            db.session.add(admin_user)
            
            # Paramètres
            instance_id = str(uuid.uuid4())
            now_iso = datetime.now().isoformat()
            
            params = [
                Parametre(cle='instance_id', valeur=instance_id, etablissement_id=nouvel_etablissement.id),
                Parametre(cle='licence_statut', valeur='FREE', etablissement_id=nouvel_etablissement.id),
                Parametre(cle='licence_date_creation', valeur=now_iso, etablissement_id=nouvel_etablissement.id)
            ]
            db.session.add_all(params)
            
            db.session.commit()
            
            current_app.logger.info(f"Setup completed: Etab {nouvel_etablissement.id}, Admin {admin_user.id}")
            
            flash(f"Félicitations ! Configuration terminée. Votre code d'invitation : {code_invit}", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.critical(f"Erreur Setup : {e}")
            flash("Une erreur critique est survenue.", "danger")
            return render_template('setup.html')
    
    return render_template('setup.html')

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for('auth.login'))

@auth_bp.route("/profil", methods=['GET', 'POST'])
@login_required
def profil():
    user_id = session['user_id']
    user = db.session.get(Utilisateur, user_id)
    
    if not user:
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        ancien_mdp = request.form.get('ancien_mot_de_passe')
        nouveau_mdp = request.form.get('nouveau_mot_de_passe')
        confirmation_mdp = request.form.get('confirmation_mot_de_passe')
        
        if not check_password_hash(user.mot_de_passe, ancien_mdp):
            flash("Ancien mot de passe incorrect.", "error")
            return redirect(url_for('auth.profil'))
        
        if nouveau_mdp != confirmation_mdp:
            flash("Les nouveaux mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.profil'))

        is_valid, msg = validate_password_strength(nouveau_mdp)
        if not is_valid:
            flash(msg, "error")
            return redirect(url_for('auth.profil'))
        
        try:
            user.mot_de_passe = generate_password_hash(nouveau_mdp, method='scrypt')
            db.session.commit()
            flash("Mot de passe mis à jour.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Erreur technique.", "error")
    
    return render_template("profil.html", now=datetime.now())