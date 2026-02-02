# ============================================================
# FICHIER : views/inventaire.py
# ============================================================
import math
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_file, session, jsonify, current_app)
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# IMPORTS DB
from db import db, Objet, Armoire, Categorie, Reservation, Utilisateur, Historique, Echeance, Budget, Depense, Fournisseur, Suggestion

# IMPORTS UTILS
from utils import login_required, admin_required, limit_objets_required, allowed_file
from extensions import limiter

from services.inventory_service import InventoryService, InventoryServiceError
from services.security_service import SecurityService
from services.document_service import DocumentService, DocumentServiceError

from markupsafe import Markup

inventaire_bp = Blueprint(
    'inventaire', 
    __name__,
    template_folder='../templates'
)


# ============================================================
# UTILITAIRES INTERNES (Sécurité & Nettoyage)
# ============================================================

def is_valid_url(url):
    """Vérifie si une chaîne est une URL valide (http/https)."""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def cleanup_old_file(relative_path):
    """
    Supprime un fichier local de manière sécurisée.
    """
    if not relative_path or not relative_path.startswith('uploads/'):
        return
    
    try:
        safe_path = os.path.normpath(relative_path)
        root_uploads = os.path.join(current_app.root_path, 'static', 'uploads')
        full_path = os.path.join(current_app.root_path, 'static', safe_path)
        
        if not os.path.abspath(full_path).startswith(os.path.abspath(root_uploads)):
            return
        
        if os.path.exists(full_path):
            os.remove(full_path)
            
    except Exception as e:
        current_app.logger.warning(f"Echec suppression fichier {relative_path}: {e}")


# ============================================================
# ROUTES DASHBOARD & LISTES
# ============================================================
@inventaire_bp.route("/")
def index():
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    if not etablissement_id:
        return redirect(url_for('auth.logout'))
    
    dashboard_data = {}

    if session.get('user_role') == 'admin':
        dashboard_data['stats'] = {
            'total_objets': db.session.query(Objet).filter_by(etablissement_id=etablissement_id).count(),
            'total_utilisateurs': db.session.query(Utilisateur).filter_by(etablissement_id=etablissement_id).count(),
            'reservations_actives': db.session.query(Reservation).filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation >= datetime.now()
            ).count()
        }

    admin_user = db.session.execute(db.select(Utilisateur).filter_by(role='admin', etablissement_id=etablissement_id)).scalar_one_or_none()
    dashboard_data['admin_contact'] = admin_user.email if admin_user and admin_user.email else (admin_user.nom_utilisateur if admin_user else "Non défini")
    
    vingt_quatre_heures_avant = datetime.now() - timedelta(hours=24)
    objets_recents = db.session.execute(db.select(Objet.id, Objet.nom).join(Historique, Objet.id == Historique.objet_id).filter(Objet.etablissement_id == etablissement_id, Historique.timestamp >= vingt_quatre_heures_avant, or_(Historique.action == 'Création', (Historique.action == 'Modification') & (Historique.details.like('%Quantité%')))).group_by(Objet.id, Objet.nom).order_by(db.desc(func.max(Historique.timestamp))).limit(10)).mappings().all()
    dashboard_data['objets_recents'] = objets_recents

    date_aujourdhui = datetime.now().date()
    date_limite = date_aujourdhui + timedelta(days=30)

    echeances_brutes = db.session.execute(
        db.select(Echeance)
        .filter(
            Echeance.etablissement_id == etablissement_id,
            Echeance.traite == 0,
            Echeance.date_echeance >= date_aujourdhui,
            Echeance.date_echeance <= date_limite
        )
        .order_by(Echeance.date_echeance.asc())
        .limit(5)
    ).scalars().all()

    prochaines_echeances_calculees = []
    for echeance in echeances_brutes:
        jours_restants = (echeance.date_echeance - date_aujourdhui).days
        prochaines_echeances_calculees.append({
            'intitule': echeance.intitule,
            'date_echeance_obj': echeance.date_echeance,
            'jours_restants': jours_restants
        })
    dashboard_data['prochaines_echeances'] = prochaines_echeances_calculees

    now = datetime.now()
    
    raw_reservations = db.session.execute(
        db.select(Reservation)
        .options(joinedload(Reservation.objet), joinedload(Reservation.kit))
        .filter(
            Reservation.etablissement_id == etablissement_id,
            Reservation.utilisateur_id == user_id,
            Reservation.debut_reservation >= now
        )
        .order_by(Reservation.debut_reservation.asc())
    ).scalars().all()

    reservations_map = {}
    for r in raw_reservations:
        if r.groupe_id not in reservations_map:
            reservations_map[r.groupe_id] = {
                'groupe_id': r.groupe_id,
                'debut': r.debut_reservation,
                'fin': r.fin_reservation,
                'liste_items': []
            }
        
        is_kit = r.kit_id is not None
        nom = r.kit.nom if is_kit else (r.objet.nom if r.objet else "Inconnu")
        
        reservations_map[r.groupe_id]['liste_items'].append({
            'nom': nom,
            'type': 'kit' if is_kit else 'objet',
            'quantite': r.quantite_reservee
        })

    dashboard_data['reservations'] = list(reservations_map.values())[:5]

    annee_scolaire_actuelle = now.year if now.month >= 9 else now.year - 1

    budget_actuel = db.session.execute(
        db.select(Budget).filter_by(
            annee=annee_scolaire_actuelle,
            cloture=False,
            etablissement_id=etablissement_id
        )
    ).scalar_one_or_none()

    solde_actuel = None
    if budget_actuel:
        total_depenses = db.session.query(func.sum(Depense.montant)).filter_by(
            budget_id=budget_actuel.id,
            etablissement_id=etablissement_id
        ).scalar() or 0
        solde_actuel = budget_actuel.montant_initial - total_depenses

    dashboard_data['solde_budget'] = solde_actuel

    historique_groupe = {
        'creations': [],
        'modifications': [],
        'deplacements': [],
        'suppressions': []
    }

    if session.get('user_role') == 'admin':
        mouvements = db.session.execute(
            db.select(Historique, Objet.nom.label('nom_actuel'), Utilisateur.nom_utilisateur)
            .outerjoin(Objet, Historique.objet_id == Objet.id)
            .outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)
            .filter(Historique.etablissement_id == etablissement_id)
            .order_by(Historique.timestamp.desc())
            .limit(50)
        ).all()

        for h, nom_obj, nom_user in mouvements:
            nom_affichage = nom_obj if nom_obj else "Objet supprimé"
            item = {
                'id': h.id,
                'objet': nom_affichage,
                'user': nom_user or "Inconnu",
                'date': h.timestamp,
                'details': h.details
            }

            if h.action == 'Création':
                historique_groupe['creations'].append(item)
            elif h.action == 'Suppression':
                if "de :" in h.details:
                    try:
                        item['objet'] = h.details.split("de :")[1].strip()
                    except IndexError:
                        pass
                historique_groupe['suppressions'].append(item)
            elif h.action == 'Modification':
                if "Déplacé" in h.details or "Armoire" in h.details:
                    historique_groupe['deplacements'].append(item)
                else:
                    historique_groupe['modifications'].append(item)

    dashboard_data['historique_groupe'] = historique_groupe
    
    fournisseurs = db.session.execute(
        db.select(Fournisseur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Fournisseur.nom)
        .limit(5)
    ).scalars().all()
    
    dashboard_data['fournisseurs'] = fournisseurs

    suggestions_dashboard = db.session.execute(
        db.select(Suggestion)
        .options(joinedload(Suggestion.objet), joinedload(Suggestion.utilisateur))
        .filter_by(etablissement_id=etablissement_id, statut='En attente')
        .order_by(Suggestion.date_demande.desc())
        .limit(10)
    ).scalars().all()
    
    dashboard_data['suggestions'] = suggestions_dashboard
    
    try:
        sec_service = SecurityService()
        dashboard_data['securite'] = sec_service.get_dashboard_stats(etablissement_id)
    except Exception as e:
        current_app.logger.error(f"Erreur chargement widget sécurité: {str(e)}")
        dashboard_data['securite'] = None

    start_tour = db.session.query(Armoire).filter_by(etablissement_id=etablissement_id).count() == 0
    
    return render_template("index.html", start_tour=start_tour, now=datetime.now(), data=dashboard_data)


@inventaire_bp.route("/inventaire")
@login_required
def inventaire():
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    
    filters = {
        'q': request.args.get('q', None),
        'type': request.args.get('type', None),
        'armoire_id': request.args.get('armoire', type=int),
        'categorie_id': request.args.get('categorie', type=int),
        'etat': request.args.get('etat', None)
    }

    try:
        dto = service.get_paginated_inventory(page, sort_by, direction, filters)

        pagination = {
            'page': dto.current_page,
            'total_pages': dto.total_pages,
            'endpoint': 'inventaire.inventaire'
        }
        
        armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
        categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()
        armoire_id = request.args.get('armoire', type=int)
        categorie_id = request.args.get('categorie', type=int)
        
        all_armoires = armoires
        all_categories = categories
        
        return render_template("inventaire.html",
                            objets=dto.items,
                            armoires=armoires,
                            categories=categories,
                            all_armoires=all_armoires,
                            all_categories=all_categories,
                            pagination=pagination,
                            date_actuelle=datetime.now(),
                            now=datetime.now,
                            sort_by=sort_by,
                            direction=direction,
                            is_general_inventory=True,
                            armoire_id=armoire_id,
                            categorie_id=categorie_id
                            )
                            
    except Exception as e:
        current_app.logger.error(f"Erreur inventaire: {e}")
        flash("Erreur lors du chargement de l'inventaire.", "error")
        return redirect(url_for('inventaire.index'))


# ============================================================
# ROUTES DE GESTION DES OBJETS (CRUD)
# ============================================================

@inventaire_bp.route("/ajouter_objet", methods=["POST"])
@login_required
@limit_objets_required
def ajouter_objet():
    etablissement_id = session['etablissement_id']
    user_id = session.get('user_id')

    def clean_float(val):
        if not val: return 0.0
        try: return float(str(val).replace(',', '.').strip())
        except ValueError: return 0.0

    def clean_int(val):
        if not val: return 0
        try: return int(float(str(val).replace(',', '.').strip()))
        except ValueError: return 0

    try:
        # 1. NOM
        nom = request.form.get("nom", "").strip()
        if not nom or len(nom) > 200:  # ✅ Ajout limite
            flash("Nom invalide (1-200 caractères).", "error")
            return redirect(request.referrer)

        # 2. TYPE
        type_objet = request.form.get("type_objet", "materiel")
        if type_objet not in ['produit', 'materiel']:  # ✅ Validation
            type_objet = 'materiel'
        
        niveau_requis = request.form.get("niveau_requis", "tous")
        
        quantite = 0
        unite = "unite"
        capacite = 0.0
        niveau = 0.0
        seuil = 0
        seuil_pct = 0

        if type_objet == 'produit':
            quantite = 1
            
            # ✅ VALIDATION UNITÉ
            UNITES = ['mL', 'L', 'g', 'kg']
            unite = request.form.get("unite", "mL")
            if unite not in UNITES:
                flash("Unité invalide.", "error")
                return redirect(request.referrer)
            
            # ✅ VALIDATION CAPACITÉ (avec limite haute)
            capacite_input = request.form.get("capacite_initiale", "").strip()
            if capacite_input:
                # L'utilisateur a explicitement modifié la capacité
                capacite = clean_float(capacite_input)
                if capacite <= 0 or capacite > 1000000:
                    flash("La contenance doit être comprise entre 0 et 1 000 000.", "error")
                    return redirect(request.referrer)
            else:
                # Si vide, on GARDE l'ancienne capacité
                if objet.type_objet == 'produit':
                    capacite = objet.capacite_initiale
                else:
                    # Si conversion matériel → produit, on demande une capacité
                    flash("Veuillez indiquer la contenance totale du produit.", "error")
                    return redirect(request.referrer)
            
            niveau_input = request.form.get("niveau_actuel", "").strip()
            niveau = clean_float(niveau_input) if niveau_input else capacite
            
            # ✅ VALIDATION SEUIL %
            seuil_pct = clean_int(request.form.get("seuil_pourcentage", "20"))
            if not (0 <= seuil_pct <= 100):
                flash("Seuil invalide (0-100%).", "error")
                return redirect(request.referrer)
                
        else:  # Matériel
            quantite = clean_int(request.form.get("quantite"))
            if quantite < 0 or quantite > 100000:  # ✅ Limite haute
                flash("Quantité invalide.", "error")
                return redirect(request.referrer)
            seuil = clean_int(request.form.get("seuil"))

        # 3. ✅ VALIDATION FK (CRITIQUE)
        try:
            armoire_id = int(request.form.get("armoire_id"))
            categorie_id = int(request.form.get("categorie_id"))
        except (ValueError, TypeError):
            flash("Erreur de classement.", "error")
            return redirect(request.referrer)

        armoire = db.session.get(Armoire, armoire_id)
        if not armoire or armoire.etablissement_id != etablissement_id:
            flash("Armoire non autorisée.", "error")
            return redirect(request.referrer)

        categorie = db.session.get(Categorie, categorie_id)
        if not categorie or categorie.etablissement_id != etablissement_id:
            flash("Catégorie non autorisée.", "error")
            return redirect(request.referrer)

        # 4. ✅ VALIDATION DATE PÉREMPTION
        date_peremption = None
        date_str = request.form.get("date_peremption", "").strip()
        if date_str:
            try:
                date_peremption = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Format de date invalide.", "error")
                return redirect(request.referrer)

        # 5. GESTION IMAGE (OK)
        image_path_db = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"{ts}_{filename}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'images', 'objets')
                    if not os.path.exists(upload_dir): os.makedirs(upload_dir)
                    file.save(os.path.join(upload_dir, unique_filename))
                    image_path_db = f"images/objets/{unique_filename}"
                else:
                    flash(f"Extension non supportée : {file.filename}", "error")
                    return redirect(request.referrer)
        
        if not image_path_db:
            url_web = request.form.get("image_url", "").strip()
            if url_web: image_path_db = url_web

        # 6. GESTION FDS (OK)
        fds_path_db = None
        if 'fds_file' in request.files:
            file = request.files['fds_file']
            if file and file.filename != '':
                if file.filename.lower().endswith('.pdf'):
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"FDS_{ts}_{filename}"
                    fds_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'fds')
                    if not os.path.exists(fds_dir): os.makedirs(fds_dir)
                    file.save(os.path.join(fds_dir, unique_filename))
                    fds_path_db = f"uploads/fds/{unique_filename}"
        
        if not fds_path_db:
            fds_path_db = request.form.get("fds_url", "").strip() or None

        # 7. CRÉATION OBJET
        new_objet = Objet(
            nom=nom, type_objet=type_objet, niveau_requis=niveau_requis,
            unite=unite, capacite_initiale=capacite, niveau_actuel=niveau, seuil_pourcentage=seuil_pct,
            quantite_physique=quantite, seuil=seuil,
            armoire_id=armoire_id, categorie_id=categorie_id,
            image_url=image_path_db, fds_url=fds_path_db,
            is_cmr=(request.form.get('is_cmr') == 'on'),
            etablissement_id=etablissement_id,
            date_peremption=date_peremption  # ✅ Variable validée
        )
        
        db.session.add(new_objet)
        db.session.commit()
        
        # 8. HISTORIQUE
        details = f"Ajout ({type_objet})"
        if type_objet == 'produit': details += f" - Total: {capacite} {unite}"
        else: details += f" - Qté: {quantite}"

        db.session.add(Historique(
            objet_id=new_objet.id, utilisateur_id=user_id, action="Création",
            details=details, etablissement_id=etablissement_id, timestamp=datetime.now()
        ))
        db.session.commit()
        
        flash(f"'{nom}' ajouté avec succès.", "success")
        
    # ✅ GESTION D'ERREURS AMÉLIORÉE
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur DB ajout: {e}")
        flash("Erreur lors de l'enregistrement.", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Erreur inattendue ajout")
        flash("Erreur technique.", "error")
        
    return redirect(request.referrer or url_for('inventaire.index'))


@inventaire_bp.route("/modifier_objet/<int:id_objet>", methods=["POST"])
@login_required
def modifier_objet(id_objet):
    # 1. VÉRIFICATION OBJET & DROITS
    objet = db.session.get(Objet, id_objet)
    if not objet or objet.etablissement_id != session['etablissement_id']:
        flash("Objet non trouvé ou accès interdit.", "error")
        return redirect(url_for('inventaire.index'))

    user_id = session.get('user_id')
    etablissement_id = session['etablissement_id']
    files_to_cleanup = []

    # --- FONCTIONS DE NETTOYAGE ---
    def clean_float(val):
        if not val: return 0.0
        try: return float(str(val).replace(',', '.').strip())
        except ValueError: return 0.0

    def clean_int(val):
        if not val: return 0
        try: return int(float(str(val).replace(',', '.').strip()))
        except ValueError: return 0
    # ------------------------------

    try:
        # 2. VALIDATION NOM
        nom = request.form.get("nom", "").strip()
        if not nom or len(nom) > 200:
            flash("Nom invalide (1-200 caractères).", "error")
            return redirect(request.referrer)

        # 3. VALIDATION TYPE
        type_objet = request.form.get("type_objet", "materiel")
        if type_objet not in ['produit', 'materiel']:
            flash("Type d'objet invalide.", "error")
            return redirect(request.referrer)

        niveau_requis = request.form.get("niveau_requis", "tous")

        # 4. VALIDATION SELON TYPE
        # Initialisation des variables
        quantite = 0
        unite = "unite"
        capacite = 0.0
        niveau = 0.0
        seuil = 0
        seuil_pct = 0

        if type_objet == 'produit':
            # --- LOGIQUE PRODUIT ---
            
            # Validation Unité
            UNITES_AUTORISEES = ['mL', 'L', 'g', 'kg']
            unite = request.form.get("unite", "mL")
            if unite not in UNITES_AUTORISEES:
                flash("Unité invalide.", "error")
                return redirect(request.referrer)

            # Validation Capacité
            capacite = clean_float(request.form.get("capacite_initiale"))
            if capacite <= 0 or capacite > 1000000:
                flash("La contenance doit être comprise entre 0 et 1 000 000.", "error")
                return redirect(request.referrer)

            # Validation Niveau (CORRECTION CRITIQUE : Ne pas reset si vide)
            niveau_input = request.form.get("niveau_actuel", "").strip()
            if niveau_input:
                # Si l'utilisateur a saisi une valeur, on l'utilise
                niveau = clean_float(niveau_input)
                if niveau < 0:
                    flash("Le niveau ne peut pas être négatif.", "error")
                    return redirect(request.referrer)
                if niveau > capacite:
                    flash(f"Le niveau ({niveau}) ne peut pas dépasser la contenance ({capacite}).", "warning")
                    niveau = capacite
            else:
                # Si vide ET c'était déjà un produit, on garde l'ancien niveau
                if objet.type_objet == 'produit':
                    niveau = objet.niveau_actuel
                else:
                    # Si conversion matériel → produit, on initialise au max
                    niveau = capacite

            # Validation Seuil %
            seuil_pct = clean_int(request.form.get("seuil_pourcentage"))
            if not (0 <= seuil_pct <= 100):
                flash("Le seuil d'alerte doit être entre 0 et 100%.", "error")
                return redirect(request.referrer)

            # Force les valeurs matériel à 0/1
            quantite = 1
            seuil = 0

        else:
            # --- LOGIQUE MATÉRIEL ---
            quantite = clean_int(request.form.get("quantite"))
            if quantite < 0 or quantite > 100000:
                flash("Quantité invalide (0-100 000).", "error")
                return redirect(request.referrer)
            
            seuil = clean_int(request.form.get("seuil"))
            if seuil < 0: seuil = 0

            # Reset des valeurs produit
            unite = "unité"
            capacite = 0.0
            niveau = 0.0
            seuil_pct = 0

        # 5. VALIDATION FK (ARMOIRE / CATÉGORIE)
        try:
            armoire_id = int(request.form.get("armoire_id", 0))
            categorie_id = int(request.form.get("categorie_id", 0))
        except (ValueError, TypeError):
            flash("Identifiants invalides.", "error")
            return redirect(request.referrer)

        # Vérification existence et appartenance
        if armoire_id:
            armoire = db.session.get(Armoire, armoire_id)
            if not armoire or armoire.etablissement_id != etablissement_id:
                flash("Armoire invalide.", "error")
                return redirect(request.referrer)
        
        if categorie_id:
            categorie = db.session.get(Categorie, categorie_id)
            if not categorie or categorie.etablissement_id != etablissement_id:
                flash("Catégorie invalide.", "error")
                return redirect(request.referrer)

        # 6. DATE PÉREMPTION
        date_peremption_str = request.form.get("date_peremption", "").strip()
        date_peremption = None
        if date_peremption_str:
            try:
                date_peremption = datetime.strptime(date_peremption_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Format de date invalide.", "error")
                return redirect(request.referrer)

        # Capture état avant modif (Pour l'historique)
        anciens = {
            'nom': objet.nom,
            'quantite': objet.quantite_physique,
            'niveau': objet.niveau_actuel,
            'type': objet.type_objet
        }

        # --- GESTION IMAGE (Code inchangé) ---
        is_image_updated = False
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Nettoyage ancien fichier (si local, pas URL web)
                    if objet.image_url and objet.image_url.startswith('images/'):
                        files_to_cleanup.append(objet.image_url)
                    
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"{ts}_{filename}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'images', 'objets')
                    if not os.path.exists(upload_dir): 
                        os.makedirs(upload_dir)
                    file.save(os.path.join(upload_dir, unique_filename))
                    objet.image_url = f"images/objets/{unique_filename}"
                    is_image_updated = True

        if not is_image_updated:
            url_input = request.form.get("image_url")
            if url_input is not None:
                url_clean = url_input.strip()
                if url_clean:
                    if is_valid_url(url_clean):
                        if objet.image_url and objet.image_url.startswith('images/'):
                            files_to_cleanup.append(objet.image_url)
                        objet.image_url = url_clean
                else:
                    if objet.image_url and objet.image_url.startswith('images/'):
                        files_to_cleanup.append(objet.image_url)
                    objet.image_url = None

        # --- GESTION FDS (Code inchangé) ---
        is_fds_updated = False
        if 'fds_file' in request.files:
            file = request.files['fds_file']
            if file and file.filename != '':
                if file.filename.lower().endswith('.pdf'):
                    if objet.fds_url and objet.fds_url.startswith('uploads/'):
                        files_to_cleanup.append(objet.fds_url)
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"FDS_{ts}_{filename}"
                    fds_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'fds')
                    if not os.path.exists(fds_folder): os.makedirs(fds_folder)
                    file.save(os.path.join(fds_folder, unique_filename))
                    objet.fds_url = f"uploads/fds/{unique_filename}"
                    is_fds_updated = True

        if not is_fds_updated:
            fds_input = request.form.get("fds_url")
            if fds_input is not None:
                url_clean = fds_input.strip()
                if url_clean:
                    if is_valid_url(url_clean):
                        if objet.fds_url and objet.fds_url.startswith('uploads/'):
                            files_to_cleanup.append(objet.fds_url)
                        objet.fds_url = url_clean
                else:
                    if objet.fds_url and objet.fds_url.startswith('uploads/'):
                        files_to_cleanup.append(objet.fds_url)
                    objet.fds_url = None

        # --- MISE À JOUR EFFECTIVE ---
        objet.nom = nom
        objet.type_objet = type_objet
        objet.niveau_requis = niveau_requis
        
        # Champs Produits
        objet.unite = unite
        objet.capacite_initiale = capacite
        objet.niveau_actuel = niveau
        objet.seuil_pourcentage = seuil_pct
        
        # Champs Matériel
        objet.quantite_physique = quantite
        objet.seuil = seuil
        
        objet.armoire_id = armoire_id
        objet.categorie_id = categorie_id
        objet.date_peremption = date_peremption
        objet.is_cmr = (request.form.get('is_cmr') == 'on')
        
        # --- HISTORIQUE ---
        details_modif = []
        if anciens['type'] != objet.type_objet:
            details_modif.append(f"Type: {anciens['type']} ➝ {objet.type_objet}")
        
        if objet.type_objet == 'produit':
            if anciens['niveau'] != objet.niveau_actuel:
                details_modif.append(f"Conso: {anciens['niveau']} ➝ {objet.niveau_actuel} {unite}")
        else:
            if anciens['quantite'] != objet.quantite_physique:
                diff = objet.quantite_physique - anciens['quantite']
                signe = "+" if diff > 0 else ""
                details_modif.append(f"Stock: {anciens['quantite']} ➝ {objet.quantite_physique} ({signe}{diff})")

        if details_modif:
            msg = ", ".join(details_modif)
            hist = Historique(
                objet_id=objet.id,
                utilisateur_id=user_id,
                action="Modification",
                details=msg,
                etablissement_id=etablissement_id,
                timestamp=datetime.now()
            )
            db.session.add(hist)

        db.session.commit()
        
        for old_path in files_to_cleanup:
            cleanup_old_file(old_path)

        flash(f"L'objet '{objet.nom}' a été mis à jour.", "success")

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur intégrité modification {id_objet}: {e}")
        flash("Erreur de base de données (doublon ou contrainte).", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Erreur inattendue modification {id_objet}")
        flash("Erreur technique inattendue.", "error")

    return redirect(request.referrer or url_for('inventaire.index'))


@inventaire_bp.route("/objet/supprimer/<int:id_objet>", methods=["POST"])
@admin_required
def supprimer_objet(id_objet):
    objet = db.session.get(Objet, id_objet)
    
    # Vérification d'appartenance
    if not objet or objet.etablissement_id != session['etablissement_id']:
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    try:
        nom_objet = objet.nom
        
        # Historique
        hist = Historique(
            objet_id=None, 
            utilisateur_id=session.get('user_id'),
            action="Suppression",
            details=f"Suppression définitive de : {nom_objet}",
            etablissement_id=session['etablissement_id'],
            timestamp=datetime.now()
        )
        db.session.add(hist)
        
        # Suppression
        db.session.delete(objet)
        db.session.commit()
        flash(f"L'objet '{nom_objet}' a été supprimé.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression objet: {e}")
        flash(f"Une erreur est survenue lors de la suppression.", "error")

    return redirect(request.referrer or url_for('inventaire.inventaire'))


@inventaire_bp.route("/objet/<int:objet_id>")
@login_required
def voir_objet(objet_id):
    etablissement_id = session['etablissement_id']
    
    objet = db.session.execute(
        db.select(Objet)
        .options(joinedload(Objet.armoire), joinedload(Objet.categorie))
        .filter_by(id=objet_id, etablissement_id=etablissement_id)
    ).scalar_one_or_none()

    if not objet:
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    now = datetime.now()
    total_reserve = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
        Reservation.objet_id == objet.id,
        Reservation.etablissement_id == etablissement_id,
        Reservation.fin_reservation > now
    ).scalar() or 0
    
    # Calcul disponible (Pour produit, c'est le niveau, pour matériel c'est la qté)
    if objet.type_objet == 'produit':
        objet.quantite_disponible = objet.niveau_actuel
    else:
        objet.quantite_disponible = objet.quantite_physique - total_reserve

    results = db.session.execute(
        db.select(Historique, Utilisateur)
        .outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)
        .filter(Historique.objet_id == objet.id)
        .filter(Historique.etablissement_id == etablissement_id)
        .order_by(Historique.timestamp.desc())
        .limit(20)
    ).all()

    historique = []
    for h, u in results:
        h.nom_utilisateur = u.nom_utilisateur if u else "Utilisateur supprimé"
        historique.append(h)

    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Inventaire', 'url': url_for('inventaire.inventaire')},
    ]
    
    if objet.categorie:
        breadcrumbs.append({
            'text': objet.categorie.nom, 
            'url': url_for('inventaire.voir_categorie', categorie_id=objet.categorie.id)
        })
    
    breadcrumbs.append({'text': objet.nom, 'url': None})

    return render_template("objet_details.html",
                           objet=objet,
                           historique=historique,
                           armoires=armoires,
                           categories=categories,
                           breadcrumbs=breadcrumbs,
                           now=datetime.now())


@inventaire_bp.route("/armoire/<int:armoire_id>")
@login_required
def voir_armoire(armoire_id):
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    
    armoire = db.session.get(Armoire, armoire_id)
    if not armoire or armoire.etablissement_id != etablissement_id:
        flash("Armoire non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    filters = {'armoire_id': armoire_id}
    dto = service.get_paginated_inventory(page, sort_by, direction, filters)

    pagination = {
        'page': dto.current_page,
        'total_pages': dto.total_pages,
        'endpoint': 'inventaire.voir_armoire',
        'armoire_id': armoire_id
    }

    autres_armoires = db.session.execute(
        db.select(Armoire)
        .filter(
            Armoire.etablissement_id == etablissement_id,
            Armoire.id != armoire_id
        )
        .order_by(Armoire.nom)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gestion des Armoires', 'url': url_for('main.gestion_armoires')},
        {'text': armoire.nom, 'url': None}
    ]

    # Pour la modale d'ajout
    all_armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    all_categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()

    return render_template("armoire.html",
                           armoire=armoire,
                           objets=dto.items,
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           autres_armoires=autres_armoires,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=datetime.now(),
                           armoire_id=armoire_id,
                           categorie_id=None,
                           all_armoires=all_armoires,
                           all_categories=all_categories
                           )


@inventaire_bp.route("/categorie/<int:categorie_id>")
@login_required
def voir_categorie(categorie_id):
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')

    categorie = db.session.get(Categorie, categorie_id)
    if not categorie or categorie.etablissement_id != etablissement_id:
        flash("Catégorie non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    filters = {'categorie_id': categorie_id}
    dto = service.get_paginated_inventory(page, sort_by, direction, filters)

    pagination = {
        'page': dto.current_page,
        'total_pages': dto.total_pages,
        'endpoint': 'inventaire.voir_categorie',
        'categorie_id': categorie_id
    }

    categories_list = db.session.execute(
        db.select(Categorie)
        .filter(
            Categorie.etablissement_id == etablissement_id,
            Categorie.id != categorie_id
        )
        .order_by(Categorie.nom)
    ).scalars().all()

    # Liste des armoires pour le déplacement de masse
    armoires = db.session.execute(
        db.select(Armoire)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Armoire.nom)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gestion des Catégories', 'url': url_for('main.gestion_categories')},
        {'text': categorie.nom, 'url': None}
    ]

    # Pour la modale d'ajout
    all_armoires = armoires
    all_categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()

    return render_template("categorie.html",
                           categorie=categorie,
                           objets=dto.items,
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           categories_list=categories_list,
                           armoires=armoires,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=datetime.now(),
                           armoire_id=None,
                           categorie_id=categorie_id,
                           all_armoires=all_armoires,
                           all_categories=all_categories
                           )
                           
@inventaire_bp.route("/maj_traite/<int:objet_id>", methods=["POST"])
@login_required
def maj_traite(objet_id):
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    
    objet = db.session.get(Objet, objet_id)

    if not objet or objet.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Objet non trouvé ou accès non autorisé."), 404

    try:
        objet.traite = 1 if data.get("traite") else 0
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


@inventaire_bp.route("/maj_commande/<int:objet_id>", methods=["POST"])
@login_required
def maj_commande(objet_id):
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    
    objet = db.session.get(Objet, objet_id)

    if not objet or objet.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Objet non trouvé ou accès non autorisé."), 404

    try:
        objet.en_commande = 1 if data.get("en_commande") else 0
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


@inventaire_bp.route("/dormants")
@login_required
def objets_dormants():
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)
    
    dormants = service.get_dormant_objects(days=365)
    
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Centre d\'Alertes', 'url': url_for('main.alertes')},
        {'text': 'Stocks Dormants', 'url': None}
    ]
    
    return render_template("dormants.html", 
                           objets=dormants, 
                           breadcrumbs=breadcrumbs,
                           now=datetime.now())


@inventaire_bp.route("/exporter", methods=['GET'])
@login_required
@limiter.limit("10 per minute")
def exporter_inventaire():
    etablissement_id = session['etablissement_id']
    
    format_type = request.args.get('format')
    armoire_id = request.args.get('armoire_id', type=int)
    categorie_id = request.args.get('categorie_id', type=int)
    filter_type = request.args.get('filter')
    
    if format_type not in ['excel', 'pdf']:
        flash("Format non supporté.", "error")
        return redirect(request.referrer or url_for('inventaire.index'))

    try:
        query = db.select(Objet).options(
            joinedload(Objet.categorie), 
            joinedload(Objet.armoire)
        ).filter_by(etablissement_id=etablissement_id)

        titre_doc = f"Inventaire - {session.get('nom_etablissement', 'Global')}"
        filename_prefix = "Inventaire"
        
        if filter_type == 'cmr':
            query = query.filter(Objet.is_cmr == True)
            titre_doc = "Inventaire - Produits CMR"
            filename_prefix = "CMR"
            
        elif armoire_id:
            armoire = db.session.get(Armoire, armoire_id)
            if not armoire or armoire.etablissement_id != etablissement_id:
                return redirect(url_for('inventaire.index'))
            query = query.filter(Objet.armoire_id == armoire_id)
            titre_doc = f"Inventaire - {armoire.nom}"
            filename_prefix = f"Armoire_{armoire.nom}"
        
        elif categorie_id:
            categorie = db.session.get(Categorie, categorie_id)
            if not categorie or categorie.etablissement_id != etablissement_id:
                return redirect(url_for('inventaire.index'))
            query = query.filter(Objet.categorie_id == categorie_id)
            titre_doc = f"Inventaire - {categorie.nom}"
            filename_prefix = f"Categorie_{categorie.nom}"

        objets = db.session.execute(query.order_by(Objet.nom)).scalars().all()
        
        if not objets:
            flash("Aucun objet à exporter dans cette sélection.", "warning")
            return redirect(request.referrer)

        upload_root = os.path.join(current_app.root_path, 'static', 'uploads')
        doc_service = DocumentService(upload_root)
        
        result = doc_service.generate_inventory_pdf(
            etablissement_name=session.get('nom_etablissement'),
            etablissement_id=etablissement_id,
            objets=objets,
            doc_title=titre_doc.upper(),
            filename_prefix=filename_prefix
        )
        
        return send_file(
            os.path.join(current_app.root_path, 'static', result['relative_path']),
            as_attachment=True,
            download_name=result['filename']
        )

    except Exception as e:
        current_app.logger.error(f"Erreur export contextuel: {e}", exc_info=True)
        flash("Erreur technique lors de l'export.", "error")
        return redirect(request.referrer)