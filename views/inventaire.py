# ============================================================
# FICHIER : views/inventaire.py
# ============================================================
import math
import os
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, current_app)
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import joinedload

# IMPORTS DB
from db import db, Objet, Armoire, Categorie, Reservation, Utilisateur, Historique, Echeance, Budget, Depense, Fournisseur, Suggestion

# IMPORTS UTILS
from utils import login_required, admin_required, limit_objets_required, allowed_file

# --- CORRECTION ICI : On importe le Service au lieu de la fonction API ---
from services.inventory_service import InventoryService, InventoryServiceError

inventaire_bp = Blueprint(
    'inventaire', 
    __name__,
    template_folder='../templates'
)

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
    
    reservations = db.session.execute(
        db.select(
            Reservation.groupe_id,
            Reservation.debut_reservation,
            func.count(Reservation.objet_id).label('item_count')
        )
        .filter(
            Reservation.etablissement_id == etablissement_id,
            Reservation.utilisateur_id == user_id,
            Reservation.debut_reservation >= now
        )
        .group_by(Reservation.groupe_id, Reservation.debut_reservation)
        .order_by(Reservation.debut_reservation.asc())
        .limit(5)
    ).mappings().all()
    
    dashboard_data['reservations'] = reservations

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

    recent_reservations = db.session.execute(
        db.select(
            Reservation.groupe_id,
            Reservation.debut_reservation.label('timestamp')
        )
        .filter_by(utilisateur_id=user_id, etablissement_id=etablissement_id)
        .group_by(Reservation.groupe_id, Reservation.debut_reservation)
        .order_by(Reservation.debut_reservation.desc())
        .limit(5)
    ).mappings().all()

    other_actions = db.session.execute(
        db.select(
            Historique.action,
            Historique.timestamp,
            Historique.details,
            Objet.nom.label('objet_nom')
        )
        .join(Objet, Historique.objet_id == Objet.id)
        .filter(
            Historique.utilisateur_id == user_id,
            Historique.etablissement_id == etablissement_id
        )
        .where(Historique.action.notlike('%Réservation%'))
        .order_by(Historique.timestamp.desc())
        .limit(5)
    ).mappings().all()

    all_actions = list(recent_reservations) + list(other_actions)
    all_actions.sort(key=lambda x: x['timestamp'], reverse=True)
    top_5_actions = all_actions[:5]

    historique_enrichi = []
    for action in top_5_actions:
        entry = {'timestamp': action['timestamp']}
        if 'groupe_id' in action: 
            entry['type'] = 'reservation'
            entry['action'] = 'Réservation'
            entry['kits'] = []
            entry['objets_manuels'] = ["Détails en cours de migration..."]
        else: 
            entry['type'] = 'autre'
            entry['action'] = action['action']
            entry['details'] = f"{action['objet_nom']}"
        historique_enrichi.append(entry)

    dashboard_data['historique_recent'] = historique_enrichi
    
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
        image_path_db = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"{ts}_{filename}"
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    file.save(os.path.join(upload_folder, unique_filename))
                    image_path_db = f"uploads/{unique_filename}"
                else:
                    flash("Format d'image non autorisé (JPG, PNG uniquement).", "warning")

        if not image_path_db:
            image_path_db = request.form.get("image_url", "").strip() or None

        new_objet = Objet(
            nom=request.form.get("nom", "").strip(),
            quantite_physique=int(request.form.get("quantite")),
            seuil=int(request.form.get("seuil")),
            armoire_id=int(request.form.get("armoire_id")),
            categorie_id=int(request.form.get("categorie_id")),
            date_peremption=request.form.get("date_peremption") or None,
            image_url=image_path_db,
            fds_url=request.form.get("fds_url", "").strip() or None,
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
        flash("Données invalides. Veuillez vérifier les champs numériques.", "error")
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
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    user_id = session.get('user_id')
    etablissement_id = session['etablissement_id']

    try:
        anciens = {
            'nom': objet.nom,
            'quantite': objet.quantite_physique,
            'seuil': objet.seuil,
            'armoire': objet.armoire_id,
            'categorie': objet.categorie_id
        }

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"{ts}_{filename}"
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    file.save(os.path.join(upload_folder, unique_filename))
                    objet.image_url = f"uploads/{unique_filename}"
                else:
                    flash("Format d'image non autorisé.", "warning")
        
        url_externe = request.form.get("image_url", "").strip()
        if url_externe:
            objet.image_url = url_externe

        objet.nom = request.form.get("nom", "").strip()
        objet.quantite_physique = int(request.form.get("quantite"))
        objet.seuil = int(request.form.get("seuil"))
        objet.armoire_id = int(request.form.get("armoire_id"))
        objet.categorie_id = int(request.form.get("categorie_id"))
        objet.date_peremption = request.form.get("date_peremption") or None
        objet.fds_url = request.form.get("fds_url", "").strip() or None
        
        details_modif = []
        if anciens['quantite'] != objet.quantite_physique:
            diff = objet.quantite_physique - anciens['quantite']
            signe = "+" if diff > 0 else ""
            details_modif.append(f"Stock: {anciens['quantite']} ➝ {objet.quantite_physique} ({signe}{diff})")
            
        if anciens['nom'] != objet.nom:
            details_modif.append(f"Nom changé")
            
        if anciens['armoire'] != objet.armoire_id:
            details_modif.append("Déplacé (Armoire)")

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
        flash(f"L'objet '{objet.nom}' a été mis à jour avec succès !", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modif objet: {e}")
        flash(f"Une erreur est survenue.", "error")

    return redirect(request.referrer or url_for('inventaire.index'))


@inventaire_bp.route("/objet/supprimer/<int:id_objet>", methods=["POST"])
@admin_required
def supprimer_objet(id_objet):
    objet = db.session.get(Objet, id_objet)
    if not objet or objet.etablissement_id != session['etablissement_id']:
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.inventaire'))

    try:
        nom_objet = objet.nom
        hist = Historique(
            objet_id=None, 
            utilisateur_id=session.get('user_id'),
            action="Suppression",
            details=f"Suppression définitive de : {nom_objet}",
            etablissement_id=session['etablissement_id'],
            timestamp=datetime.now()
        )
        db.session.add(hist)
        
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

    return render_template("objet_details.html",
                           objet=objet,
                           historique=historique,
                           armoires=armoires,
                           categories=categories,
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
                           now=datetime.now(),
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
                           now=datetime.now(),
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