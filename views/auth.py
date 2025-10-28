# Fichier: views/auth.py

import re
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError

# NOUVEAUX IMPORTS : On importe l'objet db et les modèles nécessaires
from db import db, Utilisateur, Parametre, Etablissement
from utils import login_required, is_setup_needed

auth_bp = Blueprint(
    'auth', 
    __name__,
    template_folder='../templates',
    url_prefix='/auth'
)

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # LOGIQUE SQLAlchemy pour trouver un utilisateur
        user = db.session.execute(
            db.select(Utilisateur).filter_by(nom_utilisateur=username)
        ).scalar_one_or_none()

        if user and check_password_hash(user.mot_de_passe, password):
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
    if is_setup_needed(current_app):
        return redirect(url_for('auth.setup'))
    
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email').strip()
        
        # --- Votre logique de validation (inchangée) ---
        if not all([username, password, password_confirm, email]):
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for('auth.register'))
        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.register'))
        if len(password) < 12 or not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*(),.?:{}|<>]", password):
            flash("Le mot de passe doit contenir au moins 12 caractères, incluant une majuscule, une minuscule, un chiffre et un caractère spécial.", "error")
            return redirect(url_for('auth.register'))
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("L'adresse e-mail fournie n'est pas valide.", "error")
            return redirect(url_for('auth.register'))
        # --- Fin de la logique de validation ---

        try:
            # LOGIQUE SQLAlchemy pour insérer un nouvel utilisateur
            new_user = Utilisateur(
                nom_utilisateur=username,
                mot_de_passe=generate_password_hash(password, method='scrypt'),
                email=email,
                etablissement_id=session['etablissement_id']
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"Le compte '{username}' a été créé. Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for('auth.login'))
        except IntegrityError:
            db.session.rollback()
            flash(f"Le nom d'utilisateur '{username}' existe déjà.", "error")
            return redirect(url_for('auth.register'))
            
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
    
    # LOGIQUE SQLAlchemy pour récupérer un utilisateur par son ID
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
        
        # --- Votre logique de validation du nouveau mot de passe (inchangée) ---
        if len(nouveau_mdp) < 12 or not re.search(r"[a-z]", nouveau_mdp) or not re.search(r"[A-Z]", nouveau_mdp) or not re.search(r"[0-9]", nouveau_mdp) or not re.search(r"[!@#$%^&*(),.?:{}|<>]", nouveau_mdp):
            flash("Le nouveau mot de passe doit contenir au moins 12 caractères...", "error")
            return redirect(url_for('auth.profil'))
        if nouveau_mdp != confirmation_mdp:
            flash("Les nouveaux mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.profil'))
        # --- Fin de la logique de validation ---
        
        try:
            # LOGIQUE SQLAlchemy pour mettre à jour le mot de passe
            user.mot_de_passe = generate_password_hash(nouveau_mdp, method='scrypt')
            db.session.commit()
            flash("Votre mot de passe a été mis à jour avec succès.", "success")
            return redirect(url_for('inventaire.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur de base de données : {e}", "error")
    
    # NOTE : Les armoires et catégories sont pour le layout, elles seront gérées par un context_processor plus tard.
    # On les retire d'ici pour que la route soit fonctionnelle.
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
        
        # --- Votre logique de validation (inchangée) ---
        if not all([username, password, password_confirm, email]):
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for('auth.setup'))
        if password != password_confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return redirect(url_for('auth.setup'))
        if len(password) < 12 or not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password) or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*(),.?:{}|<>]", password):
            flash("Le mot de passe doit contenir au moins 12 caractères...", "error")
            return redirect(url_for('auth.setup'))
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("L'adresse e-mail fournie n'est pas valide.", "error")
            return redirect(url_for('auth.setup'))
        # --- Fin de la logique de validation ---
        
        try:
            if not nom_etablissement: # Petite sécurité supplémentaire
                flash("Le nom de l'établissement est obligatoire.", "error")
                return render_template('setup.html')

            nouvel_etablissement = Etablissement(nom=nom_etablissement)
            db.session.add(nouvel_etablissement)
            db.session.flush()

            admin_user = Utilisateur(
                nom_utilisateur=username,
                mot_de_passe=generate_password_hash(password, method='scrypt'),
                role='admin',
                email=email,
                etablissement_id=nouvel_etablissement.id
            )
            db.session.add(admin_user)

            instance_id = str(uuid.uuid4())
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