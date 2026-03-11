from datetime import datetime, timedelta
import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_from_directory, current_app, make_response)
from sqlalchemy import func, desc, distinct
from sqlalchemy.orm import joinedload
from db import db, Armoire, Categorie, Fournisseur, Objet, Reservation, Utilisateur, Echeance, Depense, Budget, Parametre, Suggestion, MaintenanceLog, EquipementSecurite, Salle
from utils import login_required

main_bp = Blueprint(
    'main', 
    __name__,
    template_folder='../templates'
)

#============================================================
# ROUTE RACINE (ACCUEIL)
#============================================================
@main_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('inventaire.index'))
    return redirect(url_for('auth.login'))

    
#============================================================
# GESTION ARMOIRES (LOGIQUE RESTAURÉE)
#============================================================
@main_bp.route("/gestion_armoires")
@login_required
def gestion_armoires():
    etablissement_id = session['etablissement_id']
    
    armoires = db.session.execute(
        db.select(
            Armoire.id, 
            Armoire.nom, 
            Armoire.description,
            Armoire.photo_url,
            func.count(Objet.id).label('count')
        )
        .outerjoin(Objet, Armoire.id == Objet.armoire_id)
        .filter(Armoire.etablissement_id == etablissement_id)
        .group_by(Armoire.id, Armoire.nom, Armoire.description, Armoire.photo_url)  # ← MODIFIÉ
        .order_by(Armoire.nom)
    ).mappings().all()
    
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Gérer les Armoires', 'url': None}
    ]
    
    return render_template("gestion_armoires.html",
                           armoires=armoires,
                           breadcrumbs=breadcrumbs
                           )

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
                           breadcrumbs=breadcrumbs
                           )

#================================================================
#  GESTION CALENDRIER (SECTION MODIFIÉE)
#================================================================
@main_bp.route('/calendrier')
@login_required
def calendrier():
    etablissement_id = session.get('etablissement_id')
    
    # Gestion du mois affiché (par défaut mois courant)
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # 1. Récupération des jours avec réservations pour ce mois
    # On groupe par jour et on compte les groupes de réservation distincts
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    stats_res = db.session.execute(
        db.select(
            func.date(Reservation.debut_reservation).label('jour'), 
            func.count(func.distinct(Reservation.groupe_id)).label('total')
        )
        .filter(
            Reservation.etablissement_id == etablissement_id,
            Reservation.debut_reservation >= start_date,
            Reservation.debut_reservation < end_date,
            Reservation.statut == 'confirmée'
        )
        .group_by(func.date(Reservation.debut_reservation))
    ).all()

    # 2. Transformation en Dictionnaire pour accès rapide dans le template
    # Format : {'2025-12-28': 2, '2025-12-29': 1}
    reservations_map = {str(row.jour): row.total for row in stats_res}
    
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Calendrier', 'url': None}
    ]

    return render_template(
        'calendrier.html', 
        year=year, 
        month=month, 
        reservations_map=reservations_map,
        breadcrumbs=breadcrumbs
    )


@main_bp.route("/calendrier/<date_str>")
@login_required
def vue_jour(date_str):
    try:
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

        # Lecture config planning
        from utils import get_etablissement_params
        params = get_etablissement_params(etablissement_id)
        planning_debut = params.get('planning_debut', '08:00')
        planning_fin = params.get('planning_fin', '18:00')

        start_of_day = datetime.combine(date_obj, datetime.min.time())
        end_of_day = datetime.combine(date_obj, datetime.max.time())

        subq = (
            db.select(
                Reservation.groupe_id,
                db.func.min(Reservation.debut_reservation).label('debut'),
                db.func.min(Reservation.fin_reservation).label('fin'),
                db.func.min(Reservation.salle_id).label('salle_id'),
                db.func.min(Reservation.utilisateur_id).label('utilisateur_id')
            )
            .filter(
                Reservation.etablissement_id == etablissement_id,
                Reservation.debut_reservation < end_of_day,
                Reservation.fin_reservation > start_of_day
            )
            .group_by(Reservation.groupe_id)
            .subquery()
        )
        reservations_brutes = db.session.execute(
            db.select(
                subq.c.groupe_id,
                subq.c.debut,
                subq.c.fin,
                subq.c.salle_id,
                subq.c.utilisateur_id.label('resa_utilisateur_id'),
                Utilisateur.nom_utilisateur,
                Salle.nom.label('salle_nom')
            )
            .join(Utilisateur, Utilisateur.id == subq.c.resa_utilisateur_id)
            .outerjoin(Salle, Salle.id == subq.c.salle_id)
            .order_by(subq.c.debut)
        ).mappings().all()

        # Structure plate — le JS gérera le positionnement
        reservations = []
        for resa in reservations_brutes:
            reservations.append({
                'groupe_id': str(resa.groupe_id),
                'debut': resa.debut.strftime('%H:%M'),
                'fin': resa.fin.strftime('%H:%M'),
                'nom_utilisateur': str(resa.nom_utilisateur or ''),
                'salle': str(resa.salle_nom or ''),
                'salle_id': str(resa.salle_id) if resa.salle_id is not None else '',
                'user_id': str(int(resa.resa_utilisateur_id)) if resa.resa_utilisateur_id is not None else ''
            })
        
        # Filtres calendrier
        from db import Salle
        salles_dispo = db.session.execute(
            db.select(Salle)
            .filter_by(etablissement_id=etablissement_id)
            .order_by(Salle.nom)
        ).scalars().all()

        utilisateurs_dispo = db.session.execute(
            db.select(Utilisateur.id, Utilisateur.nom_utilisateur)
            .filter_by(etablissement_id=etablissement_id)
            .order_by(Utilisateur.nom_utilisateur)
        ).mappings().all()
        
        return render_template("vue_jour.html",
                               date_concernee=date_obj,
                               reservations=reservations,
                               planning_debut=planning_debut,
                               planning_fin=planning_fin,
                               salles=salles_dispo,
                               utilisateurs=utilisateurs_dispo,
                               breadcrumbs=breadcrumbs)
    except Exception as e:
        current_app.logger.error(f"ERREUR VUE_JOUR: {e}", exc_info=True)
        raise

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
            Objet.traite == False
        ).order_by(Objet.date_peremption.asc()).all()
    
    # 4. Suggestions
    suggestions = db.session.execute(
        db.select(Suggestion)
        .options(joinedload(Suggestion.objet), joinedload(Suggestion.utilisateur))
        .filter_by(etablissement_id=etablissement_id, statut='En attente')
        .order_by(Suggestion.date_demande.desc())
    ).scalars().all()
    
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Centre d\'Alertes', 'url': None}
    ]
    
    signalements_securite = []
    signalements_securite = db.session.execute(
        db.select(MaintenanceLog)
        .join(EquipementSecurite)
        .filter(EquipementSecurite.etablissement_id == etablissement_id)
        .filter(MaintenanceLog.resultat == 'signalement')
        .order_by(MaintenanceLog.date_intervention.desc())
    ).scalars().all()
    
    return render_template("alertes.html",
                           objets_stock=objets_stock_results,
                           objets_peremption=objets_peremption,
                           suggestions=suggestions,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=now,
                           signalements_securite=signalements_securite,
                           now=now
                           )

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
    
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Annuaire Fournisseurs', 'url': None}
    ]
    
    return render_template("fournisseurs.html", 
                           fournisseurs=fournisseurs,
                           breadcrumbs=breadcrumbs
                           )

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
                           licence=licence_info
                           )



# ================================================================
# GESTION BUDGET (Lecture pour tous, Admin pour modifs)
# ================================================================
@main_bp.route("/budget")
@login_required
def voir_budget():
    etablissement_id = session['etablissement_id']
    
    # 1. Déterminer l'année scolaire
    now = datetime.now()
    annee_courante = now.year if now.month >= 9 else now.year - 1
    
    # 2. Récupérer le budget
    budget = db.session.execute(
        db.select(Budget).filter_by(
            etablissement_id=etablissement_id,
            annee=annee_courante
        )
    ).scalar_one_or_none()
    
    # 3. Calculs
    depenses = []
    total_depenses = 0
    solde = 0
    
    if budget:
        # Récupérer les dépenses liées
        depenses = db.session.execute(
            db.select(Depense)
            .options(joinedload(Depense.fournisseur))
            .filter_by(budget_id=budget.id)
            .order_by(Depense.date_depense.desc())
        ).scalars().all()
        
        total_depenses = sum(d.montant for d in depenses)
        solde = budget.montant_initial - total_depenses

    # 4. Fil d'ariane
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Suivi Budgétaire', 'url': None}
    ]

    # 5. Liste des fournisseurs (pour la modale d'ajout, si admin)
    fournisseurs = []
    if session.get('user_role') == 'admin':
        fournisseurs = db.session.execute(
            db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)
        ).scalars().all()

    return render_template("budget.html",
                           budget_affiche=budget,
                           depenses=depenses,
                           total_depenses=total_depenses,
                           solde=solde,
                           annee=annee_courante,
                           fournisseurs=fournisseurs,
                           breadcrumbs=breadcrumbs,
                           now=now
                           )


#================================================================
# PAGES DU FOOTER
#================================================================
@main_bp.route("/documentation")
@login_required
def documentation():
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Documentation', 'url': None}
    ]
    return render_template("documentation.html", breadcrumbs=breadcrumbs)

@main_bp.route("/legal")
# Pas de @login_required ici, les mentions légales doivent être publiques
def legal():
    breadcrumbs = [
        {'text': 'Accueil', 'url': url_for('inventaire.index')},
        {'text': 'Mentions Légales', 'url': None}
    ]
    return render_template("legal.html", breadcrumbs=breadcrumbs)


# ================================================================
# THÈME DYNAMIQUE
# ================================================================
@main_bp.route('/theme.css')
def theme_css():
    """Génère le CSS de thème dynamiquement selon les paramètres de l'établissement."""
    etablissement_id = session.get('etablissement_id')
    
    # Valeurs par défaut
    couleur_principale = '#1f3b73'
    couleur_secondaire = '#01257d'
    logo_url = None

    if etablissement_id:
        try:
            params = db.session.execute(
                db.select(Parametre).filter(
                    Parametre.etablissement_id == etablissement_id,
                    Parametre.cle.in_(['couleur_principale', 'couleur_secondaire', 'logo_url'])
                )
            ).scalars().all()
            params_dict = {p.cle: p.valeur for p in params}
            couleur_principale = params_dict.get('couleur_principale', couleur_principale)
            couleur_secondaire = params_dict.get('couleur_secondaire', couleur_secondaire)
            logo_url = params_dict.get('logo_url')
        except Exception:
            pass

    css = f"""
:root {{
    --couleur-principale: {couleur_principale};
    --couleur-secondaire: {couleur_secondaire};
}}
"""
    if logo_url:
        css += f"""
.brand-logo-svg {{ display: none !important; }}
.brand-logo-img {{ display: block !important; }}
"""
    else:
        css += """
.brand-logo-img { display: none !important; }
.brand-logo-svg { display: block !important; }
"""

    response = make_response(css)
    response.headers['Content-Type'] = 'text/css'
    response.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return response


#================================================================
#  GESTION FAVICON
#================================================================
@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'icons'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


