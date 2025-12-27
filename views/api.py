# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import NamedTuple
from flask import Blueprint, request, jsonify, session, current_app, render_template
from werkzeug.exceptions import BadRequest

# Imports locaux
from db import db, Objet, Armoire, Categorie, Utilisateur, Reservation, Kit, KitObjet, Suggestion
from extensions import limiter
from utils import login_required

# --- SERVICES ---
from services.stock_service import StockService, StockServiceError
from services.panier_service import PanierService, PanierServiceError
from services.inventory_service import InventoryService, InventoryServiceError
from sqlalchemy import func, select

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ============================================================
# STRUCTURES DE DONNÉES
# ============================================================

class Services(NamedTuple):
    stock: StockService
    panier: PanierService
    inventory: InventoryService

# ============================================================
# SÉCURITÉ & UTILITAIRES
# ============================================================

@api_bp.before_request
def validate_json_content_type():
    """
    Valide le Content-Type pour les requêtes mutantes.
    Note: Le CSRF est géré par Flask-WTF (cookie csrf_token + header X-CSRFToken ou form data).
    """
    if request.method in ['POST', 'PUT']:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 415

def get_services() -> Services:
    """Factory sécurisée retournant un NamedTuple."""
    user_id = session.get('user_id')
    etablissement_id = session.get('etablissement_id')

    if not user_id or not etablissement_id:
        raise ValueError("Session invalide")

    user = db.session.get(Utilisateur, user_id)
    if not user or user.etablissement_id != etablissement_id:
        current_app.logger.critical(
            f"SECURITY: IDOR Attempt. User {user_id} -> Etab {etablissement_id} "
            f"on {request.endpoint} ({request.method})"
        )
        raise ValueError("Session invalide : Incohérence établissement")

    return Services(
        stock=StockService(etablissement_id),
        panier=PanierService(etablissement_id),
        inventory=InventoryService(etablissement_id)
    )

def _parse_request_dates(date_str, h_debut, h_fin):
    """Parsing basique."""
    if not date_str or not h_debut or not h_fin:
        raise ValueError("Paramètres date/heure manquants")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        t_start = datetime.strptime(h_debut, "%H:%M").time()
        t_end = datetime.strptime(h_fin, "%H:%M").time()
        return datetime.combine(d, t_start), datetime.combine(d, t_end)
    except ValueError:
        raise ValueError("Format date/heure invalide")

def _validate_simulated_cart(cart_data):
    """Valide la structure du panier simulé."""
    if not isinstance(cart_data, list):
        raise ValueError("Le panier doit être une liste")
    if len(cart_data) > PanierService.MAX_ITEMS_PANIER:
        raise ValueError("Panier trop volumineux")
    
    for item in cart_data:
        if not isinstance(item, dict):
            raise ValueError("Item malformé")
        
        if not all(k in item for k in ('type', 'id')):
            raise ValueError("Champs type/id manquants")
            
        if 'quantite' not in item and 'quantity' not in item:
             raise ValueError("Quantité manquante")

# ============================================================
# GESTION D'ERREURS CENTRALISÉE
# ============================================================

@api_bp.errorhandler(StockServiceError)
@api_bp.errorhandler(PanierServiceError)
@api_bp.errorhandler(InventoryServiceError)
def handle_business_error(error):
    return jsonify({"success": False, "error": str(error), "code": "BUSINESS_ERROR"}), 400

@api_bp.errorhandler(ValueError)
@api_bp.errorhandler(BadRequest)
def handle_validation_error(error):
    msg = str(error) if isinstance(error, ValueError) else "JSON malformé ou invalide"
    return jsonify({"success": False, "error": msg, "code": "VALIDATION_ERROR"}), 400

# ============================================================
# 1. GESTION DU PANIER
# ============================================================

@api_bp.route("/panier", methods=['GET'])
@login_required
@limiter.limit("120 per minute")
def get_panier():
    services = get_services()
    contenu = services.panier.get_contenu(session['user_id'])
    return jsonify({"success": True, "data": contenu})

@api_bp.route("/panier/ajouter", methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def ajouter_item_panier():
    services = get_services()
    data = request.get_json()
    result = services.panier.ajouter_item(session['user_id'], data)
    return jsonify({"success": True, "data": result}), 201

@api_bp.route("/panier/retirer/<int:item_id>", methods=['DELETE'])
@login_required
def retirer_item_panier(item_id):
    services = get_services()
    services.panier.retirer_item(session['user_id'], item_id)
    return jsonify({"success": True}), 200

@api_bp.route("/panier", methods=['DELETE'])
@login_required
def vider_panier():
    services = get_services()
    services.panier.vider_panier(session['user_id'])
    return jsonify({"success": True}), 200

@api_bp.route("/panier/checkout", methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def checkout_panier():
    services = get_services()
    user_id = session['user_id']
    
    try:
        result = services.panier.valider_panier(user_id)
        current_app.logger.info(f"API CHECKOUT SUCCESS | User {user_id} | Group {result['groupe_id']}")
        return jsonify({"success": True, "data": result}), 201
    except (PanierServiceError, StockServiceError) as e:
        current_app.logger.warning(f"API CHECKOUT BUSINESS ERROR | User {user_id} | {e}")
        raise
    except Exception as e:
        current_app.logger.error(f"API CHECKOUT CRITICAL ERROR | User {user_id} | {e}", exc_info=True)
        # Correction Wording : Paiement -> Validation
        return jsonify({"success": False, "error": "Erreur technique lors de la validation"}), 500

# ============================================================
# 2. DISPONIBILITÉS
# ============================================================

@api_bp.route("/disponibilites", methods=['GET'])
@login_required
def api_disponibilites():
    services = get_services()
    
    start_dt, end_dt = _parse_request_dates(
        request.args.get('date'), 
        request.args.get('heure_debut'), 
        request.args.get('heure_fin')
    )

    # 1. On récupère le panier ACTUEL de l'utilisateur (Server Side)
    # Pour que le stock affiché tienne compte de ce qu'il a déjà mis dans son panier
    items_a_deduire = []
    
    try:
        # On récupère le contenu brut
        contenu_panier = services.panier.get_contenu(session['user_id'])
        
        # On le transforme en format simple pour StockService
        if contenu_panier and 'items' in contenu_panier:
            for item in contenu_panier['items']:
                # On ne déduit que les items qui chevauchent le créneau demandé ?
                # Pour simplifier l'UX : on déduit tout ce qui est dans le panier 
                # (approche pessimiste mais sûre pour l'utilisateur)
                items_a_deduire.append({
                    'type': item['type'],
                    'id': item['id_item'], # Attention : get_contenu renvoie 'id_item'
                    'quantite': item['quantite']
                })
    except Exception as e:
        current_app.logger.warning(f"Erreur lecture panier pour dispo: {e}")

    # 2. Gestion Panier Simulé (Paramètre URL optionnel, rarement utilisé maintenant)
    panier_param = request.args.get('panier')
    if panier_param:
        try:
            panier_simule = json.loads(panier_param)
            _validate_simulated_cart(panier_simule)
            items_a_deduire.extend(panier_simule)
        except (json.JSONDecodeError, ValueError):
            pass # On ignore le panier simulé s'il est cassé

    # 3. Calcul final
    resultats = services.stock.get_disponibilites(start_dt, end_dt, panier_items=items_a_deduire)
    return jsonify({"success": True, "data": resultats})

# ============================================================
# 3. INVENTAIRE & RECHERCHE
# ============================================================

@api_bp.route("/search")
@login_required
@limiter.limit("30 per minute")
def search():
    services = get_services()
    query_text = request.args.get('q', '').strip()
    
    results = services.inventory.search_objets(query_text)
    return jsonify({"success": True, "data": results})

@api_bp.route("/inventaire")
@login_required
def api_inventaire():
    services = get_services()
    
    filters = {
        'q': request.args.get('q'),
        'armoire_id': request.args.get('armoire', type=int),
        'categorie_id': request.args.get('categorie', type=int),
        'etat': request.args.get('etat')
    }
    
    dto = services.inventory.get_paginated_inventory(
        page=request.args.get('page', 1, type=int),
        sort_by=request.args.get('sort_by', 'nom'),
        direction=request.args.get('direction', 'asc'),
        filters=filters
    )
    
    html = render_template(
        '_inventaire_content.html', 
        objets=dto.items, 
        pagination={'page': dto.current_page, 'total_pages': dto.total_pages, 'endpoint': 'inventaire.inventaire'}, 
        sort_by=request.args.get('sort_by', 'nom'), 
        direction=request.args.get('direction', 'asc'), 
        armoire=dto.context.armoire_nom, 
        categorie=dto.context.categorie_nom, 
        etat=filters['etat'], 
        date_actuelle=datetime.now()
    )
    return jsonify({'html': html})


# ============================================================
# 4. ROUTES CALENDRIER (Lecture Seule)
# ============================================================

@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    """Renvoie le nombre de réservations par jour pour le calendrier."""
    etablissement_id = session.get('etablissement_id')
    try:
        from calendar import monthrange
        start_date = datetime(year, month, 1)
        days_in_month = monthrange(year, month)[1]
        end_date = datetime(year, month, days_in_month, 23, 59, 59)

        # On compte les groupes de réservation distincts par jour
        stats = db.session.execute(
            db.select(
                func.date(Reservation.debut_reservation).label('jour'), 
                func.count(func.distinct(Reservation.groupe_id)).label('total')
            )
            .filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation >= start_date,
                Reservation.debut_reservation <= end_date,
                Reservation.statut == 'confirmée'
            )
            .group_by(func.date(Reservation.debut_reservation))
        ).all()

        # Format : {'2025-12-28': 2, '2025-12-29': 5}
        return jsonify({str(row.jour): row.total for row in stats})
    except Exception as e:
        current_app.logger.error(f"Erreur stats calendrier: {e}")
        return jsonify({})

@api_bp.route("/reservation_details/<groupe_id>")
@login_required
def api_reservation_details(groupe_id):
    """Renvoie les détails d'une réservation pour le tooltip."""
    etablissement_id = session.get('etablissement_id')
    current_user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    try:
        stmt = (
            db.select(Reservation)
            .options(
                db.joinedload(Reservation.objet), 
                db.joinedload(Reservation.utilisateur), # <--- On charge l'utilisateur
                db.joinedload(Reservation.kit)
                .joinedload(Kit.objets_assoc)
                .joinedload(KitObjet.objet)
            )
            .filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
        )
        res = db.session.execute(stmt).unique().scalars().all()
        
        if not res: 
            return jsonify({'error': 'Introuvable'}), 404
        
        first = res[0]
        
        # Calcul des permissions
        is_owner = (first.utilisateur_id == current_user_id)
        is_admin = (user_role == 'admin')
        can_edit = is_owner or is_admin

        details = {
            'groupe_id': groupe_id,
            'debut': first.debut_reservation.isoformat(),
            'fin': first.fin_reservation.isoformat(),
            'user_name': first.utilisateur.nom_utilisateur if first.utilisateur else "Inconnu", # <--- Ajout du nom
            'can_edit': can_edit, # <--- Ajout de la permission
            'items': []
        }
        
        for r in res:
            if r.kit_id and r.kit:
                nom = r.kit.nom
                type_item = 'kit'
                image = None
                if r.kit.objets_assoc and r.kit.objets_assoc[0].objet:
                    image = r.kit.objets_assoc[0].objet.image_url
            elif r.objet:
                nom = r.objet.nom
                type_item = 'objet'
                image = r.objet.image_url
            else:
                continue

            details['items'].append({
                'type': type_item,
                'id': r.kit_id if r.kit_id else r.objet_id,
                'nom': nom,
                'quantite': r.quantite_reservee,
                'image': image
            })
            
        return jsonify(details)

    except Exception as e:
        current_app.logger.error(f"Erreur details reservation: {e}", exc_info=True)
        return jsonify({'error': "Erreur serveur"}), 500

@api_bp.route("/supprimer_reservation", methods=['POST'])
@login_required
def api_supprimer_reservation():
    """Supprime une réservation (Admin ou Propriétaire)."""
    etablissement_id = session.get('etablissement_id')
    gid = request.get_json().get('groupe_id')
    
    try:
        # Vérification existence et droits
        existing = db.session.execute(
            db.select(Reservation).filter_by(groupe_id=gid, etablissement_id=etablissement_id).limit(1)
        ).scalar()
        
        if not existing: 
            return jsonify({'success': False, 'error': "Introuvable"}), 404
        
        if session.get('user_role') != 'admin' and existing.utilisateur_id != session.get('user_id'):
            return jsonify({'success': False, 'error': "Interdit"}), 403

        # Suppression
        db.session.execute(db.delete(Reservation).where(Reservation.groupe_id == gid))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression: {e}")
        return jsonify({'success': False, 'error': "Erreur technique"}), 500

# Dans views/api.py

@api_bp.route("/reservations_jour/<date_str>")
@login_required
def api_reservations_jour_detail(date_str):
    """API JSON pour le tooltip du calendrier (survol)."""
    etablissement_id = session.get('etablissement_id')
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # On récupère les réservations du jour
        # On joint avec Utilisateur pour avoir le nom
        res = db.session.execute(
            db.select(Reservation, Utilisateur.nom_utilisateur)
            .join(Utilisateur, Reservation.utilisateur_id == Utilisateur.id)
            .filter(
                Reservation.etablissement_id == etablissement_id,
                func.date(Reservation.debut_reservation) == d,
                Reservation.statut == 'confirmée'
            )
            .order_by(Reservation.debut_reservation)
        ).all()
        
        # On groupe par groupe_id pour éviter les doublons dans le tooltip
        # (Si une résa a 3 objets, on ne veut pas afficher 3 fois le nom de l'utilisateur)
        seen_groups = set()
        data = []
        
        for r, nom_user in res:
            if r.groupe_id not in seen_groups:
                data.append({
                    'nom_utilisateur': nom_user,
                    'heure_debut': r.debut_reservation.strftime('%H:%M'),
                    'heure_fin': r.fin_reservation.strftime('%H:%M')
                })
                seen_groups.add(r.groupe_id)
                
        return jsonify({'reservations': data})
    except Exception as e:
        current_app.logger.error(f"Erreur API jour: {e}")
        return jsonify({'reservations': []}), 500
        

# ============================================================
# 5. MODIFICATION LIVE DES RÉSERVATIONS (CORRIGÉ)
# ============================================================

@api_bp.route("/reservation/<groupe_id>/ajouter", methods=['POST'])
@login_required
def reservation_ajouter_item(groupe_id):
    """Ajoute un item à une réservation existante."""
    services = get_services() # Utilise la factory sécurisée
    data = request.get_json()
    
    try:
        # 1. Récupération de la réservation (via SQL direct pour performance)
        stmt = select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=session['etablissement_id'])
        existing_resas = db.session.execute(stmt).scalars().all()
        
        if not existing_resas:
            return jsonify({'success': False, 'error': "Réservation introuvable"}), 404
            
        first_resa = existing_resas[0]
        # Vérification droits
        if session.get('user_role') != 'admin' and first_resa.utilisateur_id != session.get('user_id'):
            return jsonify({'success': False, 'error': "Non autorisé"}), 403

        # 2. Données
        item_type = data.get('type')
        item_id = int(data.get('id'))
        qty_to_add = int(data.get('quantite', 1))
        
        # 3. Vérification Stock (Via le Service Stock)
        # On regarde la dispo globale sur ce créneau
        dispo = services.stock.get_disponibilites(
            first_resa.debut_reservation, 
            first_resa.fin_reservation
        )
        
        # On cherche combien il en reste
        stock_restant = 0
        found = False
        
        # Recherche dans les objets
        if item_type == 'objet':
            for obj in dispo['objets']:
                if obj['id'] == item_id:
                    stock_restant = obj['disponible']
                    found = True
                    break
        # Recherche dans les kits
        elif item_type == 'kit':
            for kit in dispo['kits']:
                if kit['id'] == item_id:
                    stock_restant = kit['disponible']
                    found = True
                    break
        
        if not found:
             return jsonify({'success': False, 'error': "Item inconnu ou indisponible"}), 400

        # Note: get_disponibilites a déjà soustrait ce qui est réservé.
        # Donc stock_restant est ce qu'on peut VRAIMENT ajouter en plus.
        if stock_restant < qty_to_add:
            return jsonify({'success': False, 'error': f"Stock insuffisant (Max ajout: {stock_restant})"}), 400

        # 4. Mise à jour DB
        target_resa = None
        for r in existing_resas:
            if item_type == 'kit' and r.kit_id == item_id: target_resa = r; break
            if item_type == 'objet' and r.objet_id == item_id: target_resa = r; break
            
        if target_resa:
            target_resa.quantite_reservee += qty_to_add
        else:
            new_resa = Reservation(
                utilisateur_id=first_resa.utilisateur_id,
                etablissement_id=session['etablissement_id'],
                quantite_reservee=qty_to_add,
                debut_reservation=first_resa.debut_reservation,
                fin_reservation=first_resa.fin_reservation,
                groupe_id=groupe_id,
                statut='confirmée'
            )
            if item_type == 'kit': new_resa.kit_id = item_id
            else: new_resa.objet_id = item_id
            db.session.add(new_resa)
            
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout live: {e}", exc_info=True)
        return jsonify({'success': False, 'error': "Erreur technique"}), 500

@api_bp.route("/reservation/<groupe_id>/retirer/<int:item_id>", methods=['DELETE'])
@login_required
def reservation_retirer_item(groupe_id, item_id):
    """Retire un item d'une réservation."""
    etablissement_id = session.get('etablissement_id')
    item_type = request.args.get('type') # 'objet' ou 'kit'
    
    try:
        stmt = select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
        resas = db.session.execute(stmt).scalars().all()
        
        target = None
        for r in resas:
            if item_type == 'kit' and r.kit_id == item_id: target = r; break
            if item_type == 'objet' and r.objet_id == item_id: target = r; break
            
        if not target:
            return jsonify({'success': False, 'error': "Item non trouvé"}), 404
            
        if target.quantite_reservee > 1:
            target.quantite_reservee -= 1
        else:
            db.session.delete(target)
            
        db.session.commit()
        
        # Vérifier s'il reste des items dans la réservation
        remaining = db.session.execute(
            select(func.count(Reservation.id)).filter_by(groupe_id=groupe_id)
        ).scalar()
        
        return jsonify({'success': True, 'remaining_items': remaining})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# 6. SUGGESTIONS
# ============================================================

@api_bp.route("/suggerer_commande", methods=['POST'])
@login_required
def suggerer_commande():
    """Enregistre une suggestion de commande."""
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': "Données manquantes"}), 400

    try:
        nouvelle_suggestion = Suggestion(
            objet_id=int(data['objet_id']),
            utilisateur_id=user_id,
            quantite=int(data['quantite']),
            commentaire=data.get('commentaire', ''),
            etablissement_id=etablissement_id,
            statut='En attente',
            date_demande=datetime.now()
        )
        
        db.session.add(nouvelle_suggestion)
        db.session.commit()
        
        current_app.logger.info(f"Suggestion créée par User {user_id} pour Objet {data['objet_id']}")
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suggestion: {e}")
        return jsonify({'success': False, 'error': "Erreur technique"}), 500