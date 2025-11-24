# views/api.py

import os
import math
import uuid
from datetime import date, datetime, timedelta
import requests
from flask import Blueprint, jsonify, request, session, render_template, current_app, flash
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload
from db import db, Objet, Reservation, Utilisateur, Kit, KitObjet, Categorie, Armoire
from utils import login_required, admin_required

api_bp = Blueprint(
    'api', 
    __name__,
    url_prefix='/api'
)

# ============================================================
# === API PEXELS (INCHANGÉ)
# ============================================================
@api_bp.route("/search-images")
@login_required
def search_pexels_images():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Le terme de recherche est manquant."}), 400
    api_key = os.environ.get('PEXELS_API_KEY')
    if not api_key:
        return jsonify({"error": "La clé d'API Pexels n'est pas configurée sur le serveur."}), 500
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=15&locale=fr-FR"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        images = [{"id": p["id"], "photographer": p["photographer"], "small_url": p["src"]["medium"], "large_url": p["src"]["large2x"]} for p in data.get("photos", [])]
        return jsonify(images)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erreur de communication avec l'API Pexels: {e}"}), 503


# ============================================================
# === API POUR L'INVENTAIRE (INCHANGÉ)
# ============================================================
def get_paginated_objets(etablissement_id, page, sort_by='nom', direction='asc', search_query=None, armoire_id=None, categorie_id=None, etat=None):
    items_per_page = 10
    offset = (page - 1) * items_per_page
    now = datetime.now()

    subquery = db.session.query(
        Reservation.objet_id,
        func.sum(Reservation.quantite_reservee).label('total_reserve')
    ).filter(
        Reservation.etablissement_id == etablissement_id,
        Reservation.fin_reservation > now
    ).group_by(Reservation.objet_id).subquery()

    query = db.session.query(
        Objet,
        Armoire.nom.label('armoire_nom'),
        Categorie.nom.label('categorie_nom'),
        (Objet.quantite_physique - func.coalesce(subquery.c.total_reserve, 0)).label('quantite_disponible')
    ).join(Armoire, Objet.armoire_id == Armoire.id)\
     .join(Categorie, Objet.categorie_id == Categorie.id)\
     .outerjoin(subquery, Objet.id == subquery.c.objet_id)\
     .filter(Objet.etablissement_id == etablissement_id)

    if search_query:
        query = query.filter(Objet.nom.ilike(f"%{search_query}%"))
    if armoire_id:
        query = query.filter(Objet.armoire_id == armoire_id)
    if categorie_id:
        query = query.filter(Objet.categorie_id == categorie_id)
    
    total_items = query.count()
    total_pages = math.ceil(total_items / items_per_page) if items_per_page > 0 else 0

    sort_map = {
        'nom': Objet.nom, 'quantite': 'quantite_disponible', 'seuil': Objet.seuil,
        'date_peremption': Objet.date_peremption, 'categorie': 'categorie_nom', 'armoire': 'armoire_nom'
    }
    sort_column = sort_map.get(sort_by, Objet.nom)
    
    if direction == 'desc':
        query = query.order_by(db.desc(sort_column))
    else:
        query = query.order_by(db.asc(sort_column))

    results = query.limit(items_per_page).offset(offset).all()
    
    objets = []
    for row in results:
        obj_dict = {c.name: getattr(row.Objet, c.name) for c in row.Objet.__table__.columns}
        obj_dict['armoire'] = row.armoire_nom
        obj_dict['categorie'] = row.categorie_nom
        obj_dict['quantite_disponible'] = row.quantite_disponible
        objets.append(obj_dict)

    return objets, total_pages


@api_bp.route("/inventaire/")
@login_required
def api_inventaire():
    etablissement_id = session['etablissement_id']
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    search_query = request.args.get('q', None)
    armoire_id = request.args.get('armoire', None)
    categorie_id = request.args.get('categorie', None)
    etat = request.args.get('etat', None)

    objets, total_pages = get_paginated_objets(
        etablissement_id, page, sort_by, direction, search_query, armoire_id, categorie_id, etat
    )

    pagination = {
        'page': page,
        'total_pages': total_pages,
        'endpoint': 'inventaire.inventaire'
    }

    html = render_template('_inventaire_content.html', 
                           objets=objets, 
                           pagination=pagination, 
                           date_actuelle=datetime.now(), 
                           sort_by=sort_by, 
                           direction=direction, 
                           session=session)
    
    return jsonify(html=html)


#===============================================
# LOGIQUE DEPLACER OBJET (INCHANGÉ)
#===============================================
@api_bp.route("/deplacer_objets", methods=['POST'])
@admin_required
def deplacer_objets():
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    objet_ids = data.get('objet_ids')
    destination_id = data.get('destination_id')
    type_destination = data.get('type_destination')

    if not all([objet_ids, destination_id, type_destination]):
        return jsonify(success=False, error="Données manquantes."), 400

    try:
        field_to_update = 'categorie_id' if type_destination == 'categorie' else 'armoire_id'
        db.session.execute(
            db.update(Objet)
            .where(Objet.id.in_(objet_ids), Objet.etablissement_id == etablissement_id)
            .values({field_to_update: destination_id})
        )
        db.session.commit()
        flash(f"{len(objet_ids)} objet(s) déplacé(s) avec succès.", "success")
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


# =========================================================================
# CALENDRIER MENSUEL (INCHANGÉ)
# =========================================================================
@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    etablissement_id = session.get('etablissement_id')
    if not etablissement_id:
        return jsonify({"error": "Non autorisé"}), 403
    try:
        start_date = date(year, month, 1)
        end_date = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
        jours_reserves = db.session.execute(
            db.select(func.date(Reservation.debut_reservation))
            .filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation >= start_date,
                Reservation.debut_reservation < end_date
            ).distinct()
        ).scalars().all()
        reservations_par_jour = {jour.strftime('%Y-%m-%d'): [{'placeholder': True}] for jour in jours_reserves}
        return jsonify(reservations_par_jour)
    except Exception as e:
        current_app.logger.error(f"Erreur API reservations_par_mois : {e}")
        return jsonify({"error": str(e)}), 500


# ========================================================================
# === SECTION RÉSERVATION (ENTIÈREMENT REFACTORISÉE)
# ========================================================================

def _get_reserved_quantities(etablissement_id, start_dt, end_dt, exclude_group_id=None):
    """
    NOUVELLE FONCTION CENTRALE : Calcule les quantités totales d'objets réservés
    qui empiètent sur un créneau horaire donné.
    Utilise la logique de chevauchement correcte pour une fiabilité maximale.
    """
    # La réservation existante (res) chevauche le créneau demandé (req) si :
    # res.debut < req.fin ET res.fin > req.debut
    overlap_filter = and_(
        Reservation.etablissement_id == etablissement_id,
        Reservation.debut_reservation < end_dt,
        Reservation.fin_reservation > start_dt
    )

    # Si on modifie une réservation, on l'exclut du calcul pour ne pas qu'elle se bloque elle-même
    if exclude_group_id:
        overlap_filter = and_(overlap_filter, Reservation.groupe_id != exclude_group_id)

    # Requête qui somme les quantités réservées pour chaque objet concerné
    reserved_objets_query = db.session.query(
        Reservation.objet_id,
        func.sum(Reservation.quantite_reservee).label('total_reserved')
    ).filter(overlap_filter, Reservation.objet_id.isnot(None)).group_by(Reservation.objet_id)
    
    # Retourne un dictionnaire pratique : {objet_id: quantite_reservee}
    return {item.objet_id: item.total_reserved for item in reserved_objets_query.all()}


@api_bp.route("/disponibilites") # ANCIENNEMENT /reservation_data
@login_required
def api_get_disponibilites():
    etablissement_id = session.get('etablissement_id')
    
    date_str = request.args.get('date')
    heure_debut_str = request.args.get('heure_debut')
    heure_fin_str = request.args.get('heure_fin')
    exclude_group_id = request.args.get('exclude_group_id')

    if not all([date_str, heure_debut_str, heure_fin_str]):
        return jsonify({"error": "Paramètres manquants"}), 400

    try:
        debut_resa = datetime.strptime(f"{date_str} {heure_debut_str}", '%Y-%m-%d %H:%M')
        fin_resa = datetime.strptime(f"{date_str} {heure_fin_str}", '%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return jsonify({"error": "Format de date ou d'heure invalide"}), 400

    # 1. Obtenir toutes les quantités déjà réservées sur ce créneau
    reserved_quantities = _get_reserved_quantities(etablissement_id, debut_resa, fin_resa, exclude_group_id)

    # 2. Calculer la disponibilité pour chaque objet
    all_objets = db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars().all()
    objets_disponibles = []
    objets_map = {} # Pour un accès rapide lors du calcul des kits
    for objet in all_objets:
        reserved = reserved_quantities.get(objet.id, 0)
        disponible = objet.quantite_physique - reserved
        obj_data = {
            'id': objet.id, 'nom': objet.nom, 
            'quantite_disponible': max(0, disponible)
        }
        objets_disponibles.append(obj_data)
        objets_map[objet.id] = obj_data

    # 3. Calculer la disponibilité pour chaque kit en se basant sur ses composants
    all_kits = db.session.execute(db.select(Kit).filter_by(etablissement_id=etablissement_id).options(joinedload(Kit.objets_assoc))).unique().scalars().all()
    kits_disponibles = []
    for kit in all_kits:
        # La dispo d'un kit est le nombre de fois qu'on peut le composer avec les objets restants
        disponibilite_kit = float('inf')
        if not kit.objets_assoc:
            disponibilite_kit = 0
        else:
            for assoc in kit.objets_assoc:
                objet_data = objets_map.get(assoc.objet_id)
                # Si un objet du kit n'existe pas ou que sa quantité requise est 0, le kit n'est pas composable
                if not objet_data or assoc.quantite == 0:
                    disponibilite_kit = 0
                    break
                # Combien de kits peut-on faire avec cet objet ?
                kits_possibles = objet_data['quantite_disponible'] // assoc.quantite
                # On garde la valeur la plus faible, car c'est le composant limitant
                disponibilite_kit = min(disponibilite_kit, kits_possibles)
        
        kits_disponibles.append({
            'id': kit.id, 'nom': kit.nom, 'description': kit.description,
            'disponible': disponibilite_kit if disponibilite_kit != float('inf') else 0
        })

    # Le JS attend un format simple : une liste d'objets et une liste de kits
    return jsonify({'objets': objets_disponibles, 'kits': kits_disponibles})


@api_bp.route("/valider_panier", methods=['POST'])
@login_required
def api_valider_panier():
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    cart_data = request.get_json()

    if not cart_data:
        return jsonify({"success": False, "error": "Le panier est vide."}), 400

    try:
        # --- ÉTAPE 1 : Agréger tous les objets requis (identique à votre code) ---
        objets_requis_par_creneau = {}
        for creneau_key, creneau_data in cart_data.items():
            objets_requis = {}
            if 'kits' in creneau_data:
                for kit_id, kit_info in creneau_data['kits'].items():
                    kit = db.session.get(Kit, int(kit_id))
                    if not kit: continue
                    for assoc in kit.objets_assoc:
                        quantite_necessaire = assoc.quantite * kit_info['quantite']
                        objets_requis[assoc.objet_id] = objets_requis.get(assoc.objet_id, 0) + quantite_necessaire
            if 'objets' in creneau_data:
                for objet_id, objet_info in creneau_data['objets'].items():
                    objets_requis[int(objet_id)] = objets_requis.get(int(objet_id), 0) + objet_info['quantite']
            objets_requis_par_creneau[creneau_key] = objets_requis

        # --- ÉTAPE 2 : VÉRIFICATION DE DISPONIBILITÉ (LOGIQUE CORRIGÉE) ---
        for creneau_key, objets_requis in objets_requis_par_creneau.items():
            creneau_data = cart_data[creneau_key]
            debut_resa = datetime.strptime(f"{creneau_data['date']} {creneau_data['heure_debut']}", '%Y-%m-%d %H:%M')
            fin_resa = datetime.strptime(f"{creneau_data['date']} {creneau_data['heure_fin']}", '%Y-%m-%d %H:%M')

            # On utilise notre nouvelle fonction fiable
            reserved_quantities = _get_reserved_quantities(etablissement_id, debut_resa, fin_resa)

            for objet_id, quantite_demandee in objets_requis.items():
                if quantite_demandee <= 0: continue
                objet = db.session.get(Objet, objet_id)
                if not objet:
                    return jsonify({"success": False, "error": f"Un objet demandé n'existe plus."}), 400

                deja_reserve = reserved_quantities.get(objet_id, 0)
                disponible = objet.quantite_physique - deja_reserve
                
                if quantite_demandee > disponible:
                    return jsonify({"success": False, "error": f"Stock insuffisant pour '{objet.nom}' sur le créneau {creneau_data['heure_debut']}-{creneau_data['heure_fin']}. Demandé: {quantite_demandee}, Disponible: {disponible}."}), 400

        # --- ÉTAPE 3 : Création des réservations (identique à votre code) ---
        for creneau_key, creneau_data in cart_data.items():
            groupe_id = str(uuid.uuid4())
            debut_resa = datetime.strptime(f"{creneau_data['date']} {creneau_data['heure_debut']}", '%Y-%m-%d %H:%M')
            fin_resa = datetime.strptime(f"{creneau_data['date']} {creneau_data['heure_fin']}", '%Y-%m-%d %H:%M')

            reservations_a_creer = {}
            if 'kits' in creneau_data:
                for kit_id, kit_info in creneau_data['kits'].items():
                    kit = db.session.get(Kit, int(kit_id))
                    if not kit: continue
                    for assoc in kit.objets_assoc:
                        key = (assoc.objet_id, kit.id)
                        quantite_a_ajouter = assoc.quantite * kit_info['quantite']
                        reservations_a_creer[key] = reservations_a_creer.get(key, 0) + quantite_a_ajouter
            if 'objets' in creneau_data:
                for objet_id, objet_info in creneau_data['objets'].items():
                    key = (int(objet_id), None)
                    reservations_a_creer[key] = reservations_a_creer.get(key, 0) + objet_info['quantite']

            for (objet_id, kit_id), quantite_totale in reservations_a_creer.items():
                if quantite_totale > 0:
                    db.session.add(Reservation(objet_id=objet_id, utilisateur_id=user_id, quantite_reservee=quantite_totale, debut_reservation=debut_resa, fin_reservation=fin_resa, groupe_id=groupe_id, kit_id=kit_id, etablissement_id=etablissement_id))
        
        db.session.commit()
        flash("Toutes vos réservations ont été confirmées avec succès !", "success")
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur critique lors de la validation du panier : {e}")
        return jsonify({"success": False, "error": "Une erreur interne est survenue. Veuillez réessayer."}), 500


@api_bp.route("/creer_reservation", methods=['POST'])
@login_required
def api_creer_reservation():
    """
    Route dédiée pour la modale de réservation (booking-modal.js)
    Format attendu: {date, heure_debut, heure_fin, items: [{type, id, name, quantity}], groupe_id}
    """
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Données manquantes."}), 400

    try:
        # Extraction des données
        date_str = data.get('date')
        heure_debut = data.get('heure_debut')
        heure_fin = data.get('heure_fin')
        items = data.get('items', [])
        groupe_id = data.get('groupe_id')  # None pour création, défini pour modification

        if not all([date_str, heure_debut, heure_fin]):
            return jsonify({"success": False, "error": "Paramètres manquants."}), 400

        debut_resa = datetime.strptime(f"{date_str} {heure_debut}", '%Y-%m-%d %H:%M')
        fin_resa = datetime.strptime(f"{date_str} {heure_fin}", '%Y-%m-%d %H:%M')

        # --- ÉTAPE 1 : Calculer les objets requis depuis les items ---
        objets_requis = {}
        
        for item in items:
            if item['type'] == 'kit':
                kit = db.session.get(Kit, item['id'])
                if kit:
                    for assoc in kit.objets_assoc:
                        objets_requis[assoc.objet_id] = objets_requis.get(assoc.objet_id, 0) + (assoc.quantite * item['quantity'])
            elif item['type'] == 'objet':
                objets_requis[item['id']] = objets_requis.get(item['id'], 0) + item['quantity']

        # --- ÉTAPE 2 : Vérifier la disponibilité ---
        reserved_quantities = _get_reserved_quantities(
            etablissement_id, 
            debut_resa, 
            fin_resa, 
            exclude_group_id=groupe_id  # Exclure si modification
        )

        for objet_id, quantite_demandee in objets_requis.items():
            if quantite_demandee <= 0:
                continue
            
            objet = db.session.get(Objet, objet_id)
            if not objet:
                return jsonify({"success": False, "error": f"Un objet demandé n'existe plus."}), 400

            deja_reserve = reserved_quantities.get(objet_id, 0)
            disponible = objet.quantite_physique - deja_reserve
            
            if quantite_demandee > disponible:
                return jsonify({
                    "success": False, 
                    "error": f"Stock insuffisant pour '{objet.nom}'. Demandé: {quantite_demandee}, Disponible: {disponible}."
                }), 400

        # --- ÉTAPE 3 : Suppression de l'ancienne réservation si modification ---
        if groupe_id:
            # Vérification des permissions
            resa_existante = db.session.execute(
                db.select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
            ).scalars().first()
            
            if not resa_existante:
                return jsonify({"success": False, "error": "Réservation non trouvée."}), 404
            
            if session.get('user_role') != 'admin' and resa_existante.utilisateur_id != user_id:
                return jsonify({"success": False, "error": "Permissions insuffisantes."}), 403
            
            # Suppression de toutes les réservations du groupe
            db.session.execute(db.delete(Reservation).where(Reservation.groupe_id == groupe_id))
        else:
            # Création : générer un nouveau groupe_id
            groupe_id = str(uuid.uuid4())

        # --- ÉTAPE 4 : Création des nouvelles réservations ---
        reservations_a_creer = {}
        
        for item in items:
            if item['type'] == 'kit':
                kit = db.session.get(Kit, item['id'])
                if kit:
                    for assoc in kit.objets_assoc:
                        key = (assoc.objet_id, kit.id)
                        reservations_a_creer[key] = reservations_a_creer.get(key, 0) + (assoc.quantite * item['quantity'])
            elif item['type'] == 'objet':
                key = (item['id'], None)
                reservations_a_creer[key] = reservations_a_creer.get(key, 0) + item['quantity']

        # Insertion des réservations
        for (objet_id, kit_id), quantite_totale in reservations_a_creer.items():
            if quantite_totale > 0:
                db.session.add(Reservation(
                    objet_id=objet_id,
                    utilisateur_id=user_id,
                    quantite_reservee=quantite_totale,
                    debut_reservation=debut_resa,
                    fin_reservation=fin_resa,
                    groupe_id=groupe_id,
                    kit_id=kit_id,
                    etablissement_id=etablissement_id
                ))

        db.session.commit()
        
        message = "Réservation modifiée avec succès !" if data.get('groupe_id') else "Réservation créée avec succès !"
        flash(message, "success")
        return jsonify({"success": True, "message": message})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur lors de la création/modification de la réservation : {e}")
        return jsonify({"success": False, "error": "Une erreur interne est survenue."}), 500

# ============================================================
# AFFICHER LES DÉTAILS D'UNE RÉSERVATION (INCHANGÉ)
# ============================================================
@api_bp.route("/reservation_details/<groupe_id>")
@login_required
def api_reservation_details(groupe_id):
    etablissement_id = session.get('etablissement_id')
    reservations = db.session.execute(db.select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id).options(joinedload(Reservation.objet), joinedload(Reservation.kit))).scalars().all()
    if not reservations:
        return jsonify({'error': 'Réservation non trouvée'}), 404
    first_resa = reservations[0]
    user = db.session.get(Utilisateur, first_resa.utilisateur_id)
    details = {'kits': {}, 'objets_manuels': [], 'nom_utilisateur': user.nom_utilisateur if user else 'Inconnu', 'utilisateur_id': first_resa.utilisateur_id, 'debut_reservation': first_resa.debut_reservation.isoformat(), 'fin_reservation': first_resa.fin_reservation.isoformat()}
    objets_manuels_bruts = [r for r in reservations if r.kit_id is None]
    objets_kits_reserves = [r for r in reservations if r.kit_id is not None]
    kits_comptes = {}
    for r in objets_kits_reserves:
        if r.kit_id not in kits_comptes:
            kits_comptes[r.kit_id] = {'nom': r.kit.nom, 'objets_reserves': {}}
        kits_comptes[r.kit_id]['objets_reserves'][r.objet_id] = r.quantite_reservee
    for kit_id, data in kits_comptes.items():
        kit_complet = db.session.get(Kit, kit_id)
        if not kit_complet or not kit_complet.objets_assoc: continue
        first_assoc = kit_complet.objets_assoc[0]
        quantite_par_kit = first_assoc.quantite
        if quantite_par_kit > 0 and first_assoc.objet_id in data['objets_reserves']:
            quantite_reelle_reservee = data['objets_reserves'][first_assoc.objet_id]
            nombre_de_kits = quantite_reelle_reservee // quantite_par_kit
            details['kits'][str(kit_id)] = {'quantite': nombre_de_kits, 'nom': data['nom']}
    for resa in objets_manuels_bruts:
        details['objets_manuels'].append({'objet_id': resa.objet_id, 'nom': resa.objet.nom, 'quantite_reservee': resa.quantite_reservee})
    return jsonify(details)

        
# ============================================================
# --- SUPPRIMER UNE RESERVATION (INCHANGÉ) ---
# ============================================================
@api_bp.route("/supprimer_reservation", methods=['POST'])
@login_required
def api_supprimer_reservation():
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    data = request.get_json()
    groupe_id = data.get("groupe_id")

    if not groupe_id:
        return jsonify({"success": False, "error": "ID de groupe manquant."}), 400

    try:
        reservation_a_supprimer = db.session.execute(db.select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)).scalars().first()
        if not reservation_a_supprimer:
            return jsonify(success=False, error="Réservation non trouvée."), 404
        if session.get('user_role') != 'admin' and reservation_a_supprimer.utilisateur_id != user_id:
            return jsonify(success=False, error="Vous n'avez pas la permission de supprimer cette réservation."), 403
        
        db.session.execute(db.delete(Reservation).where(Reservation.groupe_id == groupe_id))
        db.session.commit()
        
        flash("La réservation a été annulée.", "success")
        return jsonify(success=True)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur lors de la suppression de la réservation : {e}")
        return jsonify(success=False, error=str(e)), 500


# =============================================================
# API FONCTION RECHERCHER UN OBJET
# =============================================================
@api_bp.route("/rechercher")
@login_required
def rechercher_objets():
    etablissement_id = session.get('etablissement_id')
    query = request.args.get('q', '').strip()

    if not etablissement_id or len(query) < 2:
        return jsonify([]) # Retourne une liste vide si la requête est trop courte ou si non connecté

    search_term = f"%{query}%"
    
    objets = db.session.execute(
        db.select(
            Objet.id,
            Objet.nom,
            Armoire.nom.label('armoire_nom'),
            Categorie.nom.label('categorie_nom')
        )
        .join(Armoire, Objet.armoire_id == Armoire.id)
        .join(Categorie, Objet.categorie_id == Categorie.id)
        .filter(
            Objet.etablissement_id == etablissement_id,
            Objet.nom.ilike(search_term)
        )
        .limit(5) # On limite à 5 résultats pour la performance
    ).mappings().all()

    return jsonify([dict(row) for row in objets])