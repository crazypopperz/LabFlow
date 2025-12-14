# Fichier: views/auth.py

import re
import secrets
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError

# IMPORTS DB ET MODÈLES
from db import db, Utilisateur, Parametre, Etablissement
from utils import login_required, is_setup_needed

auth_bp = Blueprint(
    'auth', 
    __name__,
    template_folder='../templates',
    url_prefix='/auth'
)

def generer_code_invitation():
    """Génère un code unique comme LABFLOW-ABC123"""
    return f"LABFLOW-{secrets.token_hex(3).upper()}"

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Recherche de l'utilisateur
        user = db.session.execute(
            db.select(Utilisateur).filter_by(nom_utilisateur=username)
        ).scalar_one_or_none()

        if user and check_password_hash(user.mot_de_passe, password):
            # Configuration de la session
            session.permanent = (user.role != 'admin')
            session['user_id'] = user.id
            session['username'] = user.nom_utilisateur
            session['user_role'] = user.role
            session['etablissement_id'] = user.etablissement_id
            
            # Récupération du nom de l'établissement pour l'affichage
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
    # 1. Si l'utilisateur est déjà connecté, redirection
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
    
    # 2. Vérifier si le setup est nécessaire (sécurité)
    if is_setup_needed(current_app):
        return redirect(url_for('auth.setup'))
    
    if request.method == 'POST':
        # Récupération et nettoyage des données
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        code_invitation = request.form.get('code_invitation', '').strip().upper() # Force majuscules
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # --- VALIDATIONS ---
        
        # 1. Champs requis
        if not all([username, email, code_invitation, password, password_confirm]):
            flash("Tous les champs sont requis.", "error")
            return render_template('register.html')
        
        # 2. Correspondance des mots de passe
        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return render_template('register.html')
        
        # 3. Validation du Code d'Invitation (CRUCIAL POUR LE SAAS)
        etablissement = db.session.execute(
            db.select(Etablissement).filter_by(code_invitation=code_invitation)
        ).scalar_one_or_none()
        
        if not etablissement:
            flash("Code d'invitation invalide. Vérifiez auprès de votre administrateur.", "error")
            return render_template('register.html')

        # 4. Complexité du mot de passe (Doit correspondre au JS)
        # Au moins 12 chars, 1 maj, 1 min, 1 chiffre, 1 spécial
        if (len(password) < 12 or 
            not re.search(r"[a-z]", password) or 
            not re.search(r"[A-Z]", password) or 
            not re.search(r"[0-9]", password) or 
            not re.search(r"[^a-zA-Z0-9]", password)): # Tout caractère non alphanumérique est considéré comme spécial
            flash("Le mot de passe ne respecte pas les critères de sécurité (12 car., Maj, Min, Chiffre, Spécial).", "error")
            return render_template('register.html')
        
        # 5. Validation Email simple
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash("Format d'email invalide.", "error")
            return render_template('register.html')

        try:
            # --- CRÉATION DE L'UTILISATEUR ---
            new_user = Utilisateur(
                nom_utilisateur=username,
                email=email,
                mot_de_passe=generate_password_hash(password, method='scrypt'),
                role='utilisateur',  # Rôle par défaut pour une inscription publique
                etablissement_id=etablissement.id  # Liaison avec l'établissement trouvé
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f"Compte créé avec succès ! Bienvenue dans l'espace {etablissement.nom}.", "success")
            return redirect(url_for('auth.login'))
            
        except IntegrityError:
            db.session.rollback()
            # Message générique pour éviter de fuiter trop d'infos, ou spécifique si tu préfères
            flash(f"Le nom d'utilisateur '{username}' ou cet email est déjà utilisé.", "error")
            return render_template('register.html')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur inscription : {e}")
            flash("Une erreur interne est survenue.", "error")
            return render_template('register.html')
    
    return render_template('register.html')

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
        flash("Utilisateur non trouvé.", "error")
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        ancien_mdp = request.form.get('ancien_mot_de_passe')
        nouveau_mdp = request.form.get('nouveau_mot_de_passe')
        confirmation_mdp = request.form.get('confirmation_mot_de_passe')
        
        if not user or not check_password_hash(user.mot_de_passe, ancien_mdp):
            flash("Votre ancien mot de passe est incorrect.", "error")
            return redirect(url_for('auth.profil'))
        
        # Validation nouveau mot de passe
        if (len(nouveau_mdp) < 12 or 
            not re.search(r"[a-z]", nouveau_mdp) or 
            not re.search(r"[A-Z]", nouveau_mdp) or 
            not re.search(r"[0-9]", nouveau_mdp) or 
            not re.search(r"[^a-zA-Z0-9]", nouveau_mdp)):
            flash("Le nouveau mot de passe doit respecter les critères de sécurité.", "error")
            return redirect(url_for('auth.profil'))
            
        if nouveau_mdp != confirmation_mdp:
            flash("Les nouveaux mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.profil'))
        
        try:
            user.mot_de_passe = generate_password_hash(nouveau_mdp, method='scrypt')
            db.session.commit()
            flash("Votre mot de passe a été mis à jour avec succès.", "success")
            return redirect(url_for('inventaire.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur de base de données : {e}", "error")
    
    return render_template("profil.html", now=datetime.now())

@auth_bp.route("/setup", methods=['GET', 'POST'])
def setup():
    if not is_setup_needed(current_app):
        flash("L'application est déjà configurée.", "error")
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email', '').strip()
        nom_etablissement = request.form.get('nom_etablissement', '').strip()
        
        if not all([username, password, password_confirm, email]):
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for('auth.setup'))
            
        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.setup'))
            
        # Validation simplifiée pour le setup (ou identique au register, au choix)
        if len(password) < 12: 
            flash("Le mot de passe doit contenir au moins 12 caractères.", "error")
            return redirect(url_for('auth.setup'))
            
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash("L'adresse e-mail fournie n'est pas valide.", "error")
            return redirect(url_for('auth.setup'))
        
        try:
            if not nom_etablissement:
                flash("Le nom de l'établissement est obligatoire.", "error")
                return render_template('setup.html')

            # Créer l'établissement avec un code d'invitation
            nouvel_etablissement = Etablissement(
                nom=nom_etablissement,
                code_invitation=generer_code_invitation()
            )
            db.session.add(nouvel_etablissement)
            db.session.flush() # Pour récupérer l'ID

            admin_user = Utilisateur(
                nom_utilisateur=username,
                mot_de_passe=generate_password_hash(password, method='scrypt'),
                role='admin',
                email=email,
                etablissement_id=nouvel_etablissement.id
            )
            db.session.add(admin_user)

            # Paramètres par défaut
            instance_id = str(re.sub(r'[^a-zA-Z0-9]', '', str(datetime.now().timestamp()))) # Simple ID unique
            param_instance = Parametre(cle='instance_id', valeur=instance_id, etablissement_id=nouvel_etablissement.id)
            param_licence = Parametre(cle='licence_statut', valeur='FREE', etablissement_id=nouvel_etablissement.id)
            param_items = Parametre(cle='items_per_page', valeur='10', etablissement_id=nouvel_etablissement.id)
            db.session.add_all([param_instance, param_licence, param_items])
            
            db.session.commit()
            
            flash(f"Administrateur '{username}' créé avec succès ! Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash(f"Une erreur critique est survenue lors de l'initialisation : {e}", "error")
            return render_template('setup.html')
    
    return render_template('setup.html')