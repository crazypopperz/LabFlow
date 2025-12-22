# ============================================================
# IMPORTS SÉCURISÉS
# ============================================================
import json
import hashlib
import shutil
import secrets
import re
import logging
from extensions import limiter, cache
from collections import defaultdict
from functools import wraps
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse
from html import escape

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_file, current_app, abort)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Modèles et DB
from db import db, Utilisateur, Parametre, Objet, Armoire, Categorie, Fournisseur, Kit, KitObjet, Budget, Depense, Echeance, Etablissement, Historique, Reservation, Suggestion
# AJOUT DE allowed_file DANS LES IMPORTS
from utils import calculate_license_key, admin_required, login_required, log_action, get_etablissement_params, allowed_file


# ============================================================
# CONFIGURATION & SÉCURITÉ
# ============================================================
admin_bp = Blueprint('admin', __name__, template_folder='../templates', url_prefix='/admin')

MAX_EXPORT_LIMIT = 3000
MAX_FILE_SIZE = 10 * 1024 * 1024 # <--- AJOUTÉ (10 Mo max)
PASSWORD_MIN_LENGTH = 12         # <--- AJOUTÉ
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# ============================================================
# UTILITAIRES DE SÉCURITÉ (NOUVEAUX)
# ============================================================
def hash_user_id(user_id):
    """Anonymise l'ID utilisateur pour les logs."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]

def validate_email(email):
    """Valide le format de l'email."""
    return re.match(EMAIL_REGEX, email) is not None

def validate_password_strength(password):
    """Valide la complexité du mot de passe."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères."
    if not re.search(r"[a-z]", password): return False, "Doit contenir une minuscule."
    if not re.search(r"[A-Z]", password): return False, "Doit contenir une majuscule."
    if not re.search(r"[0-9]", password): return False, "Doit contenir un chiffre."
    if not re.search(r"[^a-zA-Z0-9]", password): return False, "Doit contenir un caractère spécial."
    return True, ""

def validate_url(url):
    """Vérifie si une URL est valide (http/https)."""
    if not url:
        return True
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

def sanitize_for_excel(value):
    """
    Protège contre l'injection de formules Excel (CSV Injection).
    Si une valeur commence par =, +, - ou @, on ajoute une apostrophe
    pour forcer Excel à la traiter comme du texte.
    """
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return f"'{value}"
    return value

def generer_code_unique():
    """Génère un code unique via un test d'insertion atomique (Flush/Rollback)."""
    for _ in range(10):
        code = f"LABFLOW-{secrets.token_hex(3).upper()}"
        nested = db.session.begin_nested()
        try:
            # On crée un objet temporaire juste pour tester la contrainte UNIQUE de la base
            # Le nom "__TEST__" n'a pas d'importance car on rollback juste après
            test_etab = Etablissement(nom="__TEST_UNIQUENESS__", code_invitation=code)
            
            db.session.add(test_etab)
            db.session.flush()    # Envoie à la DB : Si doublon, ça plante ici (IntegrityError)
            nested.rollback()
            return code
            
        except IntegrityError:
            nested.rollback()
            continue # On retente avec un nouveau code

    # Si on arrive ici, c'est qu'on a vraiment pas de chance (ou plus de codes dispos)
    raise RuntimeError("Impossible de générer un code d'invitation unique après 10 tentatives")

def json_serial(obj):
    """Helper pour sérialiser les dates en JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} non sérialisable")

def sanitize_filename(name):
    safe = re.sub(r'[^\w\s-]', '', str(name))
    
    cleaned = secure_filename(safe)
    
    if not cleaned:
        cleaned = "Export"
        
    return cleaned[:100]
    

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
        # Log sécurisé
        admin_hash = hash_user_id(session.get('user_id'))
        current_app.logger.critical(f"Admin access attempt invalid etab by admin_{admin_hash}")
        flash("Erreur critique : Établissement introuvable.", "error")
        return redirect(url_for('auth.login'))

    # 2. AUTO-RÉPARATION sécurisée du code invitation
    if not etablissement.code_invitation:
        try:
            etablissement.code_invitation = generer_code_unique()
            db.session.commit()
            current_app.logger.info(f"Code invitation généré pour Etab_{etablissement_id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur génération code invitation: {e}")

    # 3. Récupération des infos de licence
    params = db.session.execute(
        db.select(Parametre).filter_by(etablissement_id=etablissement_id)
    ).scalars().all()
    
    params_dict = {p.cle: p.valeur for p in params}
    
    licence_info = {
        'is_pro': params_dict.get('licence_statut') == 'PRO',
        'instance_id': params_dict.get('instance_id', 'N/A'),
        'statut': params_dict.get('licence_statut', 'FREE')
    }

    # On ne passe plus 'suggestions' ici
    return render_template(
        "admin.html", 
        now=datetime.now(), 
        licence=licence_info,
        etablissement=etablissement
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
        current_app.logger.error(f"Erreur ajout {type_objet}: {e}") # AJOUTÉ : Log
        flash(f"Erreur technique.", "error")
    
    redirect_to = "main.gestion_armoires" if type_objet == "armoire" else "main.gestion_categories"
    return redirect(url_for(redirect_to))

@admin_bp.route("/supprimer/<type_objet>/<int:id>", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def supprimer(type_objet, id):
    etablissement_id = session['etablissement_id']
    
    if type_objet == "armoire":
        Model = Armoire
        redirect_to = "main.gestion_armoires"
    elif type_objet == "categorie":
        Model = Categorie
        redirect_to = "main.gestion_categories"
    else:
        abort(400) # Bad Request si le type est inconnu

    element = db.session.get(Model, id)

    # SÉCURITÉ IDOR : Si l'élément n'existe pas ou n'appartient pas à l'établissement
    if not element or element.etablissement_id != etablissement_id:
        # On loggue la tentative suspecte
        current_app.logger.warning(f"IDOR SUSPECT: User {session.get('user_id')} a tenté de supprimer {type_objet} {id} sans droits.")
        abort(403) # Forbidden

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
        current_app.logger.error(f"Erreur suppression {type_objet}: {e}")
        flash("Erreur technique lors de la suppression.", "error")
    
    return redirect(url_for(redirect_to))

# --- ENDPOINTS JSON SÉCURISÉS ---
@admin_bp.route("/modifier_armoire", methods=["POST"])
@admin_required
def modifier_armoire():
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
# GESTION UTILISATEURS (SÉCURISÉE)
# ============================================================
@admin_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    etablissement_id = session['etablissement_id']
    utilisateurs = db.session.execute(
        db.select(Utilisateur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Utilisateur.nom_utilisateur)
        .limit(100) # AJOUTÉ : Limite anti-DoS
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Utilisateurs'}
    ]
    
    return render_template("admin_utilisateurs.html", utilisateurs=utilisateurs, breadcrumbs=breadcrumbs, now=datetime.now)

@admin_bp.route("/utilisateurs/ajouter", methods=["POST"])
@admin_required
@limiter.limit("10 per minute")
def ajouter_utilisateur():
    etablissement_id = session['etablissement_id']
    nom_utilisateur = request.form.get('nom_utilisateur', '').strip()
    email = request.form.get('email', '').strip()
    mot_de_passe = request.form.get('mot_de_passe', '').strip()
    est_admin = 'est_admin' in request.form

    if not nom_utilisateur or not mot_de_passe:
        flash("Champs obligatoires manquants.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    # AJOUTÉ : Validation Email
    if email and not validate_email(email):
        flash("Format d'email invalide.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))

    # AJOUTÉ : Validation MDP
    is_valid, error_msg = validate_password_strength(mot_de_passe)
    if not is_valid:
        flash(error_msg, "danger")
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
        log_action('create_user', f"Nouvel utilisateur : {nom_utilisateur}")
        
        # AJOUTÉ : Log anonymisé
        admin_hash = hash_user_id(session['user_id'])
        current_app.logger.info(f"Utilisateur créé par admin_{admin_hash}")
        
        flash(f"Utilisateur '{nom_utilisateur}' créé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"L'utilisateur '{nom_utilisateur}' existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur création user: {e}")
        flash("Erreur technique.", "danger")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    etablissement_id = session['etablissement_id']
    email = request.form.get('email', '').strip()
    
    # AJOUTÉ : Validation Email
    if email and not validate_email(email):
        flash("Format d'email invalide.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

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
        current_app.logger.error(f"Erreur modif email: {e}")
        flash("Erreur technique.", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
def reinitialiser_mdp(id_user):
    etablissement_id = session['etablissement_id']
    
    if id_user == session['user_id']:
        flash("Action impossible sur soi-même.", "warning")
        return redirect(url_for('admin.gestion_utilisateurs'))

    nouveau_mdp = request.form.get('nouveau_mot_de_passe')
    
    # AJOUTÉ : Validation MDP
    is_valid, error_msg = validate_password_strength(nouveau_mdp)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur introuvable.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.mot_de_passe = generate_password_hash(nouveau_mdp, method='scrypt')
        db.session.commit()
        flash(f"Mot de passe réinitialisé pour {user.nom_utilisateur}.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur reset MDP: {e}")
        flash("Erreur technique.", "error")

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
            user.role = "desactive"
            db.session.commit()
            flash("Utilisateur anonymisé et désactivé (car il possède un historique).", "warning")
        else:
            db.session.delete(user)
            db.session.commit()
            flash("Utilisateur supprimé définitivement.", "success")
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression user: {e}")
        flash("Erreur technique.", "error")
        
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
        current_app.logger.error(f"Erreur promotion: {e}")
        flash("Erreur technique.", "danger")
        return redirect(url_for('admin.gestion_utilisateurs'))


# ============================================================
# GESTION KITS (SÉCURISÉE)
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
@limiter.limit("10 per minute")
def ajouter_kit():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()

    if not nom:
        flash("Le nom du kit est requis.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    try:
        nouveau_kit = Kit(
            nom=nom, 
            description=description, 
            etablissement_id=etablissement_id
        )
        db.session.add(nouveau_kit)
        db.session.commit()
        flash(f"Kit '{nom}' créé avec succès.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=nouveau_kit.id))
        
    except IntegrityError:
        db.session.rollback()
        flash("Un kit portant ce nom existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout kit: {e}")
        flash("Erreur technique lors de la création.", "danger")
        
    return redirect(url_for('admin.gestion_kits'))

@admin_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if not kit or kit.etablissement_id != etablissement_id:
        flash("Kit introuvable ou accès refusé.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    if request.method == "POST":
        try:
            objet_id_str = request.form.get("objet_id")
            
            # CAS 1 : AJOUT D'UN OBJET AU KIT
            if objet_id_str:
                objet_id = int(objet_id_str)
                quantite = int(request.form.get("quantite", 1))
                
                # Validation Métier : Quantité positive
                if quantite <= 0:
                    raise ValueError("La quantité doit être supérieure à 0.")

                objet = db.session.get(Objet, objet_id)
                if not objet or objet.etablissement_id != etablissement_id:
                    raise ValueError("Objet invalide ou introuvable.")
                
                # Vérifier si l'objet est déjà dans le kit
                assoc = db.session.execute(
                    db.select(KitObjet).filter_by(kit_id=kit.id, objet_id=objet_id)
                ).scalar_one_or_none()
                
                if assoc:
                    assoc.quantite += quantite # On cumule
                    flash(f"Quantité mise à jour pour '{objet.nom}'.", "success")
                else:
                    db.session.add(KitObjet(
                        kit_id=kit.id, 
                        objet_id=objet_id, 
                        quantite=quantite, 
                        etablissement_id=etablissement_id
                    ))
                    flash(f"Objet '{objet.nom}' ajouté au kit.", "success")
                
                db.session.commit()

            # CAS 2 : MISE À JOUR EN MASSE (Tableau existant)
            else:
                modifications_count = 0
                for key, value in request.form.items():
                    if key.startswith("quantite_"):
                        try:
                            k_id = int(key.split("_")[1])
                            val = int(value)
                            
                            assoc = db.session.get(KitObjet, k_id)
                            # Sécurité : on vérifie que l'association appartient bien au kit en cours
                            if assoc and assoc.kit_id == kit.id:
                                if val > 0:
                                    assoc.quantite = val
                                    modifications_count += 1
                                else:
                                    # Si 0 ou négatif, on supprime l'objet du kit
                                    db.session.delete(assoc)
                                    modifications_count += 1
                        except ValueError:
                            continue # On ignore les clés malformées
                
                if modifications_count > 0:
                    db.session.commit()
                    flash("Quantités mises à jour.", "success")
                else:
                    flash("Aucune modification détectée.", "info")

        except ValueError as ve:
            flash(f"Erreur de saisie : {ve}", "warning")
        except IntegrityError:
            db.session.rollback()
            flash("Erreur d'intégrité (doublon ou conflit).", "danger")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur modif kit {kit_id}: {e}")
            flash("Erreur technique lors de la mise à jour.", "danger")
            
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

    # --- GET : AFFICHAGE ---
    
    # 1. Objets DANS le kit
    objets_in_kit = db.session.execute(
        db.select(KitObjet)
        .filter_by(kit_id=kit.id)
        .options(joinedload(KitObjet.objet))
        .order_by(KitObjet.id)
    ).scalars().all()
    
    # Liste des IDs déjà présents pour l'exclusion
    ids_in_kit = [o.objet_id for o in objets_in_kit]
    
    # 2. Objets DISPONIBLES (Hors du kit)
    # SÉCURITÉ : Limite à 500 objets pour éviter le crash du navigateur si l'inventaire est énorme
    objets_disponibles = db.session.execute(
        db.select(Objet)
        .filter(Objet.etablissement_id == etablissement_id)
        .filter(~Objet.id.in_(ids_in_kit) if ids_in_kit else True) # Exclure si la liste n'est pas vide
        .order_by(Objet.nom)
        .limit(500) 
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Administration', 'url': url_for('admin.admin')}, 
        {'text': 'Kits', 'url': url_for('admin.gestion_kits')}, 
        {'text': kit.nom}
    ]
    
    return render_template(
        "admin_kit_modifier.html", 
        kit=kit, 
        breadcrumbs=breadcrumbs, 
        objets_in_kit=objets_in_kit, 
        objets_disponibles=objets_disponibles
    )

@admin_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=["POST"])
@admin_required
def retirer_objet_kit(kit_objet_id):
    etablissement_id = session['etablissement_id']
    assoc = db.session.get(KitObjet, kit_objet_id)
    
    if not assoc or assoc.etablissement_id != etablissement_id:
        flash("Objet introuvable ou accès refusé.", "danger")
        return redirect(url_for('admin.gestion_kits'))
        
    kit_id = assoc.kit_id
    try:
        db.session.delete(assoc)
        db.session.commit()
        flash("Objet retiré du kit.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur retrait objet kit: {e}")
        flash("Erreur technique lors du retrait.", "danger")
            
    return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

@admin_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if kit and kit.etablissement_id == etablissement_id:
        try:
            db.session.delete(kit)
            db.session.commit()
            flash("Kit supprimé avec succès.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur suppression kit {kit_id}: {e}")
            flash("Erreur technique lors de la suppression.", "danger")
    else:
        flash("Kit introuvable.", "danger")
        
    return redirect(url_for('admin.gestion_kits'))

# ============================================================
# GESTION ÉCHÉANCES (SÉCURISÉE)
# ============================================================
@admin_bp.route("/echeances", methods=['GET'])
@admin_required
def gestion_echeances():
    etablissement_id = session['etablissement_id']
    
    echeances = db.session.execute(
        db.select(Echeance)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Echeance.date_echeance.asc())
    ).scalars().all()

    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Échéances'}]
    return render_template("admin_echeances.html", echeances=echeances, breadcrumbs=breadcrumbs, date_actuelle=date.today())

@admin_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    etablissement_id = session['etablissement_id']
    
    intitule = request.form.get('intitule', '').strip()
    date_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()

    # Validation des entrées
    if not intitule:
        flash("L'intitulé est obligatoire.", "warning")
        return redirect(url_for('admin.gestion_echeances'))
    
    if not date_str:
        flash("La date d'échéance est obligatoire.", "warning")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        # Parsing sécurisé de la date
        try:
            date_echeance = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Format de date invalide (attendu: AAAA-MM-JJ).")

        nouvelle_echeance = Echeance(
            intitule=intitule,
            date_echeance=date_echeance,
            details=details or None,
            etablissement_id=etablissement_id,
            traite=0 # Par défaut non traité à la création
        )
        
        db.session.add(nouvelle_echeance)
        db.session.commit()
        flash("Échéance ajoutée avec succès.", "success")

    except ValueError as ve:
        flash(f"Erreur de saisie : {ve}", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout échéance: {e}")
        flash("Erreur technique lors de l'ajout.", "danger")

    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    etablissement_id = session['etablissement_id']
    
    # Récupération sécurisée
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable ou accès refusé.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    intitule = request.form.get('intitule', '').strip()
    date_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()
    # Gestion de la checkbox (si présente = '1' ou 'on', sinon absente)
    est_traite = 1 if 'traite' in request.form else 0

    if not intitule or not date_str:
        flash("L'intitulé et la date sont obligatoires.", "warning")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        try:
            date_echeance = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Format de date invalide.")

        echeance.intitule = intitule
        echeance.date_echeance = date_echeance
        echeance.details = details or None
        echeance.traite = est_traite
        
        db.session.commit()
        flash("Échéance modifiée avec succès.", "success")

    except ValueError as ve:
        flash(f"Erreur de saisie : {ve}", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modif échéance {id}: {e}")
        flash("Erreur technique lors de la modification.", "danger")

    return redirect(url_for('admin.gestion_echeances'))

@admin_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    etablissement_id = session['etablissement_id']
    
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        db.session.delete(echeance)
        db.session.commit()
        flash("Échéance supprimée.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression échéance {id}: {e}")
        flash("Erreur technique lors de la suppression.", "danger")

    return redirect(url_for('admin.gestion_echeances'))

# ============================================================
# GESTION BUDGET (SÉCURISÉE)
# ============================================================

@admin_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    etablissement_id = session['etablissement_id']
    now = datetime.now()
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

    # 3. Initialisation auto
    if not budget_affiche and not budgets_archives:
        try:
            budget_affiche = Budget(annee=annee_selectionnee, montant_initial=0.0, etablissement_id=etablissement_id)
            db.session.add(budget_affiche)
            db.session.commit()
            budgets_archives.insert(0, budget_affiche)
        except IntegrityError:
            db.session.rollback()

    # 4. Calculs des totaux & Chargement Optimisé
    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_affiche:
        # --- OPTIMISATION N+1 ---
        # On charge les dépenses ET le fournisseur associé en une seule requête
        # On trie directement en SQL (plus rapide que Python)
        depenses = db.session.execute(
            db.select(Depense)
            .filter_by(budget_id=budget_affiche.id)
            .options(joinedload(Depense.fournisseur))  # Eager loading
            .order_by(Depense.date_depense.desc())
        ).scalars().all()

        # On calcule le total sur la liste déjà chargée en mémoire
        total_depenses = sum(d.montant for d in depenses)
        solde = budget_affiche.montant_initial - total_depenses
        
        if date.today() >= date(budget_affiche.annee + 1, 6, 1):
            cloture_autorisee = True

    # 5. Définir le budget actif pour les modales
    budget_actuel_pour_modales = None
    
    if budget_affiche and not budget_affiche.cloture:
        budget_actuel_pour_modales = budget_affiche
    else:
        budget_actuel_pour_modales = db.session.execute(
            db.select(Budget).filter_by(etablissement_id=etablissement_id, cloture=False).order_by(Budget.annee.desc())
        ).scalars().first()

    annee_proposee_pour_creation = annee_scolaire_actuelle
    if budgets_archives and budgets_archives[0].annee >= annee_scolaire_actuelle:
        annee_proposee_pour_creation = budgets_archives[0].annee + 1

    fournisseurs = db.session.execute(
        db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)
    ).scalars().all()
    
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Budget'}]
    
    return render_template("budget.html", 
                           breadcrumbs=breadcrumbs, 
                           budget_affiche=budget_affiche,
                           budget_actuel_pour_modales=budget_actuel_pour_modales,
                           annee_proposee_pour_creation=annee_proposee_pour_creation,
                           depenses=depenses, 
                           total_depenses=total_depenses, 
                           solde=solde,
                           fournisseurs=fournisseurs, 
                           budgets_archives=budgets_archives,
                           annee_selectionnee=annee_selectionnee, 
                           cloture_autorisee=cloture_autorisee, 
                           now=now)

@admin_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    etablissement_id = session['etablissement_id']
    try:
        montant_str = request.form.get('montant_initial', '0').replace(',', '.')
        annee_str = request.form.get('annee')
        
        if not annee_str:
            raise ValueError("L'année est requise.")

        montant = float(montant_str)
        annee = int(annee_str)
        
        if montant < 0:
            raise ValueError("Le montant ne peut pas être négatif.")
        
        # Recherche si le budget existe déjà pour cette année
        budget = db.session.execute(
            db.select(Budget).filter_by(annee=annee, etablissement_id=etablissement_id)
        ).scalar_one_or_none()
        
        if budget:
            budget.montant_initial = montant
            budget.cloture = False # On peut rouvrir un budget en le redéfinissant
            flash(f"Budget {annee}-{annee+1} mis à jour.", "success")
        else:
            db.session.add(Budget(annee=annee, montant_initial=montant, etablissement_id=etablissement_id))
            flash(f"Budget {annee}-{annee+1} créé.", "success")
        
        db.session.commit()
        
    except ValueError as ve:
        flash(f"Erreur de saisie : {ve}", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur définition budget: {e}")
        flash("Erreur technique.", "danger")
        
    return redirect(url_for('admin.budget', annee=annee if 'annee' in locals() else None))

@admin_bp.route("/budget/depense/ajouter", methods=['POST'])
@admin_required
def ajouter_depense():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération sécurisée des données brutes
    budget_id_raw = request.form.get('budget_id')
    fournisseur_id_raw = request.form.get('fournisseur_id')
    est_bon_achat = 'est_bon_achat' in request.form
    date_str = request.form.get('date_depense')
    montant_str = request.form.get('montant')
    contenu = request.form.get('contenu', '').strip()
    
    try:
        # 2. Vérification du Budget
        if not budget_id_raw:
            raise ValueError("Aucun budget actif sélectionné.")
            
        budget = db.session.get(Budget, int(budget_id_raw))
        if not budget or budget.etablissement_id != etablissement_id:
            raise ValueError("Budget invalide ou introuvable.")
        
        if budget.cloture:
            raise ValueError("Ce budget est clôturé, impossible d'ajouter une dépense.")

        # 3. Gestion du Fournisseur
        fournisseur_id = None
        if not est_bon_achat:
            if not fournisseur_id_raw:
                raise ValueError("Veuillez sélectionner un fournisseur.")
            fournisseur_id = int(fournisseur_id_raw)

        # 4. Validation Montant et Date
        if not montant_str: raise ValueError("Montant requis.")
        montant = float(montant_str.replace(',', '.'))
        
        if not date_str: raise ValueError("Date requise.")
        date_depense = datetime.strptime(date_str, '%Y-%m-%d').date()

        # 5. Création
        nouvelle = Depense(
            date_depense=date_depense,
            contenu=contenu,
            montant=montant,
            est_bon_achat=est_bon_achat,
            fournisseur_id=fournisseur_id,
            budget_id=budget.id,
            etablissement_id=etablissement_id
        )
        
        db.session.add(nouvelle)
        db.session.commit()
        flash("Dépense ajoutée avec succès.", "success")
        
    except ValueError as ve:
        flash(f"Erreur de saisie : {ve}", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout dépense: {e}")
        flash("Erreur technique.", "danger")
        
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/depense/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    etablissement_id = session['etablissement_id']
    depense = db.session.get(Depense, id)
    
    if depense and depense.etablissement_id == etablissement_id:
        # Vérifier si le budget est clôturé avant de supprimer ? 
        # Généralement oui, mais on laisse la souplesse à l'admin ici.
        try:
            db.session.delete(depense)
            db.session.commit()
            flash("Dépense supprimée.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erreur suppression dépense {id}: {e}")
            flash("Erreur technique.", "danger")
    else:
        flash("Dépense introuvable.", "danger")
        
    return redirect(url_for('admin.budget'))

@admin_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    etablissement_id = session['etablissement_id']
    try:
        budget_id = int(request.form.get('budget_id'))
        budget = db.session.get(Budget, budget_id)
        
        if budget and budget.etablissement_id == etablissement_id:
            budget.cloture = True
            db.session.commit()
            flash(f"Le budget {budget.annee}-{budget.annee+1} est maintenant clôturé.", "success")
        else:
            flash("Budget introuvable.", "danger")
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur clôture budget: {e}")
        flash("Erreur technique.", "danger")
        
    return redirect(url_for('admin.budget'))


@admin_bp.route("/budget/exporter", methods=['GET'])
@admin_required
def exporter_budget():
    """
    Export du budget filtré par date en Excel ou PDF.
    """
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des paramètres
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')
    format_type = request.args.get('format')
    
    if not all([date_debut_str, date_fin_str, format_type]):
        flash("Paramètres d'export manquants.", "error")
        return redirect(url_for('admin.budget'))
    
    try:
        # 2. Parsing des dates
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
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
            'etablissement': session.get('nom_etablissement', 'Mon Établissement'),
            'date_debut': date_debut.strftime('%d/%m/%Y'),
            'date_fin': date_fin.strftime('%d/%m/%Y'),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'nombre_depenses': len(data_export),
            'total': total
        }

        log_action('export_budget', f"Format: {format_type}, Période: {date_debut_str} au {date_fin_str}")
        
        # 6. Génération
        if format_type == 'excel':
            return generer_budget_excel_pro(data_export, metadata)
        else:
            return generer_budget_pdf_pro(data_export, metadata)
    
    except Exception as e:
        current_app.logger.error(f"Erreur export budget: {e}")
        flash("Une erreur est survenue lors de l'export.", "error")
        return redirect(url_for('admin.budget'))



# ============================================================
# GESTION FOURNISSEURS (SÉCURISÉE)
# ============================================================

@admin_bp.route("/fournisseurs", methods=['GET'])
@admin_required
def gestion_fournisseurs():
    etablissement_id = session['etablissement_id']
    
    # Requête optimisée : Récupère le fournisseur ET le nombre de dépenses liées
    # Cela permet de désactiver le bouton supprimer si des dépenses existent
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
    
    nom = request.form.get('nom', '').strip()
    site_web = request.form.get('site_web', '').strip()
    logo_url = request.form.get('logo_url', '').strip()

    if not nom:
        flash("Le nom du fournisseur est obligatoire.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    # SÉCURITÉ : Validation des URLs
    if site_web and not validate_url(site_web):
        flash("L'URL du site web est invalide (doit commencer par http:// ou https://).", "warning")
        return redirect(url_for('admin.gestion_fournisseurs'))
        
    if logo_url and not validate_url(logo_url):
        flash("L'URL du logo est invalide (doit commencer par http:// ou https://).", "warning")
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
        
        # Log
        admin_hash = hash_user_id(session['user_id'])
        current_app.logger.info(f"Fournisseur {nom} ajouté par admin_{admin_hash}")
        
        flash("Fournisseur ajouté avec succès.", "success")
        
    except IntegrityError:
        db.session.rollback()
        flash("Un fournisseur portant ce nom existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout fournisseur: {e}")
        flash("Erreur technique.", "danger")
        
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
        nom = request.form.get('nom', '').strip()
        site_web = request.form.get('site_web', '').strip()
        logo_url = request.form.get('logo_url', '').strip()

        if not nom: 
            raise ValueError("Le nom ne peut pas être vide")
            
        # SÉCURITÉ : Validation des URLs
        if site_web and not validate_url(site_web):
            raise ValueError("URL du site web invalide.")
        if logo_url and not validate_url(logo_url):
            raise ValueError("URL du logo invalide.")
            
        fournisseur.nom = nom
        fournisseur.site_web = site_web or None
        fournisseur.logo = logo_url or None
        
        db.session.commit()
        flash("Fournisseur modifié.", "success")
        
    except ValueError as ve:
        flash(str(ve), "warning")
    except IntegrityError:
        db.session.rollback()
        flash("Ce nom de fournisseur existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modif fournisseur {id}: {e}")
        flash("Erreur technique.", "danger")
        
    return redirect(url_for('admin.gestion_fournisseurs'))

@admin_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    
    if fournisseur and fournisseur.etablissement_id == etablissement_id:
        # Vérification stricte des dépendances avant suppression
        if fournisseur.depenses:
            flash("Impossible de supprimer : ce fournisseur est lié à des dépenses budgétaires.", "danger")
        else:
            try:
                db.session.delete(fournisseur)
                db.session.commit()
                flash("Fournisseur supprimé.", "success")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erreur suppression fournisseur {id}: {e}")
                flash("Erreur technique lors de la suppression.", "danger")
    else:
        flash("Fournisseur introuvable.", "danger")
        
    return redirect(url_for('admin.gestion_fournisseurs'))

# ============================================================
# SAUVEGARDE & RESTAURATION (JSON / SAAS)
# ============================================================
@admin_bp.route("/sauvegardes")
@admin_required
def gestion_sauvegardes():
    etablissement_id = session['etablissement_id']
    
    # Vérification Licence PRO
    param_licence = db.session.execute(
        db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='licence_statut')
    ).scalar_one_or_none()
    
    is_pro = param_licence and param_licence.valeur == 'PRO'
    
    if not is_pro:
        flash("L'accès aux sauvegardes est réservé à la version PRO.", "warning")
        return redirect(url_for('admin.admin'))

    breadcrumbs = [
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Sauvegardes', 'url': None}
    ]
    
    return render_template("admin_backup.html",
                            now=datetime.now(),
                            breadcrumbs=breadcrumbs)


@admin_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    etablissement_id = session['etablissement_id']
    
    # 1. Vérification Licence PRO
    param_licence = db.session.execute(
        db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='licence_statut')
    ).scalar_one_or_none()
    
    if not param_licence or param_licence.valeur != 'PRO':
        flash("La sauvegarde est réservée à la version PRO.", "warning")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        # 2. Récupération des données
        data = {
            'metadata': {
                'version': '1.0',
                'date': datetime.now().isoformat(),
                'etablissement': session.get('nom_etablissement')
            },
            'armoires': [],
            'categories': [],
            'fournisseurs': [],
            'objets': [],
            'budget': [],
            'depenses': [],
            'echeances': []
        }

        # Armoires
        armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for a in armoires:
            data['armoires'].append({'id': a.id, 'nom': a.nom})

        # Catégories
        categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for c in categories:
            data['categories'].append({'id': c.id, 'nom': c.nom})

        # Fournisseurs
        fournisseurs = db.session.execute(db.select(Fournisseur).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for f in fournisseurs:
            data['fournisseurs'].append({'id': f.id, 'nom': f.nom, 'site_web': f.site_web, 'logo': f.logo})

        # Objets
        objets = db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for o in objets:
            data['objets'].append({
                'id': o.id,
                'nom': o.nom,
                'quantite': o.quantite_physique,
                'seuil': o.seuil,
                'armoire_id': o.armoire_id,
                'categorie_id': o.categorie_id,
                'date_peremption': o.date_peremption,
                'image_url': o.image_url,
                'fds_url': o.fds_url
            })
            
        # Budgets & Dépenses
        budgets = db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for b in budgets:
            b_data = {'id': b.id, 'annee': b.annee, 'montant': b.montant_initial, 'cloture': b.cloture}
            data['budget'].append(b_data)
            for d in b.depenses:
                data['depenses'].append({
                    'budget_id': b.id,
                    'date': d.date_depense,
                    'contenu': d.contenu,
                    'montant': d.montant,
                    'est_bon_achat': d.est_bon_achat,
                    'fournisseur_id': d.fournisseur_id
                })

        # Échéances
        echeances = db.session.execute(db.select(Echeance).filter_by(etablissement_id=etablissement_id)).scalars().all()
        for e in echeances:
            data['echeances'].append({
                'intitule': e.intitule,
                'date': e.date_echeance,
                'details': e.details,
                'traite': e.traite
            })

        # 3. Génération du fichier JSON
        json_str = json.dumps(data, default=json_serial, indent=4)
        buffer = BytesIO()
        buffer.write(json_str.encode('utf-8'))
        buffer.seek(0)

        # Audit Log
        from utils import log_action
        log_action('backup_download', "Export complet JSON")

        # Nom de fichier sécurisé
        safe_etab = secure_filename(session.get('nom_etablissement', 'Backup'))
        filename = f"Sauvegarde_{safe_etab}_{date.today()}.json"

        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/json')

    except Exception as e:
        current_app.logger.error(f"Erreur backup: {e}")
        flash("Erreur technique lors de la sauvegarde.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))


@admin_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    etablissement_id = session['etablissement_id']
    
    if 'fichier' not in request.files:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))
        
    fichier = request.files['fichier']
    
    # 1. Vérification Nom vide
    if fichier.filename == '':
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

    # 2. SÉCURITÉ : Vérification Extension via allowed_file + Check spécifique JSON
    if not allowed_file(fichier.filename) or not fichier.filename.endswith('.json'):
        flash("Format invalide. Veuillez fournir un fichier .json autorisé.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        data = json.load(fichier)
        
        # Mappings (Ancien ID -> Nouvel ID)
        map_armoires = {}
        map_categories = {}
        map_fournisseurs = {}
        map_budgets = {}

        # 1. NETTOYAGE (Ordre strict pour FK)
        db.session.query(KitObjet).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Historique).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Reservation).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Suggestion).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Depense).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Objet).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Kit).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Budget).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Echeance).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Armoire).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Categorie).filter_by(etablissement_id=etablissement_id).delete()
        db.session.query(Fournisseur).filter_by(etablissement_id=etablissement_id).delete()
        
        db.session.flush()

        # 2. RECONSTRUCTION (Parents d'abord)
        
        # Armoires
        for a in data.get('armoires', []):
            new_a = Armoire(nom=a['nom'], etablissement_id=etablissement_id)
            db.session.add(new_a)
            db.session.flush()
            map_armoires[a['id']] = new_a.id

        # Catégories
        for c in data.get('categories', []):
            new_c = Categorie(nom=c['nom'], etablissement_id=etablissement_id)
            db.session.add(new_c)
            db.session.flush()
            map_categories[c['id']] = new_c.id

        # Fournisseurs
        for f in data.get('fournisseurs', []):
            new_f = Fournisseur(nom=f['nom'], site_web=f.get('site_web'), logo=f.get('logo'), etablissement_id=etablissement_id)
            db.session.add(new_f)
            db.session.flush()
            map_fournisseurs[f['id']] = new_f.id

        # Objets (Enfants)
        for o in data.get('objets', []):
            new_armoire_id = map_armoires.get(o['armoire_id'])
            new_cat_id = map_categories.get(o['categorie_id'])
            
            if not new_armoire_id or not new_cat_id: continue 

            date_perim = None
            if o.get('date_peremption'):
                try: date_perim = datetime.fromisoformat(o['date_peremption']).date()
                except: pass

            new_obj = Objet(
                nom=o['nom'],
                quantite_physique=o['quantite'],
                seuil=o['seuil'],
                armoire_id=new_armoire_id,
                categorie_id=new_cat_id,
                date_peremption=date_perim,
                image_url=o.get('image_url'),
                fds_url=o.get('fds_url'),
                etablissement_id=etablissement_id
            )
            db.session.add(new_obj)

        # Budgets & Dépenses
        for b in data.get('budget', []):
            new_b = Budget(
                annee=b['annee'],
                montant_initial=b['montant'],
                cloture=b['cloture'],
                etablissement_id=etablissement_id
            )
            db.session.add(new_b)
            db.session.flush()
            map_budgets[b['id']] = new_b.id

        for d in data.get('depenses', []):
            new_budget_id = map_budgets.get(d['budget_id'])
            if not new_budget_id: continue
            
            new_fournisseur_id = map_fournisseurs.get(d['fournisseur_id']) if d.get('fournisseur_id') else None
            
            try: date_dep = datetime.fromisoformat(d['date']).date()
            except: date_dep = date.today()

            new_d = Depense(
                budget_id=new_budget_id,
                fournisseur_id=new_fournisseur_id,
                contenu=d['contenu'],
                montant=d['montant'],
                date_depense=date_dep,
                est_bon_achat=d.get('est_bon_achat', False),
                etablissement_id=etablissement_id
            )
            db.session.add(new_d)

        # Échéances
        for e in data.get('echeances', []):
            try: date_ech = datetime.fromisoformat(e['date']).date()
            except: continue
            
            new_e = Echeance(
                intitule=e['intitule'],
                date_echeance=date_ech,
                details=e.get('details'),
                traite=e.get('traite', 0),
                etablissement_id=etablissement_id
            )
            db.session.add(new_e)

        db.session.commit()
        
        # Audit Log
        from utils import log_action
        log_action('backup_restore', "Restauration complète depuis JSON")
        
        flash("Restauration effectuée avec succès !", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur import DB: {e}")
        flash(f"Erreur critique lors de l'importation : {str(e)}", "error")

    return redirect(url_for('admin.gestion_sauvegardes'))
        
        
        
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
    safe_etab = sanitize_filename(metadata['etablissement'])
    safe_debut = sanitize_filename(metadata['date_debut'])
    safe_fin = sanitize_filename(metadata['date_fin'])
    
    filename = f"Budget_{safe_etab}_{safe_debut}_au_{safe_fin}.pdf"
    
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
        # SÉCURITÉ : Nettoyage anti-injection de formule
        date_val = sanitize_for_excel(item['date'])
        fournisseur_val = sanitize_for_excel(item['fournisseur'])
        contenu_val = sanitize_for_excel(item['contenu'])
        
        ws.cell(row=row_idx, column=1, value=date_val).alignment = center_align
        ws.cell(row=row_idx, column=2, value=fournisseur_val)
        ws.cell(row=row_idx, column=3, value=contenu_val)
        
        # Le montant est un float, donc pas de risque d'injection
        try:
            val_montant = float(item['montant'])
        except (ValueError, TypeError):
            val_montant = 0.0
            
        montant_cell = ws.cell(row=row_idx, column=4, value=val_montant)
        montant_cell.number_format = '#,##0.00 €'
        montant_cell.alignment = right_align
        
        # Bordures
        for col in range(1, 5):
            ws.cell(row=row_idx, column=col).border = border_style
            
        # Zebra striping
        if row_idx % 2 == 0:
            for col in range(1, 5):
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
    
    safe_etab = sanitize_filename(metadata['etablissement'])
    safe_debut = sanitize_filename(metadata['date_debut'])
    safe_fin = sanitize_filename(metadata['date_fin'])
    
    filename = f"Budget_{safe_etab}_{safe_debut}_au_{safe_fin}.xlsx"
    
    return send_file(
        buffer, 
        as_attachment=True, 
        download_name=filename, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )



# ============================================================
# IMPORT / EXPORT (SÉCURISÉ)
# ============================================================

@admin_bp.route("/importer", methods=['GET'])
@admin_required
def importer_page():
    etablissement_id = session['etablissement_id']
    # On récupère les listes pour aider l'utilisateur à vérifier ses noms
    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()
    
    breadcrumbs = [{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Importation en Masse'}]
    return render_template("admin_import.html", breadcrumbs=breadcrumbs, armoires=armoires, categories=categories, now=datetime.now())

@admin_bp.route("/telecharger_modele")
@admin_required
def telecharger_modele_excel():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des données existantes pour les listes déroulantes
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

    # --- 4. CRÉATION DES LISTES DÉROULANTES (Feuille cachée) ---
    ws_data = wb.create_sheet("Data_Listes")
    ws_data.sheet_state = 'hidden' 

    # Remplissage Armoires (Col A) et Catégories (Col B)
    for i, nom in enumerate(armoires, start=1):
        ws_data.cell(row=i, column=1, value=nom)
    for i, nom in enumerate(categories, start=1):
        ws_data.cell(row=i, column=2, value=nom)

    # --- 5. APPLICATION DE LA VALIDATION ---
    # Validation Armoires (Colonne D)
    if armoires:
        dv_armoires = DataValidation(type="list", formula1=f"'Data_Listes'!$A$1:$A${len(armoires)}", allow_blank=True)
        dv_armoires.error = 'Veuillez sélectionner une armoire dans la liste.'
        dv_armoires.errorTitle = 'Armoire inconnue'
        ws.add_data_validation(dv_armoires)
        dv_armoires.add('D2:D1000')

    # Validation Catégories (Colonne E)
    if categories:
        dv_categories = DataValidation(type="list", formula1=f"'Data_Listes'!$B$1:$B${len(categories)}", allow_blank=True)
        dv_categories.error = 'Veuillez sélectionner une catégorie dans la liste.'
        dv_categories.errorTitle = 'Catégorie inconnue'
        ws.add_data_validation(dv_categories)
        dv_categories.add('E2:E1000')

    # Aide Date
    ws['F1'].comment = Comment("Format attendu : AAAA-MM-JJ (ex: 2025-12-31)", "LabFlow")

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='modele_import_inventaire.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin_bp.route("/importer", methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def importer_fichier():
    etablissement_id = session['etablissement_id']
    
    # 1. Vérification présence fichier
    if 'fichier_excel' not in request.files:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.importer_page'))

    fichier = request.files['fichier_excel']
    
    if fichier.filename == '':
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.importer_page'))

    # 2. SÉCURITÉ DoS : Vérification taille fichier (Max 10Mo)
    fichier.seek(0, 2)
    size = fichier.tell()
    fichier.seek(0)
    
    if size > MAX_FILE_SIZE:
        flash(f"Fichier trop volumineux (Max {MAX_FILE_SIZE/1024/1024}MB).", "error")
        return redirect(url_for('admin.importer_page'))

    # 3. SÉCURITÉ : Vérification Extension via allowed_file + Check spécifique XLSX
    if not allowed_file(fichier.filename) or not fichier.filename.endswith('.xlsx'):
        flash("Format invalide. Veuillez utiliser le modèle Excel (.xlsx).", "error")
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
            
            if len(row) < 5:
                errors.append(f"Ligne {i}: Colonnes manquantes.")
                continue

            nom, quantite, seuil, armoire_nom, categorie_nom = row[0], row[1], row[2], row[3], row[4]
            date_peremption = row[5] if len(row) > 5 else None
            image_url = row[6] if len(row) > 6 else None

            if not all([nom, quantite is not None, seuil is not None]):
                errors.append(f"Ligne {i}: Nom, Quantité ou Seuil manquant.")
                continue

            if str(nom).lower() in existing_objets:
                skipped_items.append(str(nom))
                continue

            armoire_id = armoires_map.get(str(armoire_nom).lower().strip()) if armoire_nom else None
            categorie_id = categories_map.get(str(categorie_nom).lower().strip()) if categorie_nom else None

            if not armoire_id:
                errors.append(f"Ligne {i}: Armoire '{armoire_nom}' inconnue. Créez-la d'abord.")
                continue
            if not categorie_id:
                errors.append(f"Ligne {i}: Catégorie '{categorie_nom}' inconnue. Créez-la d'abord.")
                continue

            date_peremption_db = None
            if date_peremption:
                if isinstance(date_peremption, datetime):
                    date_peremption_db = date_peremption.date()
                elif isinstance(date_peremption, str):
                    try:
                        date_peremption_db = datetime.strptime(date_peremption.split(' ')[0], '%Y-%m-%d').date()
                    except ValueError:
                        pass

            nouvel_objet = Objet(
                nom=str(nom),
                quantite_physique=int(quantite),
                seuil=int(seuil),
                armoire_id=armoire_id,
                categorie_id=categorie_id,
                date_peremption=date_peremption_db,
                image_url=str(image_url) if image_url else None,
                etablissement_id=etablissement_id
            )
            db.session.add(nouvel_objet)
            success_count += 1

        if errors:
            db.session.rollback()
            for e in errors[:5]: flash(e, "error")
            if len(errors) > 5: flash(f"... et {len(errors)-5} autres erreurs.", "error")
        else:
            db.session.commit()
            log_action('import_excel', f"Importation de {success_count} objets")
            if success_count > 0: flash(f"Importation réussie : {success_count} objets ajoutés.", "success")
            if skipped_items: flash(f"{len(skipped_items)} objets ignorés car déjà existants.", "warning")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur critique import Excel: {e}")
        flash("Une erreur technique est survenue lors de la lecture du fichier.", "error")

    return redirect(url_for('admin.importer_page'))

@admin_bp.route("/exporter_inventaire")
@admin_required
def exporter_inventaire():
    etablissement_id = session['etablissement_id']
    format_type = request.args.get('format')
    
    # SÉCURITÉ : Limite pour éviter le timeout
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
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventaire"
        
        # En-têtes
        headers = ["Catégorie", "Nom", "Quantité", "Seuil", "Armoire", "Péremption"]
        ws.append(headers)
        
        # Style Header
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F3B73", fill_type="solid")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # Données
        for obj in objets:
            date_str = obj.date_peremption.strftime('%Y-%m-%d') if obj.date_peremption else ""
            
            # SÉCURITÉ : Nettoyage des champs texte
            cat_nom = sanitize_for_excel(obj.categorie.nom if obj.categorie else "")
            obj_nom = sanitize_for_excel(obj.nom)
            arm_nom = sanitize_for_excel(obj.armoire.nom if obj.armoire else "")
            
            ws.append([
                cat_nom,
                obj_nom,
                obj.quantite_physique, # Int, safe
                obj.seuil,             # Int, safe
                arm_nom,
                date_str
            ])
            
        # Ajustement largeurs
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['E'].width = 25
            
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # --- SÉCURISATION ---
        nom_etab = session.get('nom_etablissement', 'Inventaire')
        safe_etab = sanitize_filename(nom_etab)
        safe_date = sanitize_filename(str(date.today()))
        
        filename = f"Inventaire_{safe_etab}_{safe_date}.xlsx"
        
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
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



# ============================================================
# SÉCURITÉ LICENCE (Rate Limiter Optimisé)
# ============================================================
class RateLimiter:
    def __init__(self, window_minutes=15, max_attempts=5):
        self.attempts = defaultdict(list)
        self.window = timedelta(minutes=window_minutes)
        self.max_attempts = max_attempts
    
    def is_allowed(self, key):
        """Vérifie si l'action est autorisée et nettoie l'historique."""
        now = datetime.now()
        
        # 1. Nettoyage : on ne garde que les tentatives récentes (fenêtre glissante)
        # Cela résout la fuite de mémoire
        self.attempts[key] = [
            ts for ts in self.attempts[key] 
            if now - ts < self.window
        ]
        
        # 2. Vérification
        if len(self.attempts[key]) >= self.max_attempts:
            # Calcul du temps d'attente restant pour l'utilisateur
            oldest_attempt = self.attempts[key][0]
            wait_seconds = (self.window - (now - oldest_attempt)).total_seconds()
            return False, int(wait_seconds / 60) + 1
        
        # 3. Enregistrement de la tentative
        self.attempts[key].append(now)
        return True, 0

    def reset(self, key):
        """Réinitialise le compteur en cas de succès."""
        if key in self.attempts:
            del self.attempts[key]

# Instance globale du limiteur
license_limiter = RateLimiter(window_minutes=15, max_attempts=5)

def rate_limit_license(f):
    """Décorateur utilisant la classe RateLimiter"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        etablissement_id = session.get('etablissement_id')
        if not etablissement_id:
            flash("Session invalide", "error")
            return redirect(url_for('main.index'))
        
        # On utilise l'ID établissement comme clé unique
        allowed, wait_minutes = license_limiter.is_allowed(etablissement_id)
        
        if not allowed:
            flash(f"Trop de tentatives incorrectes. Veuillez patienter {wait_minutes} minutes.", "error")
            return redirect(url_for('main.a_propos'))
        
        return f(*args, **kwargs)
    return wrapped

# ============================================================
# ROUTE D'ACTIVATION SÉCURISÉE
# ============================================================
@admin_bp.route("/activer_licence", methods=["POST"])
@admin_required
@rate_limit_license # Utilise notre nouveau décorateur
def activer_licence():
    etablissement_id = session.get('etablissement_id')
    
    # Nettoyer et valider l'input
    cle_fournie = request.form.get('licence_cle', '').strip().upper()
    
    if not cle_fournie or len(cle_fournie) < 10:
        flash("Format de clé invalide.", "error")
        return redirect(url_for('main.a_propos'))
    
    try:
        # 1. Récupérer l'instance_id
        param_instance = db.session.execute(
            db.select(Parametre).filter_by(
                etablissement_id=etablissement_id, 
                cle='instance_id'
            )
        ).scalar_one_or_none()
        
        if not param_instance or not param_instance.valeur:
            flash("Erreur critique : Identifiant d'instance introuvable.", "error")
            return redirect(url_for('main.a_propos'))
        
        instance_id = param_instance.valeur.strip()
        
        # 2. Calculer la clé attendue
        cle_attendue = calculate_license_key(instance_id)
        
        # 3. Comparaison sécurisée
        if not secrets.compare_digest(cle_fournie, cle_attendue):
            flash("Clé de licence incorrecte.", "error")
            return redirect(url_for('main.a_propos'))
        
        # --- SUCCÈS ---
        
        # 4. Mise à jour du statut
        param_statut = db.session.execute(
            db.select(Parametre).filter_by(
                etablissement_id=etablissement_id, 
                cle='licence_statut'
            )
        ).scalar_one_or_none()
        
        if not param_statut:
            param_statut = Parametre(etablissement_id=etablissement_id, cle='licence_statut', valeur='PRO')
            db.session.add(param_statut)
        else:
            if param_statut.valeur == 'PRO':
                flash("Cette licence est déjà active.", "info")
                return redirect(url_for('main.a_propos'))
            param_statut.valeur = 'PRO'
        
        # 5. Enregistrement de la date d'activation
        param_date = db.session.execute(
            db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='licence_date_activation')
        ).scalar_one_or_none()
        
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if param_date:
            param_date.valeur = date_str
        else:
            db.session.add(Parametre(etablissement_id=etablissement_id, cle='licence_date_activation', valeur=date_str))
        
        db.session.commit()

        # --- INVALIDATION DU CACHE (AJOUTÉ ICI) ---
        # On force l'application à relire la base de données pour cet établissement
        # sinon l'utilisateur verra encore "GRATUIT" pendant 5 minutes.
        try:
            cache.delete_memoized(get_etablissement_params, etablissement_id)
        except Exception as e:
            current_app.logger.warning(f"Impossible d'invalider le cache : {e}")
        # ------------------------------------------
        
        # 6. Reset du compteur de tentatives (Succès = on efface l'ardoise)
        license_limiter.reset(etablissement_id)
        
        flash("Félicitations ! Votre licence PRO est activée.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur activation licence: {str(e)}")
        flash("Une erreur technique est survenue.", "error")
    
    return redirect(url_for('main.a_propos'))
