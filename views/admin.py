# ============================================================
# IMPORTS
# ============================================================
import hashlib
import shutil
import secrets
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_file, current_app)
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Pour Excel
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation

# Pour PDF
from fpdf import FPDF

# Pour HTML
from html import escape

# Modèles et DB
# NOTE: J'ai ajouté Historique et Reservation aux imports pour la suppression sécurisée
from db import db, Utilisateur, Parametre, Objet, Armoire, Categorie, Fournisseur, Kit, KitObjet, Budget, Depense, Echeance, Etablissement, Historique, Reservation, Suggestion
from utils import admin_required, login_required

# Imports Exports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# ============================================================
# CONFIGURATION
# ============================================================
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

MAX_EXPORT_LIMIT = 3000  # Limite pour éviter le DoS sur l'export Excel

# ============================================================
# UTILITAIRES
# ============================================================
def generer_code_unique():
    """Génère un code unique avec une limite de tentatives pour éviter les boucles infinies."""
    max_retries = 10
    for _ in range(max_retries):
        code = f"LABFLOW-{secrets.token_hex(3).upper()}"
        # Vérification optimisée : on ne récupère que l'ID, pas l'objet entier
        exists = db.session.execute(
            db.select(Etablissement.id).filter_by(code_invitation=code)
        ).scalar_one_or_none()
        
        if not exists:
            return code
    
    # Fallback extrême si collision (très improbable)
    return f"LABFLOW-{secrets.token_hex(6).upper()}"

# ============================================================
# ROUTE PRINCIPALE
# ============================================================
@admin_bp.route("/")
@admin_required
def admin():
    etablissement_id = session.get('etablissement_id')
    
    # 1. Récupération de l'établissement
    etablissement = db.session.get(Etablissement, etablissement_id)
    if not etablissement:
        flash("Erreur critique : Établissement introuvable.", "error")
        return redirect(url_for('auth.login'))

    # 2. AUTO-RÉPARATION sécurisée du code invitation
    if not etablissement.code_invitation:
        try:
            etablissement.code_invitation = generer_code_unique()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur génération code invitation: {e}")

    # 3. Récupération des suggestions (pour la carte dynamique)
    suggestions = db.session.execute(
        db.select(Suggestion)
        .options(joinedload(Suggestion.objet), joinedload(Suggestion.utilisateur))
        .filter_by(etablissement_id=etablissement_id, statut='En attente')
        .order_by(Suggestion.date_demande.desc())
        .limit(4)
    ).scalars().all()

    # 4. Récupération des infos de licence via Parametre
    params = db.session.execute(
        db.select(Parametre).filter_by(etablissement_id=etablissement_id)
    ).scalars().all()
    
    params_dict = {p.cle: p.valeur for p in params}
    
    licence_info = {
        'is_pro': params_dict.get('licence_statut') == 'PRO',
        'instance_id': params_dict.get('instance_id', 'N/A'),
        'statut': params_dict.get('licence_statut', 'FREE')
    }

    return render_template(
        "admin.html", 
        now=datetime.now(), 
        licence=licence_info,
        etablissement=etablissement,
        suggestions=suggestions
    )

# ============================================================
# GESTION ARMOIRES / CATÉGORIES
# ============================================================
@admin_bp.route("/ajouter", methods=["POST"])
@admin_required
def ajouter():
    etablissement_id = session['etablissement_id']
    type_objet = request.form.get("type")
    nom = request.form.get("nom", "").strip()
    
    if not nom:
        flash("Le nom ne peut pas être vide.", "error")
        return redirect(request.referrer)

    Model = Armoire if type_objet == "armoire" else Categorie
    
    try:
        nouvel_element = Model(nom=nom, etablissement_id=etablissement_id)
        db.session.add(nouvel_element)
        db.session.commit()
        flash(f"L'élément '{nom}' a été créé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"L'élément '{nom}' existe déjà.", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur technique : {e}", "error")
    
    redirect_to = "main.gestion_armoires" if type_objet == "armoire" else "main.gestion_categories"
    return redirect(url_for(redirect_to))

@admin_bp.route("/supprimer/<type_objet>/<int:id>", methods=["POST"])
@admin_required
def supprimer(type_objet, id):
    etablissement_id = session['etablissement_id']
    
    if type_objet == "armoire":
        Model = Armoire
        redirect_to = "main.gestion_armoires"
    elif type_objet == "categorie":
        Model = Categorie
        redirect_to = "main.gestion_categories"
    else:
        flash("Type d'élément non valide.", "error")
        return redirect(url_for('admin.admin'))

    element = db.session.get(Model, id)

    if not element or element.etablissement_id != etablissement_id:
        flash("Élément non trouvé ou accès non autorisé.", "error")
        return redirect(url_for(redirect_to))

    # Vérification des dépendances
    if type_objet == "armoire":
        count = db.session.query(Objet).filter_by(armoire_id=id, etablissement_id=etablissement_id).count()
    else:
        count = db.session.query(Objet).filter_by(categorie_id=id, etablissement_id=etablissement_id).count()
        
    if count > 0:
        flash(f"Impossible de supprimer '{element.nom}' car il contient encore {count} objet(s).", "error")
        return redirect(url_for(redirect_to))

    try:
        nom_element = element.nom
        db.session.delete(element)
        db.session.commit()
        flash(f"L'élément '{nom_element}' a été supprimé.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {e}", "error")
    
    return redirect(url_for(redirect_to))

# --- ENDPOINTS JSON SÉCURISÉS ---
@admin_bp.route("/modifier_armoire", methods=["POST"])
@admin_required
def modifier_armoire():
    # Protection CSRF implicite via Flask-WTF global, mais on gère les erreurs proprement
    try:
        etablissement_id = session['etablissement_id']
        data = request.get_json()
        if not data:
            return jsonify(success=False, error="Données JSON manquantes"), 400
            
        armoire_id = data.get("id")
        nouveau_nom = data.get("nom", "").strip()

        if not all([armoire_id, nouveau_nom]):
            return jsonify(success=False, error="Données invalides"), 400

        armoire = db.session.get(Armoire, armoire_id)

        if not armoire or armoire.etablissement_id != etablissement_id:
            return jsonify(success=False, error="Armoire introuvable"), 404

        armoire.nom = nouveau_nom
        db.session.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom)
    
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Ce nom existe déjà"), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modifier_armoire: {e}")
        return jsonify(success=False, error="Erreur serveur"), 500

@admin_bp.route("/modifier_categorie", methods=["POST"])
@admin_required
def modifier_categorie():
    try:
        etablissement_id = session['etablissement_id']
        data = request.get_json()
        if not data:
            return jsonify(success=False, error="Données JSON manquantes"), 400

        categorie_id = data.get("id")
        nouveau_nom = data.get("nom", "").strip()

        if not all([categorie_id, nouveau_nom]):
            return jsonify(success=False, error="Données invalides"), 400

        categorie = db.session.get(Categorie, categorie_id)

        if not categorie or categorie.etablissement_id != etablissement_id:
            return jsonify(success=False, error="Catégorie introuvable"), 404

        categorie.nom = nouveau_nom
        db.session.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom)
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Ce nom existe déjà"), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modifier_categorie: {e}")
        return jsonify(success=False, error="Erreur serveur"), 500

# ============================================================
# GESTION UTILISATEURS
# ============================================================
@admin_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    etablissement_id = session['etablissement_id']
    utilisateurs = db.session.execute(
        db.select(Utilisateur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Utilisateur.nom_utilisateur)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Utilisateurs'}
    ]
    
    return render_template("admin_utilisateurs.html", utilisateurs=utilisateurs, breadcrumbs=breadcrumbs, now=datetime.now)

@admin_bp.route("/utilisateurs/ajouter", methods=["POST"])
@admin_required
def ajouter_utilisateur():
    etablissement_id = session['etablissement_id']
    nom_utilisateur = request.form.get('nom_utilisateur', '').strip()
    email = request.form.get('email', '').strip()
    mot_de_passe = request.form.get('mot_de_passe', '').strip()
    est_admin = 'est_admin' in request.form

    if not nom_utilisateur or not mot_de_passe:
        flash("Champs obligatoires manquants.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    if len(mot_de_passe) < 4:
        flash("Le mot de passe est trop court.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        nouvel_utilisateur = Utilisateur(
            nom_utilisateur=nom_utilisateur,
            email=email or None,
            mot_de_passe=generate_password_hash(mot_de_passe, method='scrypt'),
            role='admin' if est_admin else 'utilisateur',
            etablissement_id=etablissement_id
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()
        flash(f"Utilisateur '{nom_utilisateur}' créé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"L'utilisateur '{nom_utilisateur}' existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur technique : {e}", "danger")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    etablissement_id = session['etablissement_id']
    email = request.form.get('email', '').strip()
    
    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.email = email if email else None
        db.session.commit()
        flash("Email mis à jour.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {e}", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
def reinitialiser_mdp(id_user):
    etablissement_id = session['etablissement_id']
    
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin.gestion_utilisateurs'))

    nouveau_mdp = request.form.get('nouveau_mot_de_passe')
    confirmation_mdp = request.form.get('confirmation_mot_de_passe')

    # 1. Vérification de la correspondance
    if nouveau_mdp != confirmation_mdp:
        flash("Les mots de passe ne correspondent pas.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    # 2. Vérification de la complexité (Regex identique au register)
    import re
    if (len(nouveau_mdp) < 12 or 
        not re.search(r"[a-z]", nouveau_mdp) or 
        not re.search(r"[A-Z]", nouveau_mdp) or 
        not re.search(r"[0-9]", nouveau_mdp) or 
        not re.search(r"[^a-zA-Z0-9]", nouveau_mdp)):
        flash("Le mot de passe ne respecte pas les critères de sécurité (12 car., Maj, Min, Chiffre, Spécial).", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.mot_de_passe = generate_password_hash(nouveau_mdp, method='scrypt')
        db.session.commit()
        flash(f"Mot de passe réinitialisé avec succès pour {user.nom_utilisateur}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {e}", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/supprimer/<int:id_user>", methods=["POST"])
@admin_required
def supprimer_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Impossible de supprimer son propre compte.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    user = db.session.get(Utilisateur, id_user)
    
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        # VÉRIFICATION DES DÉPENDANCES (Soft Delete)
        has_history = db.session.query(Historique).filter_by(utilisateur_id=user.id).first()
        has_reservations = db.session.query(Reservation).filter_by(utilisateur_id=user.id).first()

        if has_history or has_reservations:
            # ANONYMISATION au lieu de suppression
            user.nom_utilisateur = f"Utilisateur_Supprimé_{user.id}_{secrets.token_hex(2)}"
            user.email = None
            user.mot_de_passe = "deleted"
            user.role = "desactive" # Assure-toi que ton app gère ce rôle ou bloque le login
            db.session.commit()
            flash("Utilisateur anonymisé et désactivé (car il possède un historique).", "warning")
        else:
            # Suppression réelle si aucune trace
            db.session.delete(user)
            db.session.commit()
            flash("Utilisateur supprimé définitivement.", "success")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {e}", "error")
        
    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/promouvoir/<int:id_user>", methods=["POST"])
@admin_required
def promouvoir_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    target_user = db.session.get(Utilisateur, id_user)
    current_admin = db.session.get(Utilisateur, session['user_id'])
    
    if not target_user or target_user.etablissement_id != etablissement_id:
        flash("Utilisateur cible introuvable.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    password_confirm = request.form.get('password')
    if not password_confirm or not check_password_hash(current_admin.mot_de_passe, password_confirm):
        flash("Mot de passe incorrect.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        target_user.role = 'admin'
        current_admin.role = 'utilisateur'
        db.session.commit()
        session['user_role'] = 'utilisateur'
        flash(f"Passation réussie ! {target_user.nom_utilisateur} est désormais administrateur.", "success")
        return redirect(url_for('inventaire.index'))
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur critique : {e}", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

# ============================================================
# GESTION DES KITS
# ============================================================
@admin_bp.route("/kits")
@admin_required
def gestion_kits():
    etablissement_id = session['etablissement_id']
    
    kits_data = db.session.execute(
        db.select(Kit, func.count(KitObjet.id).label('count'))
        .outerjoin(KitObjet, Kit.id == KitObjet.kit_id)
        .filter(Kit.etablissement_id == etablissement_id)
        .group_by(Kit.id)
        .order_by(Kit.nom)
    ).mappings().all()

    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Kits'}]
    return render_template("admin_kits.html", kits=kits_data, breadcrumbs=breadcrumbs)

@admin_bp.route("/kits/ajouter", methods=["POST"])
@admin_required
def ajouter_kit():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()

    if not nom:
        flash("Nom du kit requis.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    try:
        nouveau_kit = Kit(nom=nom, description=description, etablissement_id=etablissement_id)
        db.session.add(nouveau_kit)
        db.session.commit()
        flash(f"Kit '{nom}' créé.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=nouveau_kit.id))
    except IntegrityError:
        db.session.rollback()
        flash("Ce kit existe déjà.", "danger")
        return redirect(url_for('admin.gestion_kits'))

@admin_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if not kit or kit.etablissement_id != etablissement_id:
        flash("Kit introuvable.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    if request.method == "POST":
        try:
            objet_id_str = request.form.get("objet_id")
            if objet_id_str:
                # Ajout d'un objet
                objet_id = int(objet_id_str)
                quantite = int(request.form.get("quantite", 1))
                
                objet = db.session.get(Objet, objet_id)
                if not objet or objet.etablissement_id != etablissement_id:
                    flash("Objet invalide.", "danger")
                else:
                    assoc = db.session.execute(
                        db.select(KitObjet).filter_by(kit_id=kit.id, objet_id=objet_id)
                    ).scalar_one_or_none()
                    
                    if assoc:
                        assoc.quantite += quantite
                    else:
                        db.session.add(KitObjet(kit_id=kit.id, objet_id=objet_id, quantite=quantite, etablissement_id=etablissement_id))
                    db.session.commit()
                    flash("Objet ajouté.", "success")
            else:
                # Mise à jour quantités
                for key, value in request.form.items():
                    if key.startswith("quantite_"):
                        k_id = int(key.split("_")[1])
                        assoc = db.session.get(KitObjet, k_id)
                        if assoc and assoc.kit_id == kit.id:
                            if int(value) > 0:
                                assoc.quantite = int(value)
                            else:
                                db.session.delete(assoc)
                db.session.commit()
                flash("Quantités mises à jour.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {e}", "danger")
            
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

    objets_in_kit = db.session.execute(
        db.select(KitObjet).filter_by(kit_id=kit.id).options(joinedload(KitObjet.objet))
    ).scalars().all()
    
    ids_in_kit = [o.objet_id for o in objets_in_kit]
    
    objets_disponibles = db.session.execute(
        db.select(Objet).filter(Objet.etablissement_id == etablissement_id, ~Objet.id.in_(ids_in_kit)).order_by(Objet.nom)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Kits', 'url': url_for('admin.gestion_kits')},
        {'text': kit.nom}
    ]
    return render_template("admin_kit_modifier.html", kit=kit, breadcrumbs=breadcrumbs, objets_in_kit=objets_in_kit, objets_disponibles=objets_disponibles)

@admin_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=["POST"])
@admin_required
def retirer_objet_kit(kit_objet_id):
    etablissement_id = session['etablissement_id']
    assoc = db.session.get(KitObjet, kit_objet_id)
    
    if assoc and assoc.etablissement_id == etablissement_id:
        kit_id = assoc.kit_id
        try:
            db.session.delete(assoc)
            db.session.commit()
            flash("Objet retiré.", "success")
            return redirect(url_for('admin.modifier_kit', kit_id=kit_id))
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors du retrait.", "danger")
    
    return redirect(url_for('admin.gestion_kits'))

@admin_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if kit and kit.etablissement_id == etablissement_id:
        try:
            db.session.delete(kit)
            db.session.commit()
            flash("Kit supprimé.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {e}", "danger")
    return redirect(url_for('admin.gestion_kits'))

# ============================================================
# GESTION ÉCHÉANCES
# ============================================================
@admin_bp.route("/echeances", methods=['GET'])
@admin_required
def gestion_echeances():
    etablissement_id = session['etablissement_id']
    echeances = db.session.execute(
        db.select(Echeance).filter_by(etablissement_id=etablissement_id).order_by(Echeance.date_echeance.asc())
    ).scalars().all()

    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Échéances'}]
    return render_template("admin_echeances.html", echeances=echeances, breadcrumbs=breadcrumbs, date_actuelle=date.today())

@admin_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    etablissement_id = session['etablissement_id']
    try:
        nouvelle = Echeance(
            intitule=request.form.get('intitule'),
            date_echeance=datetime.strptime(request.form.get('date_echeance'), '%Y-%m-%d').date(),
            details=request.form.get('details'),
            etablissement_id=etablissement_id
        )
        db.session.add(nouvelle)
        db.session.commit()
        flash("Échéance ajoutée.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur: {e}", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    
    if echeance and echeance.etablissement_id == etablissement_id:
        try:
            echeance.intitule = request.form.get('intitule')
            echeance.date_echeance = datetime.strptime(request.form.get('date_echeance'), '%Y-%m-%d').date()
            echeance.details = request.form.get('details')
            echeance.traite = 1 if 'traite' in request.form else 0
            db.session.commit()
            flash("Échéance modifiée.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur: {e}", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    if echeance and echeance.etablissement_id == etablissement_id:
        try:
            db.session.delete(echeance)
            db.session.commit()
            flash("Échéance supprimée.", "success")
        except Exception:
            db.session.rollback()
            flash("Erreur suppression.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

# ============================================================
# GESTION BUDGET
# ============================================================

@admin_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    etablissement_id = session['etablissement_id']
    try:
        montant = float(request.form.get('montant_initial', 0).replace(',', '.'))
        annee = int(request.form.get('annee'))
        
        budget = db.session.execute(
            db.select(Budget).filter_by(annee=annee, etablissement_id=etablissement_id)
        ).scalar_one_or_none()
        
        if budget:
            budget.montant_initial = montant
            budget.cloture = False
        else:
            db.session.add(Budget(annee=annee, montant_initial=montant, etablissement_id=etablissement_id))
        
        db.session.commit()
        flash("Budget mis à jour.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur: {e}", "danger")
    return redirect(url_for('admin.budget', annee=annee))

@admin_bp.route("/budget/depense/ajouter", methods=['POST'])
@admin_required
def ajouter_depense():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération sécurisée des données brutes
    budget_id_raw = request.form.get('budget_id')
    fournisseur_id_raw = request.form.get('fournisseur_id')
    est_bon_achat = 'est_bon_achat' in request.form
    
    try:
        # 2. Vérification du Budget
        if not budget_id_raw:
            raise ValueError("Aucun budget actif n'est défini pour ajouter une dépense.")
            
        budget = db.session.get(Budget, int(budget_id_raw))
        if not budget or budget.etablissement_id != etablissement_id:
            raise ValueError("Budget invalide ou introuvable.")
        
        if budget.cloture:
            raise ValueError("Ce budget est clôturé, impossible d'ajouter une dépense.")

        # 3. Gestion du Fournisseur
        fournisseur_id = None
        if not est_bon_achat:
            # Si ce n'est pas un bon d'achat, le fournisseur est OBLIGATOIRE
            if not fournisseur_id_raw:
                raise ValueError("Veuillez sélectionner un fournisseur.")
            fournisseur_id = int(fournisseur_id_raw)

        # 4. Création de la dépense
        nouvelle = Depense(
            date_depense=datetime.strptime(request.form.get('date_depense'), '%Y-%m-%d').date(),
            contenu=request.form.get('contenu'),
            montant=float(request.form.get('montant').replace(',', '.')),
            est_bon_achat=est_bon_achat,
            fournisseur_id=fournisseur_id,
            budget_id=budget.id,
            etablissement_id=etablissement_id
        )
        
        db.session.add(nouvelle)
        db.session.commit()
        flash("Dépense ajoutée avec succès.", "success")
        
    except ValueError as e:
        # Erreurs de conversion ou validation métier
        flash(f"Erreur de saisie : {e}", "warning")
    except Exception as e:
        # Erreurs techniques (base de données, etc.)
        db.session.rollback()
        flash(f"Erreur technique : {e}", "danger")
        
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    etablissement_id = session['etablissement_id']
    now = datetime.now()
    # On considère que l'année scolaire change en Août (mois 8)
    annee_scolaire_actuelle = now.year if now.month >= 8 else now.year - 1
    
    try:
        annee_selectionnee = int(request.args.get('annee', annee_scolaire_actuelle))
    except ValueError:
        annee_selectionnee = annee_scolaire_actuelle

    # 1. Récupérer l'historique
    budgets_archives = db.session.execute(
        db.select(Budget).filter_by(etablissement_id=etablissement_id).order_by(Budget.annee.desc())
    ).scalars().all()

    # 2. Récupérer le budget affiché
    budget_affiche = db.session.execute(
        db.select(Budget).filter_by(etablissement_id=etablissement_id, annee=annee_selectionnee)
    ).scalar_one_or_none()

    # 3. Initialisation auto si aucun budget n'existe
    if not budget_affiche and not budgets_archives:
        try:
            budget_affiche = Budget(annee=annee_selectionnee, montant_initial=0.0, etablissement_id=etablissement_id)
            db.session.add(budget_affiche)
            db.session.commit()
            budgets_archives.insert(0, budget_affiche)
        except IntegrityError:
            db.session.rollback()

    # 4. Calculs des totaux
    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_affiche:
        depenses = sorted(budget_affiche.depenses, key=lambda d: d.date_depense, reverse=True)
        total_depenses = sum(d.montant for d in budget_affiche.depenses)
        solde = budget_affiche.montant_initial - total_depenses
        if date.today() >= date(budget_affiche.annee + 1, 6, 1):
            cloture_autorisee = True

    # 5. --- CORRECTION : Définir le budget actif pour les modales ---
    # C'est ce qui manquait pour activer le bouton !
    budget_actuel_pour_modales = None
    
    # Si le budget affiché est ouvert, c'est lui qu'on modifie
    if budget_affiche and not budget_affiche.cloture:
        budget_actuel_pour_modales = budget_affiche
    else:
        # Sinon, on cherche le dernier budget ouvert
        budget_actuel_pour_modales = db.session.execute(
            db.select(Budget).filter_by(etablissement_id=etablissement_id, cloture=False).order_by(Budget.annee.desc())
        ).scalars().first()

    # Calcul de l'année à proposer pour une création
    annee_proposee_pour_creation = annee_scolaire_actuelle
    if budgets_archives and budgets_archives[0].annee >= annee_scolaire_actuelle:
        annee_proposee_pour_creation = budgets_archives[0].annee + 1
    # ---------------------------------------------------------------

    fournisseurs = db.session.execute(
        db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)
    ).scalars().all()
    
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Budget'}]
    
    return render_template("budget.html", 
                           breadcrumbs=breadcrumbs, 
                           budget_affiche=budget_affiche,
                           budget_actuel_pour_modales=budget_actuel_pour_modales, # Indispensable
                           annee_proposee_pour_creation=annee_proposee_pour_creation, # Indispensable
                           depenses=depenses, 
                           total_depenses=total_depenses, 
                           solde=solde,
                           fournisseurs=fournisseurs, 
                           budgets_archives=budgets_archives,
                           annee_selectionnee=annee_selectionnee, 
                           cloture_autorisee=cloture_autorisee, 
                           now=now)

@admin_bp.route("/budget/depense/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    etablissement_id = session['etablissement_id']
    depense = db.session.get(Depense, id)
    if depense and depense.etablissement_id == etablissement_id:
        try:
            db.session.delete(depense)
            db.session.commit()
            flash("Dépense supprimée.", "success")
        except Exception:
            db.session.rollback()
            flash("Erreur suppression.", "danger")
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    etablissement_id = session['etablissement_id']
    budget = db.session.get(Budget, int(request.form.get('budget_id')))
    if budget and budget.etablissement_id == etablissement_id:
        try:
            budget.cloture = True
            db.session.commit()
            flash("Budget clôturé.", "success")
        except Exception:
            db.session.rollback()
            flash("Erreur clôture.", "danger")
    return redirect(url_for('admin.budget'))
    

@admin_bp.route("/budget/exporter", methods=['GET'])
@admin_required
def exporter_budget():
    """
    Route d'export du budget en PDF ou Excel
    """
    try:
        etablissement_id = session.get('etablissement_id')
        nom_etablissement = session.get('nom_etablissement', 'Mon Établissement')
        
        # 1. Récupération des paramètres
        date_debut_str = request.args.get('date_debut')
        date_fin_str = request.args.get('date_fin')
        format_type = request.args.get('format')
        
        if not all([date_debut_str, date_fin_str, format_type]):
            flash("Paramètres d'export manquants.", "error")
            return redirect(url_for('admin.budget'))
        
        # 2. Parsing des dates
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Format de date invalide.", "error")
            return redirect(url_for('admin.budget'))
        
        # 3. Requête Optimisée
        depenses = db.session.execute(
            db.select(Depense)
            .options(joinedload(Depense.fournisseur))
            .filter_by(etablissement_id=etablissement_id)
            .filter(Depense.date_depense >= date_debut)
            .filter(Depense.date_depense <= date_fin)
            .order_by(Depense.date_depense.asc())
        ).scalars().all()
        
        if not depenses:
            flash("Aucune dépense trouvée pour cette période.", "warning")
            return redirect(url_for('admin.budget'))
        
        # 4. Préparation des données
        data_export = []
        total = 0.0
        for d in depenses:
            nom_fournisseur = "Petit matériel (Bon d'achat)" if d.est_bon_achat else (d.fournisseur.nom if d.fournisseur else "Inconnu")
            data_export.append({
                'date': d.date_depense.strftime('%d/%m/%Y'),
                'fournisseur': nom_fournisseur,
                'contenu': d.contenu or "-",
                'montant': d.montant
            })
            total += d.montant
        
        # 5. Métadonnées
        metadata = {
            'etablissement': nom_etablissement,
            'date_debut': date_debut.strftime('%d/%m/%Y'),
            'date_fin': date_fin.strftime('%d/%m/%Y'),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'nombre_depenses': len(data_export),
            'total': total
        }
        
        # 6. Génération
        if format_type == 'excel':
            return generer_budget_excel_pro(data_export, metadata)
        else:
            return generer_budget_pdf_pro(data_export, metadata)
    
    except Exception as e:
        # AFFICHE L'ERREUR RÉELLE DANS LE FLASH MESSAGE
        import traceback
        traceback.print_exc() # Affiche l'erreur dans la console noire
        flash(f"ERREUR TECHNIQUE : {str(e)}", "danger") # Affiche l'erreur sur le site
        return redirect(url_for('admin.budget'))

# ============================================================
# GÉNÉRATEUR PDF (ReportLab - Style LabFlow)
# ============================================================
# Assure-toi d'ajouter cet import tout en haut du fichier views/admin.py
from html import escape

def generer_budget_pdf_pro(data_export, metadata):
    buffer = BytesIO()
    
    # Configuration du document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        title=f"Budget {metadata['etablissement']}"
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Couleurs
    LABFLOW_BLUE = colors.HexColor('#1F3B73')
    
    # Styles de paragraphes
    style_titre = ParagraphStyle(
        'LabFlowTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=LABFLOW_BLUE,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    style_sous_titre = ParagraphStyle(
        'LabFlowSubTitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#6c757d'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    style_cellule = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.black,
        alignment=TA_LEFT
    )
    
    style_cellule_centre = ParagraphStyle('CellCenter', parent=style_cellule, alignment=TA_CENTER)
    style_cellule_droite = ParagraphStyle('CellRight', parent=style_cellule, alignment=TA_RIGHT)
    
    # --- Construction du contenu ---

    # 1. En-tête
    elements.append(Paragraph(metadata['etablissement'], style_titre))
    elements.append(Paragraph(
        f"Rapport de Dépenses : {metadata['date_debut']} au {metadata['date_fin']}", 
        style_sous_titre
    ))
    elements.append(Spacer(1, 0.5*cm))
    
    # 2. Préparation des données du tableau
    table_data = [['Date', 'Fournisseur', 'Libellé', 'Montant']]
    
    for item in data_export:
        date_para = Paragraph(item['date'], style_cellule_centre)
        # Sécurité : escape() empêche le crash si le texte contient <, >, &
        fournisseur_para = Paragraph(escape(item['fournisseur']), style_cellule)
        libelle_para = Paragraph(escape(item['contenu'] or "Non spécifié"), style_cellule)
        montant_para = Paragraph(f"{item['montant']:.2f} €", style_cellule_droite)
        
        table_data.append([date_para, fournisseur_para, libelle_para, montant_para])
    
    # Ligne vide de séparation (Esthétique)
    table_data.append(['', '', '', ''])
    
    # Ligne Total
    table_data.append([
        '', 
        '', 
        Paragraph('<b>TOTAL</b>', style_cellule_droite), 
        Paragraph(f"<b>{metadata['total']:.2f} €</b>", style_cellule_droite)
    ])
    
    # 3. Création et Style du Tableau
    col_widths = [2.5*cm, 6*cm, 7*cm, 2.5*cm]
    t = Table(table_data, colWidths=col_widths)
    
    t.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), LABFLOW_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Alignement vertical global
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Grille (sauf sur la ligne vide et le total)
        # -3 correspond à la dernière ligne de données avant la ligne vide
        ('GRID', (0, 0), (-1, -3), 0.5, colors.HexColor('#dee2e6')),
        
        # Zebra (lignes alternées) sur les données uniquement
        ('ROWBACKGROUNDS', (0, 1), (-1, -3), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Footer Total (Dernière ligne)
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, LABFLOW_BLUE), # Ligne épaisse au-dessus du total
        ('GRID', (2, -1), (-1, -1), 0.5, colors.HexColor('#dee2e6')), # Grille juste pour les cases total
    ]))
    
    elements.append(t)
    
    # 4. Footer du document
    elements.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer', 
        parent=styles['Normal'], 
        fontSize=8, 
        textColor=colors.grey, 
        alignment=TA_CENTER
    )
    elements.append(Paragraph(
        f"Généré par LabFlow le {metadata['date_generation']} | "
        f"{metadata['nombre_depenses']} dépense(s)", 
        footer_style
    ))
    
    # Génération
    doc.build(elements)
    
    buffer.seek(0)
    
    # Nom de fichier sécurisé (remplacement des espaces)
    safe_etablissement = metadata['etablissement'].replace(' ', '_')
    safe_debut = metadata['date_debut'].replace('/', '-')
    safe_fin = metadata['date_fin'].replace('/', '-')
    filename = f"Budget_{safe_etablissement}_{safe_debut}_au_{safe_fin}.pdf"
    
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

# ============================================================
# GÉNÉRATEUR EXCEL (OpenPyXL - Style LabFlow)
# ============================================================
def generer_budget_excel_pro(data_export, metadata):
    import re
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Budget"
    
    # Couleurs LabFlow
    COLOR_PRIMARY = "1F3B73"
    COLOR_LIGHT = "F8F9FA"
    COLOR_BORDER = "DEE2E6"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color=COLOR_PRIMARY, end_color=COLOR_PRIMARY, fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    
    border_style = Border(
        left=Side(style='thin', color=COLOR_BORDER),
        right=Side(style='thin', color=COLOR_BORDER),
        top=Side(style='thin', color=COLOR_BORDER),
        bottom=Side(style='thin', color=COLOR_BORDER)
    )
    
    # Titre
    ws.merge_cells('A1:D1')
    ws['A1'] = f"Budget : {metadata['etablissement']}"
    ws['A1'].font = Font(bold=True, size=14, color=COLOR_PRIMARY)
    ws['A1'].alignment = center_align
    
    ws.merge_cells('A2:D2')
    ws['A2'] = f"Période : {metadata['date_debut']} au {metadata['date_fin']}"
    ws['A2'].font = Font(italic=True, size=10)
    ws['A2'].alignment = center_align
    
    # En-têtes Colonnes (Ligne 4)
    headers = ['Date', 'Fournisseur', 'Libellé', 'Montant']
    for col, text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border_style
    
    # Données
    row_idx = 5
    for item in data_export:
        ws.cell(row=row_idx, column=1, value=item['date']).alignment = center_align
        ws.cell(row=row_idx, column=2, value=item['fournisseur'])
        ws.cell(row=row_idx, column=3, value=item['contenu'])
        
        # ⚠️ CORRECTION ICI : Conversion explicite en float
        montant_cell = ws.cell(row=row_idx, column=4, value=float(item['montant']))
        montant_cell.number_format = '#,##0.00 €'
        montant_cell.alignment = right_align  # Alignement à droite pour les montants
        
        # Bordures
        for col in range(1, 5):
            ws.cell(row=row_idx, column=col).border = border_style
        
        # Zebra striping (lignes alternées)
        if row_idx % 2 == 0:
            for col in range(1, 5):
                current_fill = ws.cell(row=row_idx, column=col).fill
                if current_fill.fill_type is None or current_fill.start_color.rgb != COLOR_PRIMARY:
                    ws.cell(row=row_idx, column=col).fill = PatternFill(
                        start_color=COLOR_LIGHT, end_color=COLOR_LIGHT, fill_type="solid"
                    )
        
        row_idx += 1
    
    # Total
    ws.cell(row=row_idx, column=3, value="TOTAL").font = Font(bold=True)
    ws.cell(row=row_idx, column=3).alignment = right_align
    ws.cell(row=row_idx, column=3).border = border_style
    
    # ⚠️ CORRECTION ICI : Conversion explicite en float
    total_cell = ws.cell(row=row_idx, column=4, value=float(metadata['total']))
    total_cell.font = Font(bold=True, color=COLOR_PRIMARY)
    total_cell.number_format = '#,##0.00 €'
    total_cell.alignment = right_align
    total_cell.fill = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")
    total_cell.border = border_style
    
    # Bordures pour les cellules vides de la ligne total
    for col in [1, 2]:
        cell = ws.cell(row=row_idx, column=col)
        cell.border = border_style
        cell.fill = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")
    
    # Footer
    row_idx += 2
    ws.merge_cells(f'A{row_idx}:D{row_idx}')
    footer_cell = ws.cell(row=row_idx, column=1)
    footer_cell.value = f"Généré par LabFlow le {metadata['date_generation']} | {metadata['nombre_depenses']} dépense(s)"
    footer_cell.font = Font(size=8, color="6C757D", italic=True)
    footer_cell.alignment = center_align
    
    # Largeurs
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 50
    ws.column_dimensions['D'].width = 15
    
    # Filtres automatiques sur les en-têtes
    ws.auto_filter.ref = f"A4:D{row_idx - 3}"
    
    # Figer les lignes d'en-tête
    ws.freeze_panes = "A5"
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    safe_etablissement = re.sub(r'[<>:"/\\|?*]', '_', str(metadata['etablissement']))
    safe_debut = str(metadata['date_debut']).replace('/', '-')
    safe_fin = str(metadata['date_fin']).replace('/', '-')
    
    filename = f"Budget_{safe_etablissement}_{safe_debut}_au_{safe_fin}.xlsx"
    
    return send_file(
        buffer, 
        as_attachment=True, 
        download_name=filename, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ============================================================
# GESTION FOURNISSEURS
# ============================================================
@admin_bp.route("/fournisseurs", methods=['GET'])
@admin_required
def gestion_fournisseurs():
    etablissement_id = session['etablissement_id']
    fournisseurs = db.session.execute(
        db.select(Fournisseur, func.count(Depense.id).label('depenses_count'))
        .outerjoin(Depense, Fournisseur.id == Depense.fournisseur_id)
        .filter(Fournisseur.etablissement_id == etablissement_id)
        .group_by(Fournisseur.id)
        .order_by(Fournisseur.nom)
    ).all()
    
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Fournisseurs'}]
    
    return render_template("admin_fournisseurs.html", 
                           fournisseurs=fournisseurs, 
                           breadcrumbs=breadcrumbs)

@admin_bp.route("/fournisseurs/ajouter", methods=['POST'])
@admin_required
def ajouter_fournisseur():
    etablissement_id = session['etablissement_id']
    
    # Récupération des données
    nom = request.form.get('nom', '').strip()
    site_web = request.form.get('site_web', '').strip()
    logo_url = request.form.get('logo_url', '').strip()

    if not nom:
        flash("Le nom du fournisseur est obligatoire.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    try:
        nouveau = Fournisseur(
            nom=nom,
            site_web=site_web or None,
            logo=logo_url or None,
            etablissement_id=etablissement_id
        )
        db.session.add(nouveau)
        db.session.commit()
        flash("Fournisseur ajouté avec succès.", "success")
        
    except IntegrityError:
        db.session.rollback()
        flash("Un fournisseur portant ce nom existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur technique : {e}", "danger")
        
    return redirect(url_for('admin.gestion_fournisseurs'))

@admin_bp.route("/fournisseurs/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    
    if not fournisseur or fournisseur.etablissement_id != etablissement_id:
        flash("Fournisseur introuvable.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    try:
        fournisseur.nom = request.form.get('nom')
        fournisseur.site_web = request.form.get('site_web')
        fournisseur.logo = request.form.get('logo_url')
        db.session.commit()
        flash("Fournisseur modifié.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Ce nom existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur: {e}", "danger")
        
    return redirect(url_for('admin.gestion_fournisseurs'))

@admin_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    if fournisseur and fournisseur.etablissement_id == etablissement_id:
        if fournisseur.depenses:
            flash("Impossible de supprimer : fournisseur lié à des dépenses.", "danger")
        else:
            try:
                db.session.delete(fournisseur)
                db.session.commit()
                flash("Fournisseur supprimé.", "success")
            except Exception:
                db.session.rollback()
                flash("Erreur suppression.", "danger")
    return redirect(url_for('admin.gestion_fournisseurs'))

# ============================================================
# IMPORT / EXPORT
# ============================================================
@admin_bp.route("/importer", methods=['GET'])
@admin_required
def importer_page():
    etablissement_id = session['etablissement_id']
    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()
    
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Importation'}]
    return render_template("admin_import.html", breadcrumbs=breadcrumbs, armoires=armoires, categories=categories, now=datetime.now())

@admin_bp.route("/telecharger_modele")
@admin_required
def telecharger_modele_excel():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des données existantes
    armoires = db.session.execute(
        db.select(Armoire.nom).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)
    ).scalars().all()
    
    categories = db.session.execute(
        db.select(Categorie.nom).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)
    ).scalars().all()

    # 2. Création du classeur
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventaire à Importer"

    # 3. En-têtes
    headers = ["Nom", "Quantité", "Seuil", "Armoire", "Catégorie", "Date Péremption", "Image (URL)"]
    ws.append(headers)

    # Style Header
    header_font = Font(name='Calibri', bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")
    center_alignment = Alignment(horizontal='center', vertical='center')

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment

    # Largeurs
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 30
    ws.column_dimensions['E'].width = 30
    ws.column_dimensions['F'].width = 20
    ws.column_dimensions['G'].width = 50

    # --- 4. CRÉATION DES LISTES DÉROULANTES ---
    
    # On crée une feuille cachée pour stocker les données de référence
    ws_data = wb.create_sheet("Data_Listes")
    ws_data.sheet_state = 'hidden' # On la cache pour ne pas gêner l'utilisateur

    # On remplit la feuille cachée
    # Colonne A : Armoires
    for i, nom in enumerate(armoires, start=1):
        ws_data.cell(row=i, column=1, value=nom)
    
    # Colonne B : Catégories
    for i, nom in enumerate(categories, start=1):
        ws_data.cell(row=i, column=2, value=nom)

    # --- 5. APPLICATION DE LA VALIDATION ---
    
    # Validation Armoires (Colonne D)
    # Si on a des armoires, on crée la règle
    if armoires:
        # Formule : ='Data_Listes'!$A$1:$A$X
        formula_armoires = f"'Data_Listes'!$A$1:$A${len(armoires)}"
        dv_armoires = DataValidation(type="list", formula1=formula_armoires, allow_blank=True)
        dv_armoires.error = 'Veuillez sélectionner une armoire dans la liste.'
        dv_armoires.errorTitle = 'Armoire inconnue'
        dv_armoires.prompt = 'Sélectionnez une armoire existante'
        dv_armoires.promptTitle = 'Choix Armoire'
        
        # On applique la validation sur la colonne D (lignes 2 à 1000)
        ws.add_data_validation(dv_armoires)
        dv_armoires.add('D2:D1000')

    # Validation Catégories (Colonne E)
    if categories:
        # Formule : ='Data_Listes'!$B$1:$B$X
        formula_categories = f"'Data_Listes'!$B$1:$B${len(categories)}"
        dv_categories = DataValidation(type="list", formula1=formula_categories, allow_blank=True)
        dv_categories.error = 'Veuillez sélectionner une catégorie dans la liste.'
        dv_categories.errorTitle = 'Catégorie inconnue'
        
        # On applique la validation sur la colonne E (lignes 2 à 1000)
        ws.add_data_validation(dv_categories)
        dv_categories.add('E2:E1000')

    # Ajout d'un commentaire d'aide sur la date
    date_cell = ws['F1']
    date_cell.comment = Comment("Format attendu : AAAA-MM-JJ (ex: 2025-12-31)", "LabFlow")

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='modele_import_inventaire_dynamique.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin_bp.route("/importer", methods=['POST'])
@admin_required
def importer_fichier():
    etablissement_id = session['etablissement_id']
    if 'fichier_excel' not in request.files:
        flash("Fichier manquant.", "error")
        return redirect(url_for('admin.importer_page'))

    fichier = request.files['fichier_excel']
    if not fichier.filename.endswith('.xlsx'):
        flash("Format invalide (xlsx requis).", "error")
        return redirect(url_for('admin.importer_page'))

    errors = []
    success_count = 0
    skipped_items = []

    # Chargement des données de référence
    existing_objets = {o.nom.lower() for o in db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars().all()}
    armoires_map = {a.nom.lower(): a.id for a in db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()}
    categories_map = {c.nom.lower(): c.id for c in db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()}

    try:
        workbook = load_workbook(fichier)
        sheet = workbook.active
        
        for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(cell is None for cell in row): continue
            
            # Validation structure
            if len(row) < 5:
                errors.append(f"Ligne {i}: Colonnes manquantes.")
                continue

            nom, quantite, seuil, armoire_nom, categorie_nom = row[0], row[1], row[2], row[3], row[4]
            
            if not all([nom, quantite is not None, seuil is not None, armoire_nom, categorie_nom]):
                errors.append(f"Ligne {i}: Données obligatoires manquantes.")
                continue

            # Gestion Doublons
            if str(nom).lower() in existing_objets:
                skipped_items.append(str(nom))
                continue

            # Validation FK
            armoire_id = armoires_map.get(str(armoire_nom).lower())
            categorie_id = categories_map.get(str(categorie_nom).lower())

            if not armoire_id:
                errors.append(f"Ligne {i}: Armoire '{armoire_nom}' inconnue.")
                continue
            if not categorie_id:
                errors.append(f"Ligne {i}: Catégorie '{categorie_nom}' inconnue.")
                continue

            # Création
            nouvel_objet = Objet(
                nom=str(nom),
                quantite_physique=int(quantite),
                seuil=int(seuil),
                armoire_id=armoire_id,
                categorie_id=categorie_id,
                etablissement_id=etablissement_id
            )
            db.session.add(nouvel_objet)
            success_count += 1

        if errors:
            db.session.rollback()
            for e in errors[:5]: flash(e, "error")
            if len(errors) > 5: flash(f"+ {len(errors)-5} autres erreurs.", "error")
        else:
            db.session.commit()
            if success_count > 0: flash(f"{success_count} objets importés.", "success")
            if skipped_items: flash(f"{len(skipped_items)} doublons ignorés : {', '.join(skipped_items[:3])}...", "warning")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur critique : {e}", "error")

    return redirect(url_for('admin.importer_page'))

@admin_bp.route("/exporter_inventaire")
@admin_required
def exporter_inventaire():
    etablissement_id = session['etablissement_id']
    format_type = request.args.get('format')
    
    # Protection DoS : Limite de taille
    objets = db.session.execute(
        db.select(Objet)
        .options(joinedload(Objet.categorie), joinedload(Objet.armoire))
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Objet.nom)
        .limit(MAX_EXPORT_LIMIT)
    ).scalars().all()
    
    if len(objets) == MAX_EXPORT_LIMIT:
        flash(f"Export tronqué à {MAX_EXPORT_LIMIT} lignes pour la performance.", "warning")

    if format_type == 'excel':
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Inventaire"
        sheet.append(["Catégorie", "Nom", "Quantité", "Seuil", "Armoire"])
        
        for obj in objets:
            sheet.append([
                obj.categorie.nom if obj.categorie else "",
                obj.nom,
                obj.quantite_physique,
                obj.seuil,
                obj.armoire.nom if obj.armoire else ""
            ])
            
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='inventaire.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    flash("Format non supporté.", "error")
    return redirect(url_for('admin.admin'))

# ============================================================
# PLACEHOLDERS
# ============================================================
@admin_bp.route("/rapports")
@admin_required
def rapports():
    flash("Fonctionnalité en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/activer_licence", methods=["POST"])
@admin_required
def activer_licence():
    flash("Géré par la plateforme SaaS.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    flash("Sauvegarde gérée par la plateforme SaaS.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    flash("Import désactivé en SaaS.", "info")
    return redirect(url_for('admin.admin'))