# ============================================================
# FICHIER : views/inventaire.py
# ============================================================
import math
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, current_app)
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

# IMPORTS DB
from db import db, Objet, Armoire, Categorie, Reservation, Utilisateur, Historique, Echeance, Budget, Depense, Fournisseur, Suggestion

# IMPORTS UTILS
from utils import login_required, admin_required, limit_objets_required, allowed_file

# --- CORRECTION ICI : On importe le Service au lieu de la fonction API ---
from services.inventory_service import InventoryService, InventoryServiceError
from services.security_service import SecurityService

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
    Empêche la traversée de répertoire (Path Traversal).
    """
    if not relative_path or not relative_path.startswith('uploads/'):
        return
    
    try:
        # 1. Normalisation du chemin
        safe_path = os.path.normpath(relative_path)
        
        # 2. Vérification que le chemin reste dans 'static/uploads'
        root_uploads = os.path.join(current_app.root_path, 'static', 'uploads')
        full_path = os.path.join(current_app.root_path, 'static', safe_path)
        
        # On compare les chemins absolus pour être sûr
        if not os.path.abspath(full_path).startswith(os.path.abspath(root_uploads)):
            current_app.logger.warning(f"SECURITY: Tentative de suppression hors uploads : {relative_path}")
            return
        
        if os.path.exists(full_path):
            os.remove(full_path)
            current_app.logger.info(f"Fichier orphelin supprimé : {full_path}")
            
    except Exception as e:
        current_app.logger.warning(f"Echec suppression fichier {relative_path}: {e}")



# ============================================================
# ROUTES
# ============================================================
@inventaire_bp.route("/")
@login_required
def index():
    # --- LOGIQUE DASHBOARD (Conservée) ---
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    if not etablissement_id:
        flash("Erreur critique : session invalide. Veuillez vous reconnecter.", "error")
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

    # 2. Regroupement intelligent en Python
    reservations_map = {}
    for r in raw_reservations:
        if r.groupe_id not in reservations_map:
            reservations_map[r.groupe_id] = {
                'groupe_id': r.groupe_id,
                'debut': r.debut_reservation,
                'fin': r.fin_reservation,
                'liste_items': [] # On utilise 'liste_items' pour éviter le conflit Jinja
            }
        
        # On détermine le nom et le type
        is_kit = r.kit_id is not None
        nom = r.kit.nom if is_kit else (r.objet.nom if r.objet else "Inconnu")
        
        reservations_map[r.groupe_id]['liste_items'].append({
            'nom': nom,
            'type': 'kit' if is_kit else 'objet',
            'quantite': r.quantite_reservee
        })

    # 3. On transforme en liste et on garde les 5 prochaines
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

    # --- LOGIQUE HISTORIQUE ADMINISTRATEUR (Catégorisé) ---
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
    
    # --- NOUVEAU : WIDGET SÉCURITÉ ---
    try:
        sec_service = SecurityService()
        dashboard_data['securite'] = sec_service.get_dashboard_stats(etablissement_id)
    except Exception as e:
        current_app.logger.error(f"Erreur chargement widget sécurité: {str(e)}")
        dashboard_data['securite'] = None
    # ---------------------------------

    start_tour = db.session.query(Armoire).filter_by(etablissement_id=etablissement_id).count() == 0
    
    return render_template("index.html", start_tour=start_tour, now=datetime.now(), data=dashboard_data)


@inventaire_bp.route("/inventaire")
@login_required
def inventaire():
    """
    Affiche l'inventaire principal.
    CORRIGÉ : Utilise InventoryService.
    """
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    # Paramètres
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    
    
    filters = {
        'q': request.args.get('q', None),
        'armoire_id': request.args.get('armoire', type=int),
        'categorie_id': request.args.get('categorie', type=int),
        'etat': request.args.get('etat', None)
    }

    try:
        # Appel Service (Retourne un DTO)
        dto = service.get_paginated_inventory(page, sort_by, direction, filters)

        # Construction du dict pagination pour le template
        pagination = {
            'page': dto.current_page,
            'total_pages': dto.total_pages,
            'endpoint': 'inventaire.inventaire'
        }
        
        # Listes pour les filtres (Dropdowns)
        armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
        categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()
        armoire_id = request.args.get('armoire', type=int)
        categorie_id = request.args.get('categorie', type=int)
        
        return render_template("inventaire.html",
                            objets=dto.items, # Liste de dicts
                            armoires=armoires,
                            categories=categories,
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

    try:
        # 1. Validation Nom
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom de l'objet est obligatoire.", "error")
            return redirect(request.referrer)

        # 2. Validation Numérique
        quantite = int(request.form.get("quantite", 0))
        seuil = int(request.form.get("seuil", 0))
        if quantite < 0 or seuil < 0:
            raise ValueError("Valeurs négatives interdites.")

        # 3. Validation Foreign Keys (Intégrité)
        armoire_id = int(request.form.get("armoire_id"))
        categorie_id = int(request.form.get("categorie_id"))

        armoire = db.session.get(Armoire, armoire_id)
        if not armoire or armoire.etablissement_id != etablissement_id:
            flash("Armoire invalide.", "error")
            return redirect(request.referrer)

        categorie = db.session.get(Categorie, categorie_id)
        if not categorie or categorie.etablissement_id != etablissement_id:
            flash("Catégorie invalide.", "error")
            return redirect(request.referrer)

        # --- GESTION IMAGE ---
        image_path_db = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # Check taille (5 Mo)
                file.seek(0, 2)
                if file.tell() > 5 * 1024 * 1024:
                    flash("Image trop volumineuse (Max 5 Mo).", "warning")
                else:
                    file.seek(0)
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        ts = datetime.now().strftime("%Y%m%d%H%M%S")
                        unique_filename = f"{ts}_{filename}"
                        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                        if not os.path.exists(upload_folder): os.makedirs(upload_folder)
                        file.save(os.path.join(upload_folder, unique_filename))
                        image_path_db = f"uploads/{unique_filename}"
        
        if not image_path_db:
            url_input = request.form.get("image_url", "").strip()
            if url_input and is_valid_url(url_input):
                image_path_db = url_input

        # --- GESTION FDS ---
        fds_path_db = None
        if 'fds_file' in request.files:
            file = request.files['fds_file']
            if file and file.filename != '':
                file.seek(0, 2)
                if file.tell() > 5 * 1024 * 1024:
                    flash("FDS trop volumineuse (Max 5 Mo).", "warning")
                else:
                    file.seek(0)
                    if file.filename.lower().endswith('.pdf'):
                        filename = secure_filename(file.filename)
                        ts = datetime.now().strftime("%Y%m%d%H%M%S")
                        unique_filename = f"FDS_{ts}_{filename}"
                        fds_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'fds')
                        if not os.path.exists(fds_folder): os.makedirs(fds_folder)
                        file.save(os.path.join(fds_folder, unique_filename))
                        fds_path_db = f"uploads/fds/{unique_filename}"

        if not fds_path_db:
            url_input = request.form.get("fds_url", "").strip()
            if url_input and is_valid_url(url_input):
                fds_path_db = url_input

        # --- CRÉATION ---
        new_objet = Objet(
            nom=nom,
            quantite_physique=quantite,
            seuil=seuil,
            armoire_id=armoire_id,
            categorie_id=categorie_id,
            date_peremption=request.form.get("date_peremption") or None,
            image_url=image_path_db,
            fds_url=fds_path_db,
            etablissement_id=etablissement_id
        )
        db.session.add(new_objet)
        db.session.flush() 
        
        hist = Historique(
            objet_id=new_objet.id,
            utilisateur_id=user_id,
            action="Création",
            details=f"Ajout initial (Qté: {new_objet.quantite_physique})",
            etablissement_id=etablissement_id,
            timestamp=datetime.now()
        )
        db.session.add(hist)
        db.session.commit()
        flash(f"L'objet '{new_objet.nom}' a été ajouté avec succès !", "success")
        
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Données invalides.", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout objet: {e}")
        flash(f"Une erreur est survenue.", "error")
        
    return redirect(request.referrer or url_for('inventaire.index'))


@inventaire_bp.route("/modifier_objet/<int:id_objet>", methods=["POST"])
@login_required
def modifier_objet(id_objet):
    objet = db.session.get(Objet, id_objet)
    if not objet or objet.etablissement_id != session['etablissement_id']:
        flash("Objet non trouvé ou accès interdit.", "error")
        return redirect(url_for('inventaire.index'))

    user_id = session.get('user_id')
    etablissement_id = session['etablissement_id']

    # Liste des fichiers à supprimer APRÈS le commit réussi (Race condition fix)
    files_to_cleanup = []

    try:
        # 1. Validation Nom
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom ne peut pas être vide.", "error")
            return redirect(request.referrer)

        # 2. Validation Numérique
        try:
            quantite = int(request.form.get("quantite", 0))
            seuil = int(request.form.get("seuil", 0))
            if quantite < 0 or seuil < 0: raise ValueError
        except ValueError:
            flash("Quantité et seuil doivent être positifs.", "error")
            return redirect(request.referrer)

        # 3. Validation FK
        armoire_id = int(request.form.get("armoire_id", 0))
        categorie_id = int(request.form.get("categorie_id", 0))

        armoire = db.session.get(Armoire, armoire_id)
        if not armoire or armoire.etablissement_id != etablissement_id:
            flash("Armoire invalide.", "error")
            return redirect(request.referrer)

        categorie = db.session.get(Categorie, categorie_id)
        if not categorie or categorie.etablissement_id != etablissement_id:
            flash("Catégorie invalide.", "error")
            return redirect(request.referrer)

        # Capture état avant modif
        anciens = {
            'nom': objet.nom,
            'quantite': objet.quantite_physique,
            'seuil': objet.seuil,
            'armoire': objet.armoire_id,
            'categorie': objet.categorie_id
        }

        # --- GESTION IMAGE ---
        is_image_updated = False
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                file.seek(0, 2)
                if file.tell() > 5 * 1024 * 1024:
                    flash("Image trop volumineuse (Max 5 Mo).", "warning")
                else:
                    file.seek(0)
                    if allowed_file(file.filename):
                        # On marque l'ancien fichier pour suppression future
                        if objet.image_url and objet.image_url.startswith('uploads/'):
                            files_to_cleanup.append(objet.image_url)
                        
                        filename = secure_filename(file.filename)
                        ts = datetime.now().strftime("%Y%m%d%H%M%S")
                        unique_filename = f"{ts}_{filename}"
                        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                        if not os.path.exists(upload_folder): os.makedirs(upload_folder)
                        file.save(os.path.join(upload_folder, unique_filename))
                        
                        objet.image_url = f"uploads/{unique_filename}"
                        is_image_updated = True

        if not is_image_updated:
            url_input = request.form.get("image_url")
            if url_input is not None: # Champ présent
                url_clean = url_input.strip()
                if url_clean:
                    if is_valid_url(url_clean):
                        if objet.image_url and objet.image_url.startswith('uploads/'):
                            files_to_cleanup.append(objet.image_url)
                        objet.image_url = url_clean
                    else:
                        flash("URL image invalide.", "warning")
                else:
                    # Suppression demandée (champ vide)
                    if objet.image_url and objet.image_url.startswith('uploads/'):
                        files_to_cleanup.append(objet.image_url)
                    objet.image_url = None

        # --- GESTION FDS ---
        is_fds_updated = False
        if 'fds_file' in request.files:
            file = request.files['fds_file']
            if file and file.filename != '':
                file.seek(0, 2)
                if file.tell() > 5 * 1024 * 1024:
                    flash("FDS trop volumineuse (Max 5 Mo).", "warning")
                else:
                    file.seek(0)
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
                        flash("URL FDS invalide.", "warning")
                else:
                    if objet.fds_url and objet.fds_url.startswith('uploads/'):
                        files_to_cleanup.append(objet.fds_url)
                    objet.fds_url = None

        # --- MISE À JOUR ---
        objet.nom = nom
        objet.quantite_physique = quantite
        objet.seuil = seuil
        objet.armoire_id = armoire_id
        objet.categorie_id = categorie_id
        objet.date_peremption = request.form.get("date_peremption") or None
        
        # --- HISTORIQUE ---
        details_modif = []
        if anciens['quantite'] != objet.quantite_physique:
            diff = objet.quantite_physique - anciens['quantite']
            signe = "+" if diff > 0 else ""
            details_modif.append(f"Stock: {anciens['quantite']} ➝ {objet.quantite_physique} ({signe}{diff})")
            
        if anciens['nom'] != objet.nom: details_modif.append(f"Nom changé")
        if anciens['armoire'] != objet.armoire_id: details_modif.append("Déplacé (Armoire)")
        if anciens['categorie'] != objet.categorie_id: details_modif.append("Catégorie modifiée")

        if details_modif or anciens['seuil'] != objet.seuil:
            msg = ", ".join(details_modif) if details_modif else "Mise à jour des détails"
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
        
        # --- NETTOYAGE POST-COMMIT (SÉCURISÉ) ---
        for old_path in files_to_cleanup:
            cleanup_old_file(old_path)

        flash(f"L'objet '{objet.nom}' a été mis à jour.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Erreur critique modif objet {id_objet}")
        flash("Une erreur technique est survenue.", "error")

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
    
    # Si l'objet a une catégorie, on l'ajoute pour faciliter la navigation
    if objet.categorie:
        breadcrumbs.append({
            'text': objet.categorie.nom, 
            'url': url_for('inventaire.voir_categorie', categorie_id=objet.categorie.id)
        })
    
    # L'objet lui-même (non cliquable)
    breadcrumbs.append({'text': objet.nom, 'url': None})

    return render_template("objet_details.html",
                           objet=objet,
                           historique=historique,
                           armoires=armoires,
                           categories=categories,
                           breadcrumbs=breadcrumbs,
                           now=datetime.now())

#==============================================================================
#  ROUTE AFFICHAGE ARMOIRES
#==============================================================================
@inventaire_bp.route("/armoire/<int:armoire_id>")
@login_required
def voir_armoire(armoire_id):
    """
    Affiche le contenu d'une armoire.
    CORRIGÉ : Utilise InventoryService.
    """
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    
    armoire = db.session.get(Armoire, armoire_id)
    if not armoire or armoire.etablissement_id != etablissement_id:
        flash("Armoire non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    # Appel Service avec filtre armoire
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

    return render_template("armoire.html",
                           armoire=armoire,
                           objets=dto.items, # DTO
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           autres_armoires=autres_armoires,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=datetime.now(),
                           armoire_id=armoire_id,
                           categorie_id=None
                           )

#==============================================================================
#  ROUTE AFFICHAGE CATEGORIES
#==============================================================================
@inventaire_bp.route("/categorie/<int:categorie_id>")
@login_required
def voir_categorie(categorie_id):
    """
    Affiche le contenu d'une catégorie.
    CORRIGÉ : Utilise InventoryService.
    """
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)

    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')

    categorie = db.session.get(Categorie, categorie_id)
    if not categorie or categorie.etablissement_id != etablissement_id:
        flash("Catégorie non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    # Appel Service avec filtre catégorie
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

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gestion des Catégories', 'url': url_for('main.gestion_categories')},
        {'text': categorie.nom, 'url': None}
    ]

    return render_template("categorie.html",
                           categorie=categorie,
                           objets=dto.items, # DTO
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           categories_list=categories_list,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=datetime.now(),
                           armoire_id=None,
                           categorie_id=categorie_id
                           )
                           
#=======================================================
# ROUTE GESTION ALERTES TRAITEES
#=======================================================
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


#=================================================================
# ROUTE GESTION STOCK DORMANT
#=================================================================
@inventaire_bp.route("/dormants")
@login_required
def objets_dormants():
    etablissement_id = session['etablissement_id']
    service = InventoryService(etablissement_id)
    
    # On récupère les objets non utilisés depuis 1 an (365 jours)
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