# Fichier: views/api.py (Version Finale Corrigée)

import os
# DANS views/api.py
import math
from datetime import date, datetime, timedelta
import requests
from flask import Blueprint, jsonify, request, session, render_template
from sqlalchemy import func

# NOUVEAUX IMPORTS
from db import db, Objet, Reservation, Utilisateur, Kit, KitObjet, Categorie, Armoire
from utils import login_required, admin_required

api_bp = Blueprint(
    'api', 
    __name__,
    url_prefix='/api'
)


# --- GESTION RECHERCHE IMAGES PEXELS ---
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

# --- AFFICHAGE DU CALENDRIER ---
@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    etablissement_id = session['etablissement_id']

    # On calcule les dates de début et de fin du mois demandé
    try:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
    except ValueError:
        return jsonify({"error": "Date invalide"}), 400

    reservations = db.session.execute(
        db.select(
            func.date(Reservation.debut_reservation).label('jour_reservation'),
            Reservation.groupe_id,
            Reservation.utilisateur_id
        )
        .filter(
            Reservation.etablissement_id == etablissement_id,
            Reservation.debut_reservation >= start_date,
            Reservation.debut_reservation < end_date,
            Reservation.groupe_id != None
        )
        .group_by('jour_reservation', Reservation.groupe_id, Reservation.utilisateur_id)
    ).mappings().all()

    results = {}
    for row in reservations:
        date_str = row['jour_reservation'].strftime('%Y-%m-%d')
        if date_str not in results:
            results[date_str] = []
        
        results[date_str].append({
            'is_mine': row['utilisateur_id'] == session['user_id']
        })
    
    return jsonify(results)

# ============================================================
# NOUVELLE FONCTION DE PAGINATION (SQLAlchemy)
# ============================================================
def get_paginated_objets(etablissement_id, page, sort_by='nom', direction='asc', search_query=None, armoire_id=None, categorie_id=None, etat=None):
    items_per_page = 10 # NOTE: À remplacer par une lecture des paramètres de l'établissement
    offset = (page - 1) * items_per_page
    now = datetime.now()

    # Sous-requête pour calculer la quantité disponible
    subquery = db.session.query(
        Reservation.objet_id,
        func.sum(Reservation.quantite_reservee).label('total_reserve')
    ).filter(
        Reservation.etablissement_id == etablissement_id,
        Reservation.fin_reservation > now
    ).group_by(Reservation.objet_id).subquery()

    # Requête de base, FILTRÉE PAR ÉTABLISSEMENT
    query = db.session.query(
        Objet,
        Armoire.nom.label('armoire_nom'),
        Categorie.nom.label('categorie_nom'),
        (Objet.quantite_physique - func.coalesce(subquery.c.total_reserve, 0)).label('quantite_disponible')
    ).join(Armoire, Objet.armoire_id == Armoire.id)\
     .join(Categorie, Objet.categorie_id == Categorie.id)\
     .outerjoin(subquery, Objet.id == subquery.c.objet_id)\
     .filter(Objet.etablissement_id == etablissement_id)

    # Application des filtres
    if search_query:
        query = query.filter(Objet.nom.ilike(f"%{search_query}%"))
    if armoire_id:
        query = query.filter(Objet.armoire_id == armoire_id)
    if categorie_id:
        query = query.filter(Objet.categorie_id == categorie_id)
    
    # Comptage du total AVANT le tri et la pagination
    total_items = query.count()
    total_pages = math.ceil(total_items / items_per_page) if items_per_page > 0 else 0

    # Tri
    sort_map = {
        'nom': Objet.nom, 'quantite': 'quantite_disponible', 'seuil': Objet.seuil,
        'date_peremption': Objet.date_peremption, 'categorie': 'categorie_nom', 'armoire': 'armoire_nom'
    }
    sort_column = sort_map.get(sort_by, Objet.nom)
    
    if direction == 'desc':
        query = query.order_by(db.desc(sort_column))
    else:
        query = query.order_by(db.asc(sort_column))

    # Pagination finale
    results = query.limit(items_per_page).offset(offset).all()
    
    # On transforme les résultats en une liste de dictionnaires que le template peut utiliser
    objets = []
    for row in results:
        obj_dict = {c.name: getattr(row.Objet, c.name) for c in row.Objet.__table__.columns}
        obj_dict['armoire'] = row.armoire_nom
        obj_dict['categorie'] = row.categorie_nom
        obj_dict['quantite_disponible'] = row.quantite_disponible
        objets.append(obj_dict)

    return objets, total_pages

#===========================================================================
# ROUTE TRI DYNAMIQUE TABLEAU INVENTAIRE
#===========================================================================
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

    # On rend uniquement le "morceau" de template qui contient le tableau
    html = render_template('_inventaire_content.html', 
                           objets=objets, 
                           pagination=pagination, 
                           date_actuelle=datetime.now(), 
                           sort_by=sort_by, 
                           direction=direction, 
                           session=session)
    
    return jsonify(html=html)

#===============================================
# LOGIQUE DEPLACER OBJET DANS AUTRE ARMOIRE
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

        # Requête de mise à jour en masse, plus efficace qu'une boucle
        db.session.execute(
            db.update(Objet)
            .where(
                Objet.id.in_(objet_ids),
                Objet.etablissement_id == etablissement_id # Sécurité : on ne déplace que les objets de l'établissement
            )
            .values({field_to_update: destination_id})
        )
        db.session.commit()
        
        flash(f"{len(objet_ids)} objet(s) déplacé(s) avec succès.", "success")
        return jsonify(success=True)
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500