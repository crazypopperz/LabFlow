# ============================================================
# FICHIER : views/auth.py (Avec Récupération MDP)
# ============================================================
import secrets
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from db import db, Utilisateur, Etablissement, Parametre
from utils import get_etablissement_params, login_required, validate_password_strength, validate_email
from extensions import limiter
from threading import Thread

# NOUVEAUX IMPORTS POUR L'EMAIL
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

auth_bp = Blueprint('auth', __name__)

# --- UTILITAIRES EMAIL ---
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def send_async_email(app, msg):
    """Envoie l'email dans un thread séparé."""
    print("🧵 THREAD DÉMARRÉ !!!")
    with app.app_context():
        try:
            mail = app.extensions.get('mail')
            print(f"📧 Envoi vers: {msg.recipients}")
            mail.send(msg)
            print("✅ Email envoyé en arrière-plan")
        except Exception as e:
            print(f"❌ Erreur mail async: {e}")
            import traceback
            traceback.print_exc()
            app.logger.error(f"Erreur envoi mail: {e}")
    print("🧵 THREAD TERMINÉ")

def send_reset_email(user_email, token):
    """Envoie l'email via l'API SendGrid (pas SMTP)."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        message = Mail(
            from_email='help.labflow@gmail.com',
            to_emails=user_email,
            subject='Réinitialisation de votre mot de passe LabFlow',
            plain_text_content=f"""Bonjour,

Une demande de réinitialisation de mot de passe a été effectuée pour votre compte LabFlow.

Pour définir un nouveau mot de passe, cliquez sur le lien suivant (valable 1 heure) :
{reset_url}

Si vous n'êtes pas à l'origine de cette demande, ignorez simplement cet email.

Cordialement,
L'équipe LabFlow
""")
        
        api_key = current_app.config.get('SENDGRID_API_KEY')
        if not api_key:
            print("❌ SENDGRID_API_KEY manquante !")
            return False
            
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        print(f"✅ Email envoyé via API SendGrid ! Status: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"❌ ERREUR SendGrid API: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- ROUTES EXISTANTES ---

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
        
        if not validate_email(email):
            flash("Format d'email invalide.", "error")
            return render_template('register.html')

        is_valid_pass, msg_pass = validate_password_strength(password)
        if not is_valid_pass:
            flash(msg_pass, "error")
            return render_template('register.html')

        etablissement = db.session.execute(db.select(Etablissement).filter_by(code_invitation=code_invitation)).scalar_one_or_none()
        if not etablissement:
            flash("Code d'invitation invalide.", "error")
            return render_template('register.html')
            
        existing_user = db.session.execute(db.select(Utilisateur).filter_by(nom_utilisateur=username)).scalar_one_or_none()
        if existing_user:
            flash(f"Le nom d'utilisateur '{username}' est déjà pris.", "error")
            return render_template('register.html')
            
        existing_email = db.session.execute(db.select(Utilisateur).filter_by(email=email)).scalar_one_or_none()
        if existing_email:
            flash("Cet email est déjà utilisé.", "error")
            return render_template('register.html')

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
            flash("Compte créé ! Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur register: {e}")
            flash("Erreur technique.", "error")
            
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def setup():
    if request.method == 'POST':
        nom_etablissement = request.form.get('nom_etablissement')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not validate_email(email):
            flash("Format d'email invalide.", "error")
            return render_template('setup.html')

        is_valid_pass, msg_pass = validate_password_strength(password)
        if not is_valid_pass:
            flash(msg_pass, "error")
            return render_template('setup.html')

        user_exist = db.session.execute(db.select(Utilisateur).filter_by(nom_utilisateur=username)).scalar_one_or_none()
        if user_exist:
            flash(f"Le nom d'utilisateur '{username}' est déjà pris.", "error")
            return render_template('setup.html')

        email_exist = db.session.execute(db.select(Utilisateur).filter_by(email=email)).scalar_one_or_none()
        if email_exist:
            flash("Cet email est déjà utilisé.", "error")
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
            
            flash(f"Établissement créé ! Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur setup: {e}")
            flash(f"Erreur technique.", "error")

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

# --- NOUVELLES ROUTES : MOT DE PASSE OUBLIÉ ---

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        print(f"🔍 DEBUG: Tentative de reset pour l'email : '{email}'")
        
        user = db.session.execute(db.select(Utilisateur).filter_by(email=email)).scalar_one_or_none()
        
        if user:
            print(f"👤 DEBUG: Utilisateur trouvé ! ID: {user.id}, Nom: {user.nom_utilisateur}")
            s = get_serializer()
            token = s.dumps(user.email, salt='password-reset-salt')
            
            if send_reset_email(user.email, token):
                flash("Un email de réinitialisation a été envoyé.", "info")
            else:
                flash("Erreur technique lors de l'envoi.", "error")
        else:
            print(f"⚠️ DEBUG: AUCUN utilisateur trouvé avec cet email dans la BDD.")
            flash("Si cet email existe, un lien a été envoyé.", "info")
            
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        s = get_serializer()
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash("Le lien de réinitialisation a expiré.", "error")
        return redirect(url_for('auth.forgot_password'))
    except BadSignature:
        flash("Le lien de réinitialisation est invalide.", "error")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", "error")
            return render_template('reset_password.html', token=token)
            
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            flash(msg, "error")
            return render_template('reset_password.html', token=token)
            
        user = db.session.execute(db.select(Utilisateur).filter_by(email=email)).scalar_one_or_none()
        if user:
            user.mot_de_passe = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            flash("Votre mot de passe a été modifié avec succès. Connectez-vous.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("Utilisateur introuvable.", "error")
            return redirect(url_for('auth.login'))
            
    return render_template('reset_password.html', token=token)
