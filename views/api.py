# ============================================================
# FICHIER : views/api.py (Version Finale - Refactorisée & Complète)
# ============================================================
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import or_, func, text, and_
from sqlalchemy.exc import SQLAlchemyError

# Imports locaux
from db import db, Objet, Armoire, Categorie, Reservation, Suggestion, Kit, KitObjet, Utilisateur
from extensions import limiter
from utils import login_required, admin_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ============================================================
# 1. UTILITAIRES & VALIDATEURS (DRY)
# ============================================================

def validate_reservation_dates(date_str, heure_debut, heure_fin):
    """
    Valide la cohérence des dates pour une réservation.
    Retourne (start_dt, end_dt) ou lève une ValueError.
    """
    try:
        start_dt = datetime.strptime(f"{date_str} {heure_debut}", '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(f"{date_str} {heure_fin}", '%Y-%m-%d %H:%M')
    except ValueError:
        raise ValueError("Format de date ou d'heure invalide.")

    now = datetime.now()
    
    if start_dt < now:
        raise ValueError("Impossible de réserver dans le passé.")
    
    if end_dt <= start_dt:
        raise ValueError("L'heure de fin doit être postérieure à l'heure de début.")
        
    if (end_dt - start_dt).total_seconds() > 12 * 3600:
        raise ValueError("La réservation ne peut pas dépasser 12 heures.")

    return start_dt, end_dt

def validate_and_parse_items(items, etablissement_id):
    """
    Valide les items du panier et retourne :
    - objets_demandes: {objet_id: quantite_totale} (pour vérification stock)
    - reservations_a_creer: [{objet_id, quantite, kit_id}] (pour insertion DB)
    
    Lève ValueError si les données sont invalides.
    """
    if not items:
        raise ValueError("Panier vide")
    
    objets_demandes = {}
    reservations_a_creer = []
    
    for item in items:
        # Validation défensive des types
        try:
            qte = int(item.get('quantity', 0))
            item_id = int(item.get('id', 0))
            item_type = item.get('type', '').strip()
            
            if qte <= 0 or item_id <= 0:
                continue
                
            if item_type not in ['objet', 'kit']:
                raise ValueError("Type d'item invalide")
                
        except (ValueError, TypeError, KeyError):
            raise ValueError("Format de données invalide dans le panier")
        
        # Traitement Objet unique
        if item_type == 'objet':
            objets_demandes[item_id] = objets_demandes.get(item_id, 0) + qte
            reservations_a_creer.append({
                'objet_id': item_id, 
                'quantite': qte, 
                'kit_id': None
            })
        
        # Traitement Kit (Explosion du kit en objets)
        elif item_type == 'kit':
            kit = db.session.get(Kit, item_id)
            if not kit or kit.etablissement_id != etablissement_id:
                raise ValueError(f"Kit ID {item_id} invalide ou inaccessible")
                
            for assoc in kit.objets_assoc:
                qte_necessaire = assoc.quantite * qte
                objets_demandes[assoc.objet_id] = objets_demandes.get(assoc.objet_id, 0) + qte_necessaire
                reservations_a_creer.append({
                    'objet_id': assoc.objet_id, 
                    'quantite': qte_necessaire, 
                    'kit_id': item_id
                })
    
    if not objets_demandes:
        raise ValueError("Aucun objet valide trouvé dans le panier")
    
    return objets_demandes, reservations_a_creer

def get_paginated_objets(etablissement_id, page, sort_by, direction, search_query=None, armoire_id=None, categorie_id=None, etat=None):
    """
    Fonction helper pour la pagination avec protection SQL Injection et DoS.
    """
    try:
        page = int(page)
        page = max(1, min(page, 1000))
    except (ValueError, TypeError):
        page = 1

    ALLOWED_SORT_COLUMNS = {
        'nom': Objet.nom,
        'quantite': Objet.quantite_physique,
        'seuil': Objet.seuil,
        'date_peremption': Objet.date_peremption,
        'categorie': 'categorie_nom',
        'armoire': 'armoire_nom'
    }
    
    sort_column = ALLOWED_SORT_COLUMNS.get(sort_by, Objet.nom)
    
    query = db.select(Objet).filter_by(etablissement_id=etablissement_id)
    query = query.outerjoin(Categorie).outerjoin(Armoire)

    if search_query:
        term = f"%{search_query}%"
        query = query.filter(or_(Objet.nom.ilike(term), Categorie.nom.ilike(term), Armoire.nom.ilike(term)))
    
    if armoire_id: query = query.filter(Objet.armoire_id == armoire_id)
    if categorie_id: query = query.filter(Objet.categorie_id == categorie_id)

    if etat:
        today = datetime.now().date()
        if etat == 'perime': query = query.filter(Objet.date_peremption < today)
        elif etat == 'bientot': query = query.filter(Objet.date_peremption >= today, Objet.date_peremption <= today + timedelta(days=30))
        elif etat == 'stock': query = query.filter(Objet.quantite_physique <= Objet.seuil)

    if sort_by == 'categorie': sort_expr = Categorie.nom
    elif sort_by == 'armoire': sort_expr = Armoire.nom
    else: sort_expr = sort_column

    query = query.order_by(sort_expr.desc() if direction == 'desc' else sort_expr.asc())

    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    
    # Calcul stock dispo
    objets = pagination.items
    now = datetime.now()
    objet_ids = [o.id for o in objets]
    
    res_map = {}
    if objet_ids:
        reservations = db.session.execute(
            db.select(Reservation.objet_id, func.sum(Reservation.quantite_reservee))
            .filter(Reservation.objet_id.in_(objet_ids), Reservation.fin_reservation > now, Reservation.etablissement_id == etablissement_id)
            .group_by(Reservation.objet_id)
        ).all()
        res_map = {r[0]: r[1] for r in reservations}

    for obj in objets:
        obj.quantite_disponible = obj.quantite_physique - res_map.get(obj.id, 0)

    return objets, pagination.pages


# ============================================================
# 2. ENDPOINTS PUBLICS / MONITORING
# ============================================================
@api_bp.route('/health')
@limiter.limit("60 per minute")
def health_check():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({'status': 'ok', 'db': 'connected', 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        current_app.logger.error(f"Health Check Failed: {e}")
        return jsonify({'status': 'error', 'db': 'disconnected'}), 503


# ============================================================
# 3. ENDPOINTS RECHERCHE & SUGGESTIONS
# ============================================================
@api_bp.route("/search")
@login_required
def search():
    etablissement_id = session.get('etablissement_id')
    query_text = request.args.get('q', '').strip()
    
    if not query_text or len(query_text) < 2:
        return jsonify([])

    try:
        results = db.session.execute(
            db.select(Objet)
            .filter(Objet.etablissement_id == etablissement_id, Objet.nom.ilike(f"%{query_text}%"))
            .limit(10)
        ).scalars().all()
        
        return jsonify([{
            'id': obj.id, 'nom': obj.nom, 'image': obj.image_url,
            'armoire': obj.armoire.nom if obj.armoire else None
        } for obj in results])
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return jsonify([]), 500

@api_bp.route("/suggerer_commande", methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def suggerer_commande():
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    data = request.get_json()
    
    try:
        objet_id = int(data.get('objet_id'))
        quantite = int(data.get('quantite', 1))
        commentaire = data.get('commentaire', '').strip()
        
        if quantite <= 0: return jsonify({'success': False, 'error': "Quantité positive requise."}), 400

        objet = db.session.get(Objet, objet_id)
        if not objet or objet.etablissement_id != etablissement_id:
            return jsonify({'success': False, 'error': "Objet introuvable."}), 404

        db.session.add(Suggestion(
            objet_id=objet_id, utilisateur_id=user_id, quantite=quantite,
            commentaire=commentaire[:255], etablissement_id=etablissement_id
        ))
        db.session.commit()
        return jsonify({'success': True})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': "Données invalides."}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suggestion: {e}")
        return jsonify({'success': False, 'error': "Erreur serveur."}), 500

@api_bp.route("/traiter_suggestion/<int:suggestion_id>/<action>", methods=['POST'])
@admin_required
def traiter_suggestion(suggestion_id, action):
    etablissement_id = session.get('etablissement_id')
    suggestion = db.session.get(Suggestion, suggestion_id)
    
    if not suggestion or suggestion.etablissement_id != etablissement_id:
        return jsonify({'success': False, 'error': "Suggestion introuvable"}), 404

    try:
        if action == 'valider':
            suggestion.statut = 'Validée'
            suggestion.objet.en_commande = 1
        elif action == 'refuser':
            suggestion.statut = 'Refusée'
            db.session.delete(suggestion)
        else:
            return jsonify({'success': False, 'error': "Action inconnue"}), 400
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur traitement suggestion: {e}")
        return jsonify({'success': False, 'error': "Erreur serveur"}), 500


# ============================================================
# 4. CŒUR DU SYSTÈME : RÉSERVATIONS (SÉCURISÉ & DRY)
# ============================================================

@api_bp.route("/valider_panier", methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def api_valider_panier():
    """
    Vérifie la disponibilité des objets sans créer de réservation.
    Utilise la logique centralisée `validate_and_parse_items`.
    """
    etablissement_id = session.get('etablissement_id')
    data = request.get_json()
    
    try:
        start_dt, end_dt = validate_reservation_dates(
            data.get('date'), data.get('heure_debut'), data.get('heure_fin')
        )
        
        # ✅ LOGIQUE CENTRALISÉE
        objets_demandes, _ = validate_and_parse_items(data.get('items', []), etablissement_id)

        # Vérification Disponibilité
        for obj_id, qte_demandee in objets_demandes.items():
            objet = db.session.get(Objet, obj_id)
            if not objet or objet.etablissement_id != etablissement_id:
                return jsonify({"success": False, "error": "Objet introuvable"}), 404

            qte_reservee = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                Reservation.objet_id == obj_id,
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation < end_dt,
                Reservation.fin_reservation > start_dt
            ).scalar() or 0
            
            disponible = objet.quantite_physique - qte_reservee
            
            if qte_demandee > disponible:
                return jsonify({
                    "success": False, 
                    "error": f"Stock insuffisant pour '{objet.nom}'. Demandé: {qte_demandee}, Dispo: {disponible}"
                }), 409

        return jsonify({"success": True})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Erreur validation panier: {e}")
        return jsonify({"success": False, "error": "Erreur serveur"}), 500


@api_bp.route("/creer_reservation", methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def api_creer_reservation():
    """
    Crée une nouvelle réservation avec vérification atomique de disponibilité.
    
    Request Body (JSON):
        {
            "date": "2025-01-15",
            "heure_debut": "09:00",
            "heure_fin": "11:00",
            "items": [
                {"type": "objet", "id": 1, "quantity": 2},
                {"type": "kit", "id": 5, "quantity": 1}
            ]
        }
    
    Returns:
        200: {"success": true, "groupe_id": "uuid"}
        400: {"success": false, "error": "message"}
        500: {"success": false, "error": "Erreur serveur"}
    
    Security:
        - Pessimistic locking (FOR UPDATE) pour éviter race conditions
        - Validation stricte des inputs
        - Rate limited à 5 requêtes/minute
    """
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    data = request.get_json()
    
    try:
        start_dt, end_dt = validate_reservation_dates(
            data.get('date'), data.get('heure_debut'), data.get('heure_fin')
        )
        
        # ✅ LOGIQUE CENTRALISÉE
        objets_demandes, reservations_a_creer = validate_and_parse_items(
            data.get('items', []), etablissement_id
        )

        groupe_id = str(uuid.uuid4())
        
        # LOCK & VÉRIFICATION (Transaction implicite via Flask-SQLAlchemy)
        for obj_id, qte_demandee in objets_demandes.items():
            # SELECT ... FOR UPDATE (Lock Pessimiste)
            objet = db.session.execute(
                db.select(Objet)
                .filter_by(id=obj_id, etablissement_id=etablissement_id)
                .with_for_update()
            ).scalar_one_or_none()
            
            if not objet:
                raise ValueError("Objet introuvable")

            qte_reservee = db.session.query(func.sum(Reservation.quantite_reservee)).filter(
                Reservation.objet_id == obj_id,
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation < end_dt,
                Reservation.fin_reservation > start_dt
            ).scalar() or 0
            
            disponible = objet.quantite_physique - qte_reservee
            
            if qte_demandee > disponible:
                raise ValueError(f"Stock insuffisant pour '{objet.nom}' (Dispo: {disponible})")

        # CRÉATION
        for r in reservations_a_creer:
            db.session.add(Reservation(
                objet_id=r['objet_id'],
                utilisateur_id=user_id,
                quantite_reservee=r['quantite'],
                debut_reservation=start_dt,
                fin_reservation=end_dt,
                groupe_id=groupe_id,
                kit_id=r['kit_id'],
                etablissement_id=etablissement_id
            ))
        
        db.session.commit()
        
        current_app.logger.info(
            "Reservation created",
            extra={
                'user_id': user_id, 'groupe_id': groupe_id,
                'items_count': len(data.get('items', [])),
                'start': start_dt.isoformat()
            }
        )
        
        return jsonify({"success": True, "groupe_id": groupe_id})

    except ValueError as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"DB Error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erreur technique"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erreur serveur"}), 500


@api_bp.route("/reservation_details/<groupe_id>")
@login_required
def api_reservation_details(groupe_id):
    """Récupère les détails d'une réservation (Sécurisé IDOR)."""
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    reservations = db.session.execute(
        db.select(Reservation)
        .options(db.joinedload(Reservation.objet), db.joinedload(Reservation.kit))
        .filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
    ).scalars().all()
    
    if not reservations:
        return jsonify({'error': 'Réservation introuvable'}), 404
        
    # SÉCURITÉ IDOR
    first_resa = reservations[0]
    if user_role != 'admin' and first_resa.utilisateur_id != user_id:
        current_app.logger.warning(f"IDOR Attempt: User {user_id} tried to access reservation {groupe_id}")
        return jsonify({'error': 'Accès non autorisé'}), 403

    details = {
        'groupe_id': groupe_id,
        'debut': first_resa.debut_reservation.isoformat(),
        'fin': first_resa.fin_reservation.isoformat(),
        'objets': []
    }
    
    for r in reservations:
        nom = r.objet.nom
        if r.kit: nom += f" (via Kit: {r.kit.nom})"
        details['objets'].append({
            'nom': nom, 'quantite': r.quantite_reservee, 'image': r.objet.image_url
        })
        
    return jsonify(details)


# ============================================================
# 5. ENDPOINTS CALENDRIER & GESTION (RESTAURÉS)
# ============================================================

@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    """Retourne le nombre de réservations par jour pour le calendrier."""
    etablissement_id = session.get('etablissement_id')
    
    try:
        if not (1 <= month <= 12) or not (2000 <= year <= 2100):
            return jsonify({"error": "Date invalide"}), 400
        
        from calendar import monthrange
        start_date = datetime(year, month, 1).date()
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        reservations = db.session.execute(
            db.select(
                func.date(Reservation.debut_reservation).label('jour'),
                func.count(func.distinct(Reservation.groupe_id)).label('count')
            )
            .filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation >= start_date,
                Reservation.debut_reservation <= end_date
            )
            .group_by(func.date(Reservation.debut_reservation))
        ).all()
        
        return jsonify({r.jour.strftime('%Y-%m-%d'): r.count for r in reservations})
        
    except Exception as e:
        current_app.logger.error(f"Erreur calendrier: {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@api_bp.route("/reservations_jour/<date_str>")
@login_required
def api_reservations_jour(date_str):
    """Retourne les réservations d'un jour spécifique."""
    etablissement_id = session.get('etablissement_id')
    
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        groupes = db.session.execute(
            db.select(
                Reservation.groupe_id,
                Reservation.utilisateur_id,
                Reservation.debut_reservation,
                Reservation.fin_reservation
            )
            .filter(
                Reservation.etablissement_id == etablissement_id,
                func.date(Reservation.debut_reservation) == date_obj
            )
            .distinct(Reservation.groupe_id)
            .order_by(Reservation.groupe_id, Reservation.debut_reservation)
        ).all()
        
        result = []
        for groupe in groupes:
            user = db.session.get(Utilisateur, groupe.utilisateur_id)
            result.append({
                'nom_utilisateur': user.nom_utilisateur if user else 'Inconnu',
                'heure_debut': groupe.debut_reservation.strftime('%H:%M'),
                'heure_fin': groupe.fin_reservation.strftime('%H:%M'),
                'groupe_id': groupe.groupe_id
            })
        
        return jsonify({'reservations': result})
        
    except ValueError:
        return jsonify({'error': 'Format de date invalide', 'reservations': []}), 400
    except Exception as e:
        current_app.logger.error(f"Erreur reservations jour: {e}")
        return jsonify({'error': 'Erreur serveur', 'reservations': []}), 500


@api_bp.route("/supprimer_reservation", methods=['POST'])
@login_required
def api_supprimer_reservation():
    """Supprime une réservation (avec vérification des droits)."""
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    data = request.get_json()
    if not data: return jsonify({'success': False, 'error': "Corps de requête vide"}), 400
        
    groupe_id = data.get("groupe_id")
    if not groupe_id: return jsonify({'success': False, 'error': "ID de groupe manquant"}), 400
    
    try:
        reservation = db.session.execute(
            db.select(Reservation).filter_by(groupe_id=groupe_id, etablissement_id=etablissement_id)
        ).scalars().first()
        
        if not reservation:
            return jsonify({'success': False, 'error': "Réservation introuvable"}), 404
        
        if user_role != 'admin' and reservation.utilisateur_id != user_id:
            current_app.logger.warning(f"Delete attempt: User {user_id} tried to delete reservation {groupe_id}")
            return jsonify({'success': False, 'error': "Permissions insuffisantes"}), 403
        
        db.session.execute(
            db.delete(Reservation).where(
                Reservation.groupe_id == groupe_id,
                Reservation.etablissement_id == etablissement_id
            )
        )
        db.session.commit()
        
        current_app.logger.info(f"Reservation deleted: {groupe_id} by user {user_id}")
        return jsonify({'success': True, 'message': "Réservation supprimée"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression réservation: {e}", exc_info=True)
        return jsonify({'success': False, 'error': "Erreur serveur"}), 500


# ============================================================
# 6. ENDPOINTS INVENTAIRE (Pagination)
# ============================================================

@api_bp.route("/inventaire/")
@login_required
def api_inventaire():
    """Retourne l'inventaire paginé avec filtres (JSON)."""
    etablissement_id = session.get('etablissement_id')
    
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    search_query = request.args.get('q')
    armoire_id = request.args.get('armoire', type=int)
    categorie_id = request.args.get('categorie', type=int)
    etat = request.args.get('etat')

    objets, total_pages = get_paginated_objets(
        etablissement_id, page, sort_by, direction, 
        search_query, armoire_id, categorie_id, etat
    )

    objets_json = [{
        'id': o.id,
        'nom': o.nom,
        'quantite_physique': o.quantite_physique,
        'quantite_disponible': o.quantite_disponible,
        'seuil': o.seuil,
        'image_url': o.image_url,
        'armoire': o.armoire.nom if o.armoire else None,
        'categorie': o.categorie.nom if o.categorie else None
    } for o in objets]

    return jsonify({
        'objets': objets_json,
        'pagination': {
            'page': page,
            'total_pages': total_pages
        }
    })