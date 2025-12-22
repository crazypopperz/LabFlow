from datetime import datetime, timedelta
import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_from_directory, current_app)
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from db import db, Armoire, Categorie, Fournisseur, Objet, Reservation, Utilisateur, Echeance, Depense, Budget, Parametre, Suggestion
from utils import login_required

main_bp = Blueprint(
    'main', 
    __name__,
    template_folder='../templates'
)

    
#============================================================
# GESTION ARMOIRES (LOGIQUE RESTAURÉE)
#============================================================
@main_bp.route("/gestion_armoires")
@login_required
def gestion_armoires():
    etablissement_id = session['etablissement_id']
    
    armoires = db.session.execute(
        db.select(Armoire.id, Armoire.nom, func.count(Objet.id).label('count'))
        .outerjoin(Objet, Armoire.id == Objet.armoire_id)
        .filter(Armoire.etablissement_id == etablissement_id)
        .group_by(Armoire.id, Armoire.nom)
        .order_by(Armoire.nom)
    ).mappings().all()

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gérer les Armoires', 'url': None}
    ]

    return render_template("gestion_armoires.html",
                           armoires=armoires,
                           breadcrumbs=breadcrumbs,
                           now=datetime.now())

#============================================================
# GESTION CATEGORIES (LOGIQUE RESTAURÉE)
#============================================================
@main_bp.route("/gestion_categories")
@login_required
def gestion_categories():
    etablissement_id = session['etablissement_id']

    categories = db.session.execute(
        db.select(Categorie.id, Categorie.nom, func.count(Objet.id).label('count'))
        .outerjoin(Objet, Categorie.id == Objet.categorie_id)
        .filter(Categorie.etablissement_id == etablissement_id)
        .group_by(Categorie.id, Categorie.nom)
        .order_by(Categorie.nom)
    ).mappings().all()

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gérer les Catégories', 'url': None}
    ]

    return render_template("gestion_categories.html",
                           categories=categories,
                           breadcrumbs=breadcrumbs,
                           now=datetime.now())

#================================================================
#  GESTION CALENDRIER (SECTION MODIFIÉE)
#================================================================
@main_bp.route("/calendrier")
@login_required
def calendrier():
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Calendrier', 'url': None}
    ]
    return render_template("calendrier.html", now=datetime.now(), breadcrumbs=breadcrumbs)


@main_bp.route("/jour/<string:date_str>")
@login_required
def vue_jour(date_str):
    etablissement_id = session['etablissement_id']
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Format de date invalide.", "danger")
        return redirect(url_for('main.calendrier'))

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Calendrier', 'url': url_for('main.calendrier')},
        {'text': date_obj.strftime('%d %B %Y'), 'url': None}
    ]

    start_of_day = datetime.combine(date_obj, datetime.min.time())
    end_of_day = datetime.combine(date_obj, datetime.max.time())

    # La requête SQLAlchemy est bien présente et complète
    reservations_brutes = db.session.execute(
        db.select(
            Reservation.groupe_id,
            Reservation.debut_reservation,
            Reservation.fin_reservation,
            Utilisateur.nom_utilisateur
        )
        .join(Utilisateur, Reservation.utilisateur_id == Utilisateur.id)
        .filter(
            Reservation.etablissement_id == etablissement_id,
            Reservation.debut_reservation < end_of_day,
            Reservation.fin_reservation > start_of_day
        )
        .distinct(Reservation.groupe_id)
        .order_by(Reservation.groupe_id, Reservation.debut_reservation)
    ).mappings().all()

    # La logique de formatage des données est bien présente et complète
    reservations_par_heure = {hour: {'starts': [], 'continues': []} for hour in range(24)}
    for resa in reservations_brutes:
        debut_dt = resa.debut_reservation.replace(tzinfo=None)
        fin_dt = resa.fin_reservation.replace(tzinfo=None)

        start_hour = max(8, debut_dt.hour)
        end_hour = min(20, fin_dt.hour if fin_dt.minute > 0 or fin_dt.second > 0 else fin_dt.hour - 1)

        if debut_dt.date() == date_obj and 8 <= debut_dt.hour <= 20:
            reservations_par_heure[debut_dt.hour]['starts'].append(dict(resa))
        
        for hour in range(start_hour, end_hour + 1):
            if 8 <= hour <= 20:
                if hour != debut_dt.hour or debut_dt.date() != date_obj:
                    if not any(d.get('groupe_id') == resa.groupe_id for d in reservations_par_heure[hour]['continues']):
                        reservations_par_heure[hour]['continues'].append(dict(resa))

    # L'appel à render_template est bien présent et complet
    return render_template("vue_jour.html",
                           date_concernee=date_obj,
                           reservations_par_heure=reservations_par_heure,
                           breadcrumbs=breadcrumbs)

#================================================================
# GESTION ALERTES
#================================================================
@main_bp.route("/alertes")
@login_required
def alertes():
    etablissement_id = session['etablissement_id']
    now = datetime.now()

    options = [
        joinedload(Objet.armoire),
        joinedload(Objet.categorie)
    ]
    
    # 1. Sous-requête pour la quantité disponible
    subquery = db.session.query(
        Objet.id.label('objet_id'),
        (Objet.quantite_physique - func.coalesce(db.session.query(func.sum(Reservation.quantite_reservee))
            .filter(Reservation.objet_id == Objet.id, Reservation.fin_reservation > now)
            .scalar_subquery(), 0)).label('quantite_disponible')
    ).filter(Objet.etablissement_id == etablissement_id).subquery()

    # 2. Requête brute (Renvoie des Rows [Objet, quantite])
    rows_stock = db.session.query(Objet, subquery.c.quantite_disponible.label('quantite_disponible'))\
        .join(subquery, Objet.id == subquery.c.objet_id)\
        .options(*options)\
        .filter(
            Objet.etablissement_id == etablissement_id,
            subquery.c.quantite_disponible <= Objet.seuil
        ).order_by(Objet.nom).all()

    # --- CORRECTION ICI : On extrait l'objet de la Row ---
    objets_stock_results = []
    for row in rows_stock:
        # row[0] est l'objet, row[1] est la quantité disponible calculée
        obj = row[0] 
        # On peut attacher la quantité calculée à l'objet si on veut l'afficher
        obj.quantite_disponible_calc = row[1] 
        objets_stock_results.append(obj)
    # -----------------------------------------------------

    # 3. Requête Péremption (Celle-ci renvoie déjà des Objets, pas de souci)
    date_limite = (now + timedelta(days=30)).date()
    objets_peremption = db.session.query(Objet)\
        .options(*options)\
        .filter(
            Objet.etablissement_id == etablissement_id,
            Objet.date_peremption != None,
            func.date(Objet.date_peremption) < date_limite,
            Objet.traite == 0
        ).order_by(Objet.date_peremption.asc()).all()
    
    # 4. Suggestions
    suggestions = db.session.execute(
        db.select(Suggestion)
        .options(joinedload(Suggestion.objet), joinedload(Suggestion.utilisateur))
        .filter_by(etablissement_id=etablissement_id, statut='En attente')
        .order_by(Suggestion.date_demande.desc())
    ).scalars().all()

    return render_template("alertes.html",
                           objets_stock=objets_stock_results,
                           objets_peremption=objets_peremption,
                           suggestions=suggestions,
                           date_actuelle=now,
                           now=now)

#================================================================
# GESTION FOURNISSEURS
#================================================================
@main_bp.route("/fournisseurs")
@login_required
def voir_fournisseurs():
    etablissement_id = session['etablissement_id']
    
    # NOUVELLE REQUÊTE : On récupère tous les fournisseurs de l'établissement
    fournisseurs = db.session.execute(
        db.select(Fournisseur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Fournisseur.nom)
    ).scalars().all()
    
    return render_template("fournisseurs.html", fournisseurs=fournisseurs)

#================================================================
#  GESTION PANIER
#================================================================
@main_bp.route("/panier")
@login_required
def panier():
    # Définition du fil d'Ariane
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Mon Panier', 'url': None}
    ]
    return render_template("panier.html", breadcrumbs=breadcrumbs)

#================================================================
#  GESTION PAGE A PROPOS
#================================================================
@main_bp.route("/a-propos")
@login_required
def a_propos():
    etablissement_id = session.get('etablissement_id')
    
    # 1. Récupération des infos de licence (Indispensable pour le template)
    params = db.session.execute(
        db.select(Parametre).filter_by(etablissement_id=etablissement_id)
    ).scalars().all()
    
    params_dict = {p.cle: p.valeur for p in params}
    
    licence_info = {
        'is_pro': params_dict.get('licence_statut') == 'PRO',
        'instance_id': params_dict.get('instance_id', 'N/A'),
        'statut': params_dict.get('licence_statut', 'FREE')
    }

    # 2. Fil d'Ariane
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'À Propos', 'url': None}
    ]

    return render_template("a_propos.html", 
                           breadcrumbs=breadcrumbs,
                           licence=licence_info,
                           now=datetime.now())

#================================================================
#  GESTION FAVICON
#================================================================
@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'icons'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ... Le reste des routes est neutralisé pour l'instant ...