import math
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify)
from sqlalchemy import func, or_

# NOUVEAUX IMPORTS
from db import db, Objet, Armoire, Categorie, Reservation, Utilisateur, Historique, Echeance, Budget, Depense
from utils import login_required, admin_required, limit_objets_required
from .api import get_paginated_objets

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
    etablissement_id = session.get('etablissement_id')
    user_id = session.get('user_id')
    if not etablissement_id:
        flash("Erreur critique : session invalide. Veuillez vous reconnecter.", "error")
        return redirect(url_for('auth.logout'))
    
    dashboard_data = {}

    # --- Widget Statistiques (déjà fonctionnel) ---
    if session.get('user_role') == 'admin':
        dashboard_data['stats'] = {
            'total_objets': db.session.query(Objet).filter_by(etablissement_id=etablissement_id).count(),
            'total_utilisateurs': db.session.query(Utilisateur).filter_by(etablissement_id=etablissement_id).count(),
            'reservations_actives': db.session.query(Reservation).filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation >= datetime.now()
            ).count()
        }

    # --- Widget Nouveautés & Contact (déjà fonctionnel) ---
    admin_user = db.session.execute(db.select(Utilisateur).filter_by(role='admin', etablissement_id=etablissement_id)).scalar_one_or_none()
    dashboard_data['admin_contact'] = admin_user.email if admin_user and admin_user.email else (admin_user.nom_utilisateur if admin_user else "Non défini")
    
    vingt_quatre_heures_avant = datetime.now() - timedelta(hours=24)
    objets_recents = db.session.execute(db.select(Objet.id, Objet.nom).join(Historique, Objet.id == Historique.objet_id).filter(Objet.etablissement_id == etablissement_id, Historique.timestamp >= vingt_quatre_heures_avant, or_(Historique.action == 'Création', (Historique.action == 'Modification') & (Historique.details.like('%Quantité%')))).group_by(Objet.id, Objet.nom).order_by(db.desc(func.max(Historique.timestamp))).limit(10)).mappings().all()
    dashboard_data['objets_recents'] = objets_recents

    # --- DÉBUT DE LA NOUVELLE LOGIQUE POUR LES ÉCHÉANCES ---
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
    # --- FIN DE LA NOUVELLE LOGIQUE ---

    # --- DÉBUT DE LA NOUVELLE LOGIQUE POUR LES RÉSERVATIONS ---
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
    # --- FIN DE LA NOUVELLE LOGIQUE ---

    # --- DÉBUT DE LA NOUVELLE LOGIQUE POUR LE BUDGET ---
    now = datetime.now()
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
    # --- FIN DE LA NOUVELLE LOGIQUE ---

    # --- DÉBUT DE LA NOUVELLE LOGIQUE POUR L'HISTORIQUE ---
    # 1. On récupère les 5 dernières réservations de l'utilisateur
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

    # 2. On récupère les 5 dernières autres actions de l'utilisateur
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

    # 3. On fusionne les deux listes et on les trie
    all_actions = list(recent_reservations) + list(other_actions)
    # On trie par la clé 'timestamp', du plus récent au plus ancien
    all_actions.sort(key=lambda x: x['timestamp'], reverse=True)

    # On ne garde que les 5 actions les plus récentes au total
    top_5_actions = all_actions[:5]

    # 4. On enrichit les données pour l'affichage (logique conservée)
    historique_enrichi = []
    for action in top_5_actions:
        entry = {'timestamp': action['timestamp']}
        if 'groupe_id' in action: 
            entry['type'] = 'reservation'
            entry['action'] = 'Réservation'
            # NOTE : La logique pour récupérer le contenu des kits et objets manuels
            # est complexe et sera réactivée dans un second temps.
            entry['kits'] = []
            entry['objets_manuels'] = ["Détails en cours de migration..."]
        else: 
            entry['type'] = 'autre'
            entry['action'] = action['action']
            entry['details'] = f"{action['objet_nom']}"
        historique_enrichi.append(entry)

    dashboard_data['historique_recent'] = historique_enrichi
    # --- FIN DE LA NOUVELLE LOGIQUE ---

    start_tour = db.session.query(Armoire).filter_by(etablissement_id=etablissement_id).count() == 0
    
    return render_template("index.html", start_tour=start_tour, now=datetime.now(), data=dashboard_data)


@inventaire_bp.route("/inventaire")
@login_required
def inventaire():
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

    # On construit le VRAI dictionnaire de pagination
    pagination = {
        'page': page,
        'total_pages': total_pages,
        'endpoint': 'inventaire.inventaire' # <-- L'attribut manquant est maintenant là !
    }
    
    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()

    return render_template("inventaire.html",
                           objets=objets,
                           armoires=armoires,
                           categories=categories,
                           pagination=pagination,
                           date_actuelle=datetime.now(),
                           now=datetime.now,
                           sort_by=sort_by,
                           direction=direction,
                           is_general_inventory=True)

# ============================================================
# ROUTES DE GESTION DES OBJETS (CRUD)
# ============================================================

@inventaire_bp.route("/ajouter_objet", methods=["POST"])
@login_required
@limit_objets_required
def ajouter_objet():
    etablissement_id = session['etablissement_id']
    try:
        new_objet = Objet(
            nom=request.form.get("nom", "").strip(),
            quantite_physique=int(request.form.get("quantite")),
            seuil=int(request.form.get("seuil")),
            armoire_id=int(request.form.get("armoire_id")),
            categorie_id=int(request.form.get("categorie_id")),
            date_peremption=request.form.get("date_peremption") or None,
            image_url=request.form.get("image_url", "").strip() or None,
            fds_url=request.form.get("fds_url", "").strip() or None,
            etablissement_id=etablissement_id
        )
        db.session.add(new_objet)
        db.session.commit()
        flash(f"L'objet '{new_objet.nom}' a été ajouté avec succès !", "success")
    except (ValueError, TypeError):
        flash("Données invalides. Veuillez vérifier les champs numériques.", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue : {e}", "error")
        
    return redirect(request.referrer or url_for('inventaire.index'))

@inventaire_bp.route("/modifier_objet/<int:id_objet>", methods=["POST"])
@login_required
def modifier_objet(id_objet):
    objet = db.session.get(Objet, id_objet)
    if not objet or objet.etablissement_id != session['etablissement_id']:
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    try:
        objet.nom = request.form.get("nom", "").strip()
        objet.quantite_physique = int(request.form.get("quantite"))
        objet.seuil = int(request.form.get("seuil"))
        objet.armoire_id = int(request.form.get("armoire_id"))
        objet.categorie_id = int(request.form.get("categorie_id"))
        objet.date_peremption = request.form.get("date_peremption") or None
        objet.image_url = request.form.get("image_url", "").strip() or None
        objet.fds_url = request.form.get("fds_url", "").strip() or None
        
        db.session.commit()
        flash(f"L'objet '{objet.nom}' a été mis à jour avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue : {e}", "error")

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
        db.session.delete(objet)
        db.session.commit()
        flash(f"L'objet '{nom_objet}' a été supprimé.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue : {e}", "error")

    return redirect(request.referrer or url_for('inventaire.inventaire'))


@inventaire_bp.route("/objet/<int:objet_id>")
@login_required
def voir_objet(objet_id):
    etablissement_id = session['etablissement_id']
    now = datetime.now()
    subquery = db.session.query(
        Reservation.objet_id,
        func.sum(Reservation.quantite_reservee).label('total_reserve')
    ).filter(
        Reservation.etablissement_id == etablissement_id,
        Reservation.fin_reservation > now
    ).group_by(Reservation.objet_id).subquery()

    result = db.session.execute(
        db.select(
            Objet,
            Armoire.nom.label('armoire_nom'),
            Categorie.nom.label('categorie_nom'),
            (Objet.quantite_physique - func.coalesce(subquery.c.total_reserve, 0)).label('quantite_disponible')
        )
        .join(Armoire, Objet.armoire_id == Armoire.id)
        .join(Categorie, Objet.categorie_id == Categorie.id)
        .outerjoin(subquery, Objet.id == subquery.c.objet_id)
        .filter(
            Objet.id == objet_id,
            Objet.etablissement_id == etablissement_id
        )
    ).first()

    if not result:
        flash("Objet non trouvé ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    objet = result.Objet
    objet.quantite_disponible = result.quantite_disponible
    objet.armoire_nom = result.armoire_nom
    objet.categorie_nom = result.categorie_nom
    historique = db.session.execute(
        db.select(Historique, Utilisateur.nom_utilisateur)
        .join(Utilisateur, Historique.utilisateur_id == Utilisateur.id)
        .filter(
            Historique.objet_id == objet_id,
            Historique.etablissement_id == etablissement_id
        )
        .order_by(Historique.timestamp.desc())
    ).all()

    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()
    
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
    etablissement_id = session['etablissement_id']
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')
    
    armoire = db.session.get(Armoire, armoire_id)
    if not armoire or armoire.etablissement_id != etablissement_id:
        flash("Armoire non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    objets, total_pages = get_paginated_objets(
        etablissement_id=etablissement_id, 
        page=page, 
        sort_by=sort_by, 
        direction=direction,
        armoire_id=armoire_id
    )

    pagination = {
        'page': page,
        'total_pages': total_pages,
        'endpoint': 'inventaire.voir_armoire',
        'armoire_id': armoire_id
    }

    # --- AJOUT : Récupérer la liste des autres armoires pour la liste déroulante ---
    autres_armoires = db.session.execute(
        db.select(Armoire)
        .filter(
            Armoire.etablissement_id == etablissement_id,
            Armoire.id != armoire_id  # On exclut l'armoire actuelle
        )
        .order_by(Armoire.nom)
    ).scalars().all()

    return render_template("armoire.html",
                           armoire=armoire,
                           objets=objets,
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           autres_armoires=autres_armoires, # <-- On passe la liste au template
                           now=datetime.now())

#==============================================================================
#  ROUTE AFFICHAGE CATEGORIES
#==============================================================================
@inventaire_bp.route("/categorie/<int:categorie_id>")
@login_required
def voir_categorie(categorie_id):
    etablissement_id = session['etablissement_id']
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'nom')
    direction = request.args.get('direction', 'asc')

    categorie = db.session.get(Categorie, categorie_id)
    if not categorie or categorie.etablissement_id != etablissement_id:
        flash("Catégorie non trouvée ou accès non autorisé.", "error")
        return redirect(url_for('inventaire.index'))

    objets, total_pages = get_paginated_objets(
        etablissement_id=etablissement_id, 
        page=page, 
        sort_by=sort_by, 
        direction=direction,
        categorie_id=categorie_id
    )

    pagination = {
        'page': page,
        'total_pages': total_pages,
        'endpoint': 'inventaire.voir_categorie',
        'categorie_id': categorie_id
    }

    # --- AJOUT : Récupérer la liste des autres catégories pour la liste déroulante ---
    categories_list = db.session.execute(
        db.select(Categorie)
        .filter(
            Categorie.etablissement_id == etablissement_id,
            Categorie.id != categorie_id # On exclut la catégorie actuelle
        )
        .order_by(Categorie.nom)
    ).scalars().all()

    return render_template("categorie.html",
                           categorie=categorie,
                           objets=objets,
                           pagination=pagination,
                           sort_by=sort_by,
                           direction=direction,
                           categories_list=categories_list, # <-- On passe la liste au template
                           now=datetime.now())
                           
#=======================================================
# ROUTE GESTION ALERTES TRAITEES
#=======================================================
@inventaire_bp.route("/maj_traite/<int:objet_id>", methods=["POST"])
@login_required
def maj_traite(objet_id):
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    
    objet = db.session.get(Objet, objet_id)

    # SÉCURITÉ : On vérifie que l'objet existe et appartient bien à l'établissement
    if not objet or objet.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Objet non trouvé ou accès non autorisé."), 404

    try:
        # On met à jour le statut "traité"
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

    # SÉCURITÉ : On vérifie que l'objet existe et appartient bien à l'établissement
    if not objet or objet.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Objet non trouvé ou accès non autorisé."), 404

    try:
        # On met à jour le statut "en_commande"
        objet.en_commande = 1 if data.get("en_commande") else 0
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500