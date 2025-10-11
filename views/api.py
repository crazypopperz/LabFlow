# ============================================================
# IMPORTS
# ============================================================

# Imports depuis la bibliothèque standard
import uuid
import traceback
from datetime import datetime, timedelta
import math

# Imports depuis les bibliothèques tierces (Flask)
from flask import (Blueprint, jsonify, request, flash, session, current_app)

# Imports depuis nos propres modules
from db import get_db
from utils import login_required, admin_required, enregistrer_action
# On importera d'autres fonctions au besoin

# ============================================================
# CRÉATION DU BLUEPRINT API
# ============================================================
api_bp = Blueprint(
    'api', 
    __name__,
    url_prefix='/api' # Toutes les routes commenceront par /api
)

# ============================================================
# LES FONCTIONS DE ROUTES API SERONT COLLÉES ICI
# ============================================================
def get_disponibilite_objet(db, objet_id, debut_str, fin_str):
    """
    Calcule la quantité disponible d'un objet pour un créneau horaire spécifique.
    """
    objet = db.execute("SELECT quantite_physique FROM objets WHERE id = ?", (objet_id,)).fetchone()
    if not objet:
        return 0
    quantite_physique = objet['quantite_physique']
    
    reservations_chevauchement = db.execute("""
        SELECT SUM(quantite_reservee) as total_reserve
        FROM reservations
        WHERE objet_id = ? AND fin_reservation > ? AND debut_reservation < ?
    """, (objet_id, debut_str, fin_str)).fetchone()
    
    quantite_reservee_max = reservations_chevauchement['total_reserve'] if reservations_chevauchement and reservations_chevauchement['total_reserve'] else 0

    return quantite_physique - quantite_reservee_max


@api_bp.route("/rechercher")
@login_required
def api_rechercher():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    db = get_db()
    resultats = db.execute(
        """SELECT o.id, o.nom, o.armoire_id, a.nom as armoire_nom,
                  c.nom as categorie_nom
           FROM objets o
           JOIN armoires a ON o.armoire_id = a.id
           JOIN categories c ON o.categorie_id = c.id
           WHERE unaccent(LOWER(o.nom)) LIKE unaccent(LOWER(?))
           LIMIT 10""", (f"%{query}%", )).fetchall()
    return jsonify([dict(row) for row in resultats])


@api_bp.route("/reservations_par_mois/<int:year>/<int:month>")
@login_required
def api_reservations_par_mois(year, month):
    db = get_db()

    start_date_str = f"{year}-{str(month).zfill(2)}-01 00:00:00"

    if month == 12:
        end_date_str = f"{year + 1}-01-01 00:00:00"
    else:
        end_date_str = f"{year}-{str(month + 1).zfill(2)}-01 00:00:00"

    reservations = db.execute(
        """
        SELECT
            DATE(r.debut_reservation) as jour_reservation,
            r.groupe_id,
            r.utilisateur_id,
            u.nom_utilisateur
        FROM reservations r
        JOIN utilisateurs u ON r.utilisateur_id = u.id
        WHERE r.debut_reservation >= ? AND r.debut_reservation < ?
              AND r.groupe_id IS NOT NULL
        GROUP BY jour_reservation, r.groupe_id
        """, (start_date_str, end_date_str)).fetchall()

    results = {}
    for row in reservations:
        date = row['jour_reservation']
        if date not in results:
            results[date] = []

        results[date].append(
            {'is_mine': row['utilisateur_id'] == session['user_id']})
    return jsonify(results)


@api_bp.route("/reservation_details/<groupe_id>")
@login_required
def api_reservation_details(groupe_id):
    db = get_db()
    reservations = db.execute(
        """
        SELECT r.quantite_reservee, o.id as objet_id, o.nom as objet_nom, 
               u.nom_utilisateur, r.utilisateur_id, r.kit_id, k.nom as kit_nom,
               r.debut_reservation, r.fin_reservation
        FROM reservations r
        JOIN objets o ON r.objet_id = o.id
        JOIN utilisateurs u ON r.utilisateur_id = u.id
        LEFT JOIN kits k ON r.kit_id = k.id
        WHERE r.groupe_id = ?
        """, (groupe_id, )).fetchall()

    if not reservations:
        return jsonify({'error': 'Réservation non trouvée'}), 404

    details = {
        'kits': {},
        'objets_manuels': [],
        'nom_utilisateur': reservations[0]['nom_utilisateur'],
        'utilisateur_id': reservations[0]['utilisateur_id'],
        'debut_reservation': reservations[0]['debut_reservation'],
        'fin_reservation': reservations[0]['fin_reservation']
    }

    objets_manuels_bruts = [dict(r) for r in reservations if r['kit_id'] is None]
    objets_kits_reserves = [r for r in reservations if r['kit_id'] is not None]

    kits_comptes = {}
    for r in objets_kits_reserves:
        if r['kit_id'] not in kits_comptes:
            kits_comptes[r['kit_id']] = {'nom': r['kit_nom'], 'objets_reserves': {}}
        kits_comptes[r['kit_id']]['objets_reserves'][r['objet_id']] = r['quantite_reservee']

    for kit_id, data in kits_comptes.items():
        objets_base_du_kit = db.execute("SELECT objet_id, quantite FROM kit_objets WHERE kit_id = ?", (kit_id,)).fetchall()
        if not objets_base_du_kit: continue
        
        id_objet_calcul, quantite_par_kit = next(((obj['objet_id'], obj['quantite']) for obj in objets_base_du_kit if obj['objet_id'] in data['objets_reserves']), (None, 0))

        if id_objet_calcul and quantite_par_kit > 0:
            quantite_reelle_reservee = data['objets_reserves'][id_objet_calcul]
            nombre_de_kits = quantite_reelle_reservee // quantite_par_kit
            details['kits'][str(kit_id)] = {'quantite': nombre_de_kits, 'nom': data['nom']}

    objets_manuels_agreges = {}
    for item in objets_manuels_bruts:
        obj_id = item['objet_id']
        nom = item['objet_nom'] 
        quantite = item['quantite_reservee']
        
        if obj_id not in objets_manuels_agreges:
            objets_manuels_agreges[obj_id] = {'nom': nom, 'quantite_reservee': 0}
        objets_manuels_agreges[obj_id]['quantite_reservee'] += quantite

    for obj_id, data in objets_manuels_agreges.items():
        details['objets_manuels'].append({
            'objet_id': obj_id,
            'nom': data['nom'],
            'quantite_reservee': data['quantite_reservee']
        })

    return jsonify(details)


@api_bp.route("/reservation_data/<date>/<heure_debut>/<heure_fin>")
@login_required
def api_reservation_data(date, heure_debut, heure_fin):
    db = get_db()
    
    debut_str = f"{date} {heure_debut}"
    fin_str = f"{date} {heure_fin}"

    objets_bruts = db.execute("""
        SELECT o.id, o.nom, c.nom as categorie, o.quantite_physique
        FROM objets o JOIN categories c ON o.categorie_id = c.id
        ORDER BY c.nom, o.nom
    """).fetchall()
    
    grouped_objets = {}
    objets_map = {}
    for row in objets_bruts:
        categorie_nom = row['categorie']
        if categorie_nom not in grouped_objets:
            grouped_objets[categorie_nom] = []
        
        quantite_disponible = get_disponibilite_objet(db, row['id'], debut_str, fin_str)
        
        obj_data = {
            "id": row['id'],
            "nom": row['nom'],
            "quantite_totale": row['quantite_physique'],
            "quantite_disponible": quantite_disponible if quantite_disponible >= 0 else 0
        }
        grouped_objets[categorie_nom].append(obj_data)
        objets_map[row['id']] = obj_data

    kits = db.execute("SELECT id, nom, description FROM kits ORDER BY nom").fetchall()
    kits_details = []
    for kit in kits:
        objets_du_kit = db.execute("SELECT objet_id, quantite FROM kit_objets WHERE kit_id = ?", (kit['id'],)).fetchall()
        
        disponibilite_kit = 9999 # On part d'un nombre très grand
        if not objets_du_kit:
            disponibilite_kit = 0
        else:
            for obj_in_kit in objets_du_kit:
                objet_data = objets_map.get(obj_in_kit['objet_id'])
                
                if not objet_data or obj_in_kit['quantite'] == 0:
                    disponibilite_kit = 0
                    break
                
                kits_possibles = math.floor(objet_data['quantite_disponible'] / obj_in_kit['quantite'])
                
                if kits_possibles < disponibilite_kit:
                    disponibilite_kit = kits_possibles

        kits_details.append({
            'id': kit['id'],
            'nom': kit['nom'],
            'description': kit['description'],
            'objets': [dict(o) for o in objets_du_kit],
            'disponibilite': disponibilite_kit if disponibilite_kit != 9999 else 0
        })

    return jsonify({'objets': grouped_objets, 'kits': kits_details})

@api_bp.route("/reserver", methods=["POST"])
@login_required
def api_reserver():
    return jsonify(success=False, error="Cette route est obsolète."), 400


@api_bp.route("/modifier_reservation", methods=["POST"])
@login_required
def api_modifier_reservation():
    data = request.get_json()
    groupe_id = data.get("groupe_id")
    db = get_db()
    
    try:
        # On utilise une transaction pour s'assurer que tout réussit ou tout échoue
        db.execute("BEGIN")
        
        # Étape 1: Supprimer l'ancienne réservation
        db.execute("DELETE FROM reservations WHERE groupe_id = ?", (groupe_id,))
        
        # Étape 2: Valider et insérer la nouvelle réservation comme un "mini-panier"
        creneau_key = f"{data['date']}_{data['heure_debut']}_{data['heure_fin']}"
        mini_cart = { creneau_key: data }
        
        response = api_valider_panier_interne(mini_cart, groupe_id_existant=groupe_id) 
        
        if response.get('success'):
            db.commit()
            flash("Réservation modifiée avec succès !", "success")
            return jsonify(success=True)
        else:
            db.rollback() # Annule la suppression si la nouvelle réservation échoue
            return jsonify(success=False, error=response.get('error', 'Erreur inconnue lors de la modification')), 400

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=f"Une erreur interne est survenue : {e}"), 500

def api_valider_panier_interne(cart_data, groupe_id_existant=None):
    db = get_db()
    user_id = session['user_id']

    try:
        # Étape 1 : Vérifier la disponibilité pour chaque créneau
        for creneau_key, resa_details in cart_data.items():
            debut_str = f"{resa_details['date']} {resa_details['heure_debut']}"
            fin_str = f"{resa_details['date']} {resa_details['heure_fin']}"
            
            objets_requis_pour_creneau = {}
            for kit_id, kit_data in resa_details.get('kits', {}).items():
                objets_du_kit = db.execute("SELECT objet_id, quantite FROM kit_objets WHERE kit_id = ?", (kit_id,)).fetchall()
                for obj_in_kit in objets_du_kit:
                    objets_requis_pour_creneau[obj_in_kit['objet_id']] = objets_requis_pour_creneau.get(obj_in_kit['objet_id'], 0) + (obj_in_kit['quantite'] * kit_data.get('quantite', 0))
            for obj_id, obj_data in resa_details.get('objets', {}).items():
                objets_requis_pour_creneau[int(obj_id)] = objets_requis_pour_creneau.get(int(obj_id), 0) + obj_data.get('quantite', 0)

            for obj_id, quantite_demandee in objets_requis_pour_creneau.items():
                if quantite_demandee <= 0: continue
                disponibilite_reelle = get_disponibilite_objet(db, obj_id, debut_str, fin_str)
                objet_nom = db.execute("SELECT nom FROM objets WHERE id = ?", (obj_id,)).fetchone()['nom']
                if disponibilite_reelle < quantite_demandee:
                    return {'success': False, 'error': f"Stock insuffisant pour '{objet_nom}' sur le créneau {resa_details['heure_debut']}-{resa_details['heure_fin']} ({disponibilite_reelle} disponible(s))."}

        # Étape 2 : Si tout est disponible, on insère les réservations
        for creneau_key, resa_details in cart_data.items():
            groupe_id = groupe_id_existant or str(uuid.uuid4())
            debut_dt = datetime.strptime(f"{resa_details['date']} {resa_details['heure_debut']}", '%Y-%m-%d %H:%M')
            fin_dt = datetime.strptime(f"{resa_details['date']} {resa_details['heure_fin']}", '%Y-%m-%d %H:%M')
            
            # --- LA CORRECTION EST ICI : On reconstruit la liste des objets à insérer ---
            final_reservations = {}
            for kit_id_str, kit_data in resa_details.get('kits', {}).items():
                objets_du_kit = db.execute("SELECT objet_id, quantite FROM kit_objets WHERE kit_id = ?", (kit_id_str,)).fetchall()
                for obj_in_kit in objets_du_kit:
                    key = (obj_in_kit['objet_id'], int(kit_id_str))
                    final_reservations[key] = final_reservations.get(key, 0) + (obj_in_kit['quantite'] * kit_data.get('quantite', 0))
            for obj_id_str, obj_data in resa_details.get('objets', {}).items():
                key = (int(obj_id_str), None)
                final_reservations[key] = final_reservations.get(key, 0) + obj_data.get('quantite', 0)
            # --- FIN DE LA CORRECTION ---

            for (obj_id, kit_id), quantite_totale in final_reservations.items():
                if quantite_totale > 0:
                    db.execute(
                        """INSERT INTO reservations (objet_id, quantite_reservee, debut_reservation, fin_reservation, utilisateur_id, groupe_id, kit_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (obj_id, quantite_totale, debut_dt, fin_dt, user_id, groupe_id, kit_id))
                    action = "Modification Réservation" if groupe_id_existant else "Réservation"
                    enregistrer_action(obj_id, action, f"Quantité: {quantite_totale} pour le {debut_dt.strftime('%d/%m/%Y')}")
        
        # On ne fait pas de commit ici, on laisse la fonction appelante décider.
        return {'success': True}
    except Exception as e:
        traceback.print_exc()
        return {'success': False, 'error': f"Erreur interne: {e}"}

@api_bp.route("/valider_panier", methods=["POST"])
@login_required
def api_valider_panier():
    cart_data = request.get_json()
    if not cart_data:
        return jsonify(success=False, error="Le panier est vide."), 400

    db = get_db()
    try:
        # On utilise une transaction pour s'assurer que l'ensemble du panier est validé ou rien du tout.
        db.execute("BEGIN")
        response = api_valider_panier_interne(cart_data)
        
        if response.get('success'):
            db.commit()
            flash("Toutes vos réservations ont été confirmées avec succès !", "success")
            return jsonify(success=True)
        else:
            db.rollback()
            return jsonify(success=False, error=response.get('error')), 400
            
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return jsonify(success=False, error=f"Une erreur interne est survenue : {e}"), 500

@api_bp.route("/supprimer_reservation", methods=["POST"])
@login_required
def api_supprimer_reservation():
    data = request.get_json()
    groupe_id = data.get("groupe_id")
    db = get_db()
    try:
        reservation_info = db.execute("SELECT utilisateur_id FROM reservations WHERE groupe_id = ? LIMIT 1", (groupe_id, )).fetchone()
        if not reservation_info:
            return jsonify(success=False, error="Réservation non trouvée."), 404
        if (session.get('user_role') != 'admin' and reservation_info['utilisateur_id'] != session['user_id']):
            return jsonify(success=False, error="Vous n'avez pas la permission de supprimer cette réservation."), 403
        
        db.execute("DELETE FROM reservations WHERE groupe_id = ?", (groupe_id,))
        db.commit()
        
        flash("La réservation a été annulée.", "success")
        return jsonify(success=True)
    except sqlite3.Error as e:
        db.rollback()
        return jsonify(success=False, error=str(e)), 500

@api_bp.route("/suggestion_commande/<int:objet_id>")
@admin_required
def api_suggestion_commande(objet_id):
    db = get_db()

    date_limite = datetime.now() - timedelta(days=90)

    result = db.execute(
        """
        SELECT SUM(quantite_reservee)
        FROM reservations
        WHERE objet_id = ? AND debut_reservation >= ?
        """, (objet_id, date_limite)).fetchone()

    consommation = result[0] if result and result[0] is not None else 0

    suggestion = 0
    if consommation > 0:
        suggestion = math.ceil(consommation * 1.5)
    else:
        objet = db.execute("SELECT seuil FROM objets WHERE id = ?",
                           (objet_id, )).fetchone()
        if objet:
            suggestion = objet['seuil'] * 2
        else:
            suggestion = 5

    return jsonify(suggestion=suggestion, consommation=consommation)