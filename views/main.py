from datetime import datetime, timedelta
import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_from_directory, current_app)
from sqlalchemy import func
from sqlalchemy.orm import joinedload
# NOUVEAUX IMPORTS
from db import db, Armoire, Categorie, Fournisseur, Objet, Reservation, Utilisateur
from utils import login_required

main_bp = Blueprint(
    'main', 
    __name__,
    template_folder='../templates'
)

#============================================================
# GESTION ARMOIRES
#============================================================
@main_bp.route("/gestion_armoires")
@login_required
def gestion_armoires():
    etablissement_id = session['etablissement_id']
    
    # NOUVELLE REQUÊTE : On utilise une jointure pour compter les objets dans chaque armoire.
    armoires = db.session.execute(
        db.select(Armoire.id, Armoire.nom, func.count(Objet.id).label('count'))
        .outerjoin(Objet, Armoire.id == Objet.armoire_id)
        .filter(Armoire.etablissement_id == etablissement_id)
        .group_by(Armoire.id, Armoire.nom)
        .order_by(Armoire.nom)
    ).mappings().all() # .mappings().all() transforme le résultat en une liste de dictionnaires

    return render_template("gestion_armoires.html",
                           armoires=armoires,
                           now=datetime.now())

#============================================================
# GESTION CATEGORIES
#============================================================
@main_bp.route("/gestion_categories")
@login_required
def gestion_categories():
    etablissement_id = session['etablissement_id']

    # NOUVELLE REQUÊTE : Même chose pour les catégories.
    categories = db.session.execute(
        db.select(Categorie.id, Categorie.nom, func.count(Objet.id).label('count'))
        .outerjoin(Objet, Categorie.id == Objet.categorie_id)
        .filter(Categorie.etablissement_id == etablissement_id)
        .group_by(Categorie.id, Categorie.nom)
        .order_by(Categorie.nom)
    ).mappings().all()

    return render_template("gestion_categories.html",
                           categories=categories,
                           now=datetime.now())
 
#================================================================
#  GESTION CALENDRIER
#================================================================
@main_bp.route("/calendrier")
@login_required
def calendrier():
    return render_template("calendrier.html", now=datetime.now())


@main_bp.route("/jour/<string:date_str>")
@login_required
def vue_jour(date_str):
    etablissement_id = session['etablissement_id']
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Format de date invalide.", "error")
        return redirect(url_for('main.calendrier'))

    # On définit le début et la fin de la journée
    start_of_day = datetime.combine(date_obj, datetime.min.time())
    end_of_day = datetime.combine(date_obj, datetime.max.time())

    # NOUVELLE REQUÊTE SQLAlchemy
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
            Reservation.debut_reservation <= end_of_day,
            Reservation.fin_reservation >= start_of_day
        )
        .group_by(Reservation.groupe_id, Reservation.debut_reservation, Reservation.fin_reservation, Utilisateur.nom_utilisateur)
        .order_by(Reservation.debut_reservation)
    ).mappings().all()

    # Le reste de ta logique de formatage est conservé, car elle est bonne
    reservations_par_heure = {hour: {'starts': [], 'continues': []} for hour in range(24)}
    for resa in reservations_brutes:
        debut_dt = resa['debut_reservation']
        fin_dt = resa['fin_reservation']
        start_hour = max(8, debut_dt.hour)
        end_hour = min(20, fin_dt.hour if fin_dt.minute > 0 else fin_dt.hour - 1)

        if debut_dt.date() == date_obj:
            reservations_par_heure[debut_dt.hour]['starts'].append(dict(resa))
        
        for hour in range(start_hour + 1, end_hour + 1):
            if 8 <= hour <= 20:
                if not any(d.get('groupe_id') == resa['groupe_id'] for d in reservations_par_heure[hour]['continues']):
                    reservations_par_heure[hour]['continues'].append(dict(resa))

    return render_template("vue_jour.html",
                           date_concernee=date_obj,
                           reservations_par_heure=reservations_par_heure)

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
    # Sous-requête pour la quantité disponible (on la réutilise)
    subquery = db.session.query(
        Objet.id.label('objet_id'),
        (Objet.quantite_physique - func.coalesce(db.session.query(func.sum(Reservation.quantite_reservee))
            .filter(Reservation.objet_id == Objet.id, Reservation.fin_reservation > now)
            .scalar_subquery(), 0)).label('quantite_disponible')
    ).filter(Objet.etablissement_id == etablissement_id).subquery()

    # Requête pour récupérer les objets en alerte de stock
    objets_stock_results = db.session.query(Objet, subquery.c.quantite_disponible.label('quantite_disponible'))\
        .join(subquery, Objet.id == subquery.c.objet_id)\
        .options(*options)\
        .filter(
            Objet.etablissement_id == etablissement_id,
            subquery.c.quantite_disponible <= Objet.seuil
        ).order_by(Objet.nom).all()

    # Requête pour récupérer les objets en alerte de péremption
    date_limite = (now + timedelta(days=30)).date()
    objets_peremption = db.session.query(Objet)\
        .options(*options)\
        .filter(
            Objet.etablissement_id == etablissement_id,
            Objet.date_peremption != None,
            func.date(Objet.date_peremption) < date_limite,
            Objet.traite == 0
        ).order_by(Objet.date_peremption.asc()).all()
    
    return render_template("alertes.html",
                           objets_stock=objets_stock_results,
                           objets_peremption=objets_peremption,
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
    return render_template("panier.html")

#================================================================
#  GESTION PAGE A PROPOS
#================================================================
@main_bp.route("/a-propos")
@login_required
def a_propos():
    return render_template("a_propos.html")

#================================================================
#  GESTION FAVICON
#================================================================
@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'icons'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ... Le reste des routes est neutralisé pour l'instant ...