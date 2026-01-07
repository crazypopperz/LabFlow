# ============================================================
# FICHIER : views/api.py (CORRECTION LOGIQUE STOCK PANIER)
# ============================================================
# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import NamedTuple
from flask import Blueprint, request, jsonify, session, current_app, render_template
from werkzeug.exceptions import BadRequest

# Imports locaux
from db import db, Objet, Armoire, Categorie, Utilisateur, Reservation, Kit, KitObjet, Suggestion, Historique, MaintenanceLog, EquipementSecurite
from extensions import limiter
from utils import login_required, admin_required

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
    if request.method in ['POST', 'PUT']:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 415

def get_services() -> Services:
    user_id = session.get('user_id')
    etablissement_id = session.get('etablissement_id')

    if not user_id or not etablissement_id:
        raise ValueError("Session invalide")

    user = db.session.get(Utilisateur, user_id)
    if not user or user.etablissement_id != etablissement_id:
        current_app.logger.critical(f"SECURITY: IDOR Attempt. User {user_id}")
        raise ValueError("Session invalide : Incohérence établissement")

    return Services(
        stock=StockService(etablissement_id),
        panier=PanierService(etablissement_id),
        inventory=InventoryService(etablissement_id)
    )

def _parse_request_dates(date_str, h_debut, h_fin):
    """Parsing robuste avec logs pour le débogage."""
    # Log debug (masqué en prod si configuré)
    current_app.logger.debug(f"[API DEBUG] Parsing dates: date='{date_str}', start='{h_debut}', end='{h_fin}'")

    if not date_str: raise ValueError("Paramètre 'date' manquant")
    if not h_debut: raise ValueError("Paramètre 'heure_debut' manquant")
    if not h_fin: raise ValueError("Paramètre 'heure_fin' manquant")
    
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Format de date invalide (attendu: YYYY-MM-DD, reçu: '{date_str}')")
    
    try:
        t_start = datetime.strptime(h_debut, "%H:%M").time()
    except ValueError:
        raise ValueError(f"Format heure_debut invalide (attendu: HH:MM, reçu: '{h_debut}')")
    
    try:
        t_end = datetime.strptime(h_fin, "%H:%M").time()
    except ValueError:
        raise ValueError(f"Format heure_fin invalide (attendu: HH:MM, reçu: '{h_fin}')")
    
    start_dt = datetime.combine(d, t_start)
    end_dt = datetime.combine(d, t_end)
    
    if start_dt >= end_dt:
        raise ValueError(f"L'heure de début ({h_debut}) doit être avant l'heure de fin ({h_fin})")
    
    return start_dt, end_dt

def _validate_simulated_cart(cart_data):
    if not isinstance(cart_data, list):
        raise ValueError("Le panier doit être une liste")
    if len(cart_data) > PanierService.MAX_ITEMS_PANIER:
        raise ValueError("Panier trop volumineux")
    
    for item in cart_data:
        if not isinstance(item, dict): raise ValueError("Item malformé")
        
        # Vérification des champs obligatoires
        if not all(k in item for k in ('type', 'id')): 
            raise ValueError("Champs type/id manquants")
            
        # Vérification de la quantité
        qty = item.get('quantite') or item.get('quantity')
        if qty is None or not isinstance(qty, (int, float)) or qty <= 0:
            raise ValueError("Quantité invalide ou manquante")

def _creneaux_se_chevauchent(start1, end1, start2, end2):
    """
    Détermine si deux créneaux temporels se chevauchent.
    Logique : (StartA < EndB) et (EndA > StartB)
    """
    return start1 < end2 and end1 > start2

# ============================================================
# GESTION D'ERREURS CENTRALISÉE
# ============================================================

@api_bp.errorhandler(StockServiceError)
@api_bp.errorhandler(PanierServiceError)
@api_bp.errorhandler(InventoryServiceError)
def handle_business_error(error):
    # Renvoie 200 pour que le JS puisse lire le message d'erreur proprement
    return jsonify({"success": False, "error": str(error), "code": "BUSINESS_ERROR"}), 200

@api_bp.errorhandler(ValueError)
@api_bp.errorhandler(BadRequest)
def handle_validation_error(error):
    current_app.logger.warning(f"[API VALIDATION ERROR] {str(error)}")
    msg = str(error) if isinstance(error, ValueError) else "JSON malformé ou invalide"
    return jsonify({
        "success": False, 
        "error": msg, 
        "code": "VALIDATION_ERROR",
        "details": str(error)
    }), 400

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
        current_app.logger.info(f"API CHECKOUT SUCCESS | User {user_id}")
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        current_app.logger.error(f"API CHECKOUT ERROR: {e}", exc_info=True)
        if isinstance(e, (PanierServiceError, StockServiceError)):
            raise e
        return jsonify({"success": False, "error": "Erreur technique"}), 500

# ============================================================
# 2. DISPONIBILITÉS (CORRIGÉ & ROBUSTE)
# ============================================================

@api_bp.route("/disponibilites", methods=['GET'])
@login_required
def api_disponibilites():
    try:
        services = get_services()
        
        # 1. Parsing des dates demandées
        start_dt, end_dt = _parse_request_dates(
            request.args.get('date'), 
            request.args.get('heure_debut'), 
            request.args.get('heure_fin')
        )

        # 2. Récupération du panier ACTUEL avec filtrage par chevauchement
        items_a_deduire = []
        
        try:
            contenu_panier = services.panier.get_contenu(session['user_id'])
            
            if contenu_panier and isinstance(contenu_panier, dict) and 'items' in contenu_panier:
                for item in contenu_panier['items']:
                    # Validation des champs requis
                    if not all(k in item for k in ('type', 'id_item', 'quantite', 'date_reservation', 'heure_debut', 'heure_fin')):
                        # On loggue mais on continue (item malformé ignoré)
                        # current_app.logger.warning(f"Item panier incomplet ignoré: {item}")
                        continue
                    
                    try:
                        # Conversion robuste des dates du panier
                        cart_date_str = item['date_reservation']
                        
                        # Gérer les deux formats possibles (str ou date object)
                        if isinstance(cart_date_str, str):
                            cart_date = datetime.strptime(cart_date_str, "%Y-%m-%d").date()
                        else:
                            cart_date = cart_date_str 
                        
                        cart_start_time = datetime.strptime(item['heure_debut'], "%H:%M").time()
                        cart_end_time = datetime.strptime(item['heure_fin'], "%H:%M").time()
                        
                        cart_start_dt = datetime.combine(cart_date, cart_start_time)
                        cart_end_dt = datetime.combine(cart_date, cart_end_time)
                        
                        # Test de chevauchement avec le créneau demandé
                        if _creneaux_se_chevauchent(cart_start_dt, cart_end_dt, start_dt, end_dt):
                            items_a_deduire.append({
                                'type': item['type'],
                                'id': item['id_item'],
                                'quantite': item['quantite']
                            })
                            current_app.logger.debug(f"Item panier CONFLIT: {item['type']}#{item['id_item']}")
                        else:
                            current_app.logger.debug(f"Item panier OK (pas de conflit): {item['type']}#{item['id_item']}")
                    
                    except (ValueError, KeyError, TypeError) as e:
                        current_app.logger.warning(f"Erreur parsing item panier (ignoré): {e}")
                        continue
        
        except Exception as e:
            current_app.logger.error(f"Erreur lecture panier: {e}", exc_info=True)

        # 3. Panier Simulé (Optionnel)
        panier_param = request.args.get('panier')
        if panier_param:
            try:
                panier_simule = json.loads(panier_param)
                _validate_simulated_cart(panier_simule)
                items_a_deduire.extend(panier_simule)
            except Exception as e:
                current_app.logger.warning(f"Panier simulé invalide: {e}")

        # 4. Calcul final des disponibilités
        resultats = services.stock.get_disponibilites(start_dt, end_dt, panier_items=items_a_deduire)
        return jsonify({"success": True, "data": resultats})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e), "code": "INVALID_PARAMS"}), 400
    except Exception as e:
        current_app.logger.error(f"Erreur API Disponibilités: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erreur serveur"}), 500

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
        armoire_id=filters['armoire_id'],
        categorie_id=filters['categorie_id'],
        date_actuelle=datetime.now(),
        etat=filters['etat']
    )
    return jsonify({'html': html})

# ============================================================
# 4. CALENDRIER
# ============================================================

@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    etablissement_id = session.get('etablissement_id')
    try:
        from calendar import monthrange
        start_date = datetime(year, month, 1)
        days_in_month = monthrange(year, month)[1]
        end_date = datetime(year, month, days_in_month, 23, 59, 59)

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
        return jsonify({str(row.jour): row.total for row in stats})
    except Exception:
        return jsonify({})

@api_bp.route("/reservation_details/<groupe_id>")
@login_required
def api_reservation_details(groupe_id):
    etablissement_id = session.get('etablissement_id')
    try:
        stmt = (
            db.select(Reservation)
            .options(
                db.joinedload(Reservation.objet), 
                db.joinedload(Reservation.utilisateur),
                db.joinedload(Reservation.kit).joinedload(Kit.objets_assoc).joinedload(KitObjet.objet)
            )
            .filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
        )
        res = db.session.execute(stmt).unique().scalars().all()
        if not res: return jsonify({'error': 'Introuvable'}), 404
        
        first = res[0]
        details = {
            'groupe_id': groupe_id,
            'debut': first.debut_reservation.isoformat(),
            'fin': first.fin_reservation.isoformat(),
            'user_name': first.utilisateur.nom_utilisateur if first.utilisateur else "Inconnu",
            'can_edit': (first.utilisateur_id == session.get('user_id')) or (session.get('user_role') == 'admin'),
            'items': []
        }
        for r in res:
            if r.kit_id and r.kit:
                img = r.kit.objets_assoc[0].objet.image_url if r.kit.objets_assoc and r.kit.objets_assoc[0].objet else None
                details['items'].append({'type': 'kit', 'id': r.kit_id, 'nom': r.kit.nom, 'quantite': r.quantite_reservee, 'image': img})
            elif r.objet:
                details['items'].append({'type': 'objet', 'id': r.objet_id, 'nom': r.objet.nom, 'quantite': r.quantite_reservee, 'image': r.objet.image_url})
        return jsonify(details)
    except Exception as e:
        current_app.logger.error(f"Erreur details: {e}")
        return jsonify({'error': "Erreur serveur"}), 500

@api_bp.route("/supprimer_reservation", methods=['POST'])
@login_required
def api_supprimer_reservation():
    etablissement_id = session.get('etablissement_id')
    gid = request.get_json().get('groupe_id')
    try:
        existing = db.session.execute(db.select(Reservation).filter_by(groupe_id=gid, etablissement_id=etablissement_id).limit(1)).scalar()
        if not existing: return jsonify({'success': False, 'error': "Introuvable"}), 404
        if session.get('user_role') != 'admin' and existing.utilisateur_id != session.get('user_id'):
            return jsonify({'success': False, 'error': "Interdit"}), 403
        db.session.execute(db.delete(Reservation).where(Reservation.groupe_id == gid))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': "Erreur technique"}), 500

@api_bp.route("/reservations_jour/<date_str>")
@login_required
def api_reservations_jour_detail(date_str):
    etablissement_id = session.get('etablissement_id')
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        res = db.session.execute(
            db.select(Reservation, Utilisateur.nom_utilisateur)
            .join(Utilisateur, Reservation.utilisateur_id == Utilisateur.id)
            .filter(Reservation.etablissement_id == etablissement_id, func.date(Reservation.debut_reservation) == d, Reservation.statut == 'confirmée')
            .order_by(Reservation.debut_reservation)
        ).all()
        seen_groups = set()
        data = []
        for r, nom_user in res:
            if r.groupe_id not in seen_groups:
                data.append({'nom_utilisateur': nom_user, 'heure_debut': r.debut_reservation.strftime('%H:%M'), 'heure_fin': r.fin_reservation.strftime('%H:%M')})
                seen_groups.add(r.groupe_id)
        return jsonify({'reservations': data})
    except Exception:
        return jsonify({'reservations': []}), 500

# ============================================================
# 5. MODIFICATION LIVE DES RÉSERVATIONS
# ============================================================

@api_bp.route("/reservation/<groupe_id>/ajouter", methods=['POST'])
@login_required
def reservation_ajouter_item(groupe_id):
    services = get_services()
    data = request.get_json()
    try:
        stmt = select(Reservation).filter_by(
            groupe_id=groupe_id, 
            etablissement_id=session['etablissement_id']
        )
        if session.get('user_role') != 'admin':
            stmt = stmt.filter_by(utilisateur_id=session.get('user_id'))
            
        existing_resas = db.session.execute(stmt).scalars().all()
        if not existing_resas:
            return jsonify({'success': False, 'error': "Réservation introuvable ou non autorisée"}), 404
            
        first_resa = existing_resas[0]
        item_type = data.get('type')
        item_id = int(data.get('id'))
        qty_to_add = int(data.get('quantite', 1))
        
        dispo = services.stock.get_disponibilites(first_resa.debut_reservation, first_resa.fin_reservation)
        stock_restant = 0
        found = False
        
        list_to_check = dispo['objets'] if item_type == 'objet' else dispo['kits']
        for item in list_to_check:
            if item['id'] == item_id:
                stock_restant = item['disponible']
                found = True
                break
        
        if not found: return jsonify({'success': False, 'error': "Item indisponible"}), 400
        if stock_restant < qty_to_add: return jsonify({'success': False, 'error': f"Stock insuffisant (Max: {stock_restant})"}), 400

        target_resa = None
        for r in existing_resas:
            if (item_type == 'kit' and r.kit_id == item_id) or (item_type == 'objet' and r.objet_id == item_id):
                target_resa = r
                break
            
        if target_resa: target_resa.quantite_reservee += qty_to_add
        else:
            new_resa = Reservation(
                utilisateur_id=first_resa.utilisateur_id, etablissement_id=session['etablissement_id'],
                quantite_reservee=qty_to_add, debut_reservation=first_resa.debut_reservation,
                fin_reservation=first_resa.fin_reservation, groupe_id=groupe_id, statut='confirmée'
            )
            if item_type == 'kit': new_resa.kit_id = item_id
            else: new_resa.objet_id = item_id
            db.session.add(new_resa)
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': "Erreur technique"}), 500

@api_bp.route("/reservation/<groupe_id>/retirer/<int:item_id>", methods=['DELETE'])
@login_required
def reservation_retirer_item(groupe_id, item_id):
    etablissement_id = session.get('etablissement_id')
    item_type = request.args.get('type')
    try:
        stmt = select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
        resas = db.session.execute(stmt).scalars().all()
        target = None
        for r in resas:
            if (item_type == 'kit' and r.kit_id == item_id) or (item_type == 'objet' and r.objet_id == item_id):
                target = r
                break
        if not target: return jsonify({'success': False, 'error': "Item non trouvé"}), 404
        
        if target.quantite_reservee > 1: target.quantite_reservee -= 1
        else: db.session.delete(target)
        db.session.commit()
        
        remaining = db.session.execute(select(func.count(Reservation.id)).filter_by(groupe_id=groupe_id)).scalar()
        return jsonify({'success': True, 'remaining_items': remaining})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route("/reservation/<groupe_id>/modifier_heure", methods=['POST'])
@login_required
def reservation_modifier_heure(groupe_id):
    """Modifie l'horaire d'une réservation avec validation du stock."""
    etablissement_id = session.get('etablissement_id')
    data = request.get_json()
    
    try:
        # 1. Parsing des nouvelles heures
        d = datetime.strptime(data.get('date'), "%Y-%m-%d").date()
        t_start = datetime.strptime(data.get('heure_debut'), "%H:%M").time()
        t_end = datetime.strptime(data.get('heure_fin'), "%H:%M").time()
        new_start = datetime.combine(d, t_start)
        new_end = datetime.combine(d, t_end)
        
        if new_start >= new_end:
            return jsonify({'success': False, 'error': "Heures invalides"}), 400

        # 2. Récupération des réservations du groupe
        stmt = select(Reservation).filter_by(
            groupe_id=groupe_id, 
            etablissement_id=etablissement_id
        )
        
        # Vérification droits
        if session.get('user_role') != 'admin':
            stmt = stmt.filter_by(utilisateur_id=session.get('user_id'))
            
        resas = db.session.execute(stmt).scalars().all()
        
        if not resas:
            return jsonify({'success': False, 'error': "Introuvable ou non autorisé"}), 404

        # 3. VALIDATION CRITIQUE : Vérification du stock sur le nouveau créneau
        for r in resas:
            if r.objet_id:
                # Calcul du stock déjà pris par LES AUTRES sur le nouveau créneau
                taken = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                    Reservation.etablissement_id == etablissement_id,
                    Reservation.groupe_id != groupe_id,  # On s'exclut
                    Reservation.objet_id == r.objet_id,
                    Reservation.debut_reservation < new_end,
                    Reservation.fin_reservation > new_start,
                    Reservation.statut == 'confirmée'
                ).scalar() or 0
                
                obj = db.session.get(Objet, r.objet_id)
                if not obj:
                    return jsonify({'success': False, 'error': "Objet introuvable"}), 404
                    
                dispo = obj.quantite_physique - taken
                
                if dispo < r.quantite_reservee:
                    return jsonify({
                        'success': False,
                        'error': f"Stock insuffisant pour '{obj.nom}' sur ce créneau (Dispo: {dispo}/{r.quantite_reservee})"
                    }), 400
                    
            elif r.kit_id:
                # Pour les kits, on vérifie chaque composant
                kit = db.session.get(Kit, r.kit_id)
                if not kit:
                    return jsonify({'success': False, 'error': "Kit introuvable"}), 404
                
                for kit_obj in kit.objets_assoc:
                    qty_needed = kit_obj.quantite * r.quantite_reservee
                    
                    taken = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                        Reservation.etablissement_id == etablissement_id,
                        Reservation.groupe_id != groupe_id,
                        Reservation.objet_id == kit_obj.objet_id,
                        Reservation.debut_reservation < new_end,
                        Reservation.fin_reservation > new_start,
                        Reservation.statut == 'confirmée'
                    ).scalar() or 0
                    
                    obj = kit_obj.objet
                    dispo = obj.quantite_physique - taken
                    
                    if dispo < qty_needed:
                        return jsonify({
                            'success': False,
                            'error': f"Stock insuffisant pour '{obj.nom}' (composant de {kit.nom}) sur ce créneau"
                        }), 400

        # 4. Application de la modification
        for r in resas:
            r.debut_reservation = new_start
            r.fin_reservation = new_end
            
        db.session.commit()
        
        current_app.logger.info(
            f"Réservation {groupe_id} déplacée vers {new_start.strftime('%Y-%m-%d %H:%M')} "
            f"par User {session.get('user_id')}"
        )
        
        return jsonify({'success': True})
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modifier_heure: {e}", exc_info=True)
        return jsonify({'success': False, 'error': "Erreur technique"}), 500

# ============================================================
# 6. SUGGESTIONS & SÉCURITÉ
# ============================================================

@api_bp.route("/suggerer_commande", methods=['POST'])
@login_required
def suggerer_commande():
    etablissement_id = session.get('etablissement_id')
    data = request.get_json()
    try:
        db.session.add(Suggestion(
            objet_id=int(data['objet_id']), utilisateur_id=session.get('user_id'),
            quantite=int(data['quantite']), commentaire=data.get('commentaire', ''),
            etablissement_id=etablissement_id, statut='En attente', date_demande=datetime.now()
        ))
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': "Erreur"}), 500

@api_bp.route("/traiter_suggestion/<int:suggestion_id>/<action>", methods=['POST'])
@login_required
def traiter_suggestion(suggestion_id, action):
    if session.get('user_role') != 'admin': return jsonify({'success': False, 'error': "Non autorisé"}), 403
    suggestion = db.session.get(Suggestion, suggestion_id)
    if not suggestion: return jsonify({'success': False, 'error': "Introuvable"}), 404
    try:
        if action == 'valider': suggestion.statut = 'Validée'
        elif action == 'refuser': db.session.delete(suggestion)
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': "Erreur"}), 500

@api_bp.route("/valider_dormant/<int:objet_id>", methods=['POST'])
@login_required
def valider_dormant(objet_id):
    if session.get('user_role') != 'admin': return jsonify({'success': False, 'error': "Non autorisé"}), 403
    try:
        db.session.add(Historique(
            objet_id=objet_id, utilisateur_id=session.get('user_id'),
            action="Vérification", details="Objet dormant validé",
            etablissement_id=session.get('etablissement_id'), timestamp=datetime.now()
        ))
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': "Erreur"}), 500

@api_bp.route('/api/signalement', methods=['POST'])
@login_required
def signaler_dysfonctionnement():
    try:
        data = request.json
        equipement_id = data.get('equipement_id')
        description = data.get('description')
        
        if not equipement_id or not description:
            return jsonify({'success': False, 'error': "Description manquante."}), 400

        user = db.session.get(Utilisateur, session.get('user_id'))
        nom_operateur = user.nom_utilisateur if user else "Utilisateur Inconnu"

        log = MaintenanceLog(
            equipement_id=equipement_id,
            date_intervention=datetime.now().date(),
            operateur=nom_operateur,
            resultat='signalement', 
            observations=description
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Erreur signalement: {e}")
        return jsonify({'success': False, 'error': "Erreur technique."}), 500

@api_bp.route('/api/traiter_signalement/<int:log_id>/<action>', methods=['POST'])
@admin_required
def traiter_signalement(log_id, action):
    try:
        log = db.session.get(MaintenanceLog, log_id)
        if not log: return jsonify({'success': False, 'error': "Introuvable"}), 404
        
        if action == 'valider':
            log.resultat = 'non_conforme' 
            log.observations += " [Validé par Admin]"
        elif action == 'refuser':
            db.session.delete(log)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500