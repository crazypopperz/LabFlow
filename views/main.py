# ============================================================
# IMPORTS
# ============================================================

# Imports depuis la bibliothèque standard
import os
from datetime import datetime, date, timedelta
import sqlite3

# Imports depuis les bibliothèques tierces (Flask)
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, send_file, send_from_directory, current_app)

# Imports depuis nos propres modules
from db import get_db, get_all_armoires, get_all_categories
from utils import login_required

# ============================================================
# CRÉATION DU BLUEPRINT PRINCIPAL
# ============================================================
main_bp = Blueprint(
    'main', 
    __name__,
    template_folder='../templates'
)

# ============================================================
# LES FONCTIONS DE ROUTES SERONT COLLÉES ICI
# ============================================================
@main_bp.route("/calendrier")
@login_required
def calendrier():
    db = get_db()
    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    return render_template("calendrier.html",
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)

@main_bp.route("/jour/<string:date_str>")
@login_required
def vue_jour(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Format de date invalide.", "error")
        return redirect(url_for('main.calendrier'))

    db = get_db()
    start_of_day = datetime.strptime(f"{date_str} 00:00:00", '%Y-%m-%d %H:%M:%S')
    end_of_day = datetime.strptime(f"{date_str} 23:59:59", '%Y-%m-%d %H:%M:%S')

    reservations_brutes = db.execute(
        """
        SELECT
            r.groupe_id, r.debut_reservation, r.fin_reservation,
            u.nom_utilisateur
        FROM reservations r
        JOIN utilisateurs u ON r.utilisateur_id = u.id
        WHERE datetime(r.debut_reservation) <= ? AND datetime(r.fin_reservation) > ?
        GROUP BY r.groupe_id, r.debut_reservation, r.fin_reservation, u.nom_utilisateur
        ORDER BY r.debut_reservation
        """, (end_of_day.strftime('%Y-%m-%d %H:%M:%S'), start_of_day.strftime('%Y-%m-%d %H:%M:%S'))).fetchall()

    reservations_par_heure = {hour: {'starts': [], 'continues': []} for hour in range(24)}

    for resa in reservations_brutes:
        debut_dt = datetime.fromisoformat(resa['debut_reservation'])
        fin_dt = datetime.fromisoformat(resa['fin_reservation'])

        start_hour = max(8, debut_dt.hour)
        end_hour = min(20, fin_dt.hour if fin_dt.minute > 0 else fin_dt.hour - 1)

        if debut_dt.date() == date_obj:
            reservations_par_heure[debut_dt.hour]['starts'].append(dict(resa))
        
        for hour in range(start_hour + 1, end_hour + 1):
            if hour >= 8 and hour <= 20:
                # On vérifie que le bloc n'est pas déjà présent (cas de plusieurs objets pour un même groupe_id)
                if not any(d.get('groupe_id') == resa['groupe_id'] for d in reservations_par_heure[hour]['continues']):
                    reservations_par_heure[hour]['continues'].append(dict(resa))

    return render_template("vue_jour.html",
                           date_concernee=date_obj,
                           reservations_par_heure=reservations_par_heure)

@main_bp.route("/panier")
@login_required
def panier():
    return render_template("panier.html")

@main_bp.route("/alertes")
@login_required
def alertes():
    db = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    objets_stock_query = """
        SELECT o.id, o.nom, o.quantite_physique, o.seuil, a.nom AS armoire,
            c.nom AS categorie, o.image, o.en_commande,
            o.date_peremption, o.traite,
            (o.quantite_physique - COALESCE(SUM(r.quantite_reservee), 0)) as quantite_disponible
        FROM objets o 
        JOIN armoires a ON o.armoire_id = a.id
        JOIN categories c ON o.categorie_id = c.id
        LEFT JOIN reservations r ON o.id = r.objet_id AND r.fin_reservation > ?
        GROUP BY o.id
        HAVING quantite_disponible <= o.seuil 
        ORDER BY o.nom
    """
    objets_stock = db.execute(objets_stock_query, (now_str,)).fetchall()

    date_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    objets_peremption_query = """
        SELECT o.id, o.nom, o.quantite_physique, o.seuil, a.nom AS armoire,
               c.nom AS categorie, o.image, o.en_commande, o.date_peremption,
               o.traite,
               (o.quantite_physique - COALESCE(SUM(r.quantite_reservee), 0)) as quantite_disponible
        FROM objets o 
        JOIN armoires a ON o.armoire_id = a.id
        JOIN categories c ON o.categorie_id = c.id
        LEFT JOIN reservations r ON o.id = r.objet_id AND r.fin_reservation > ?
        WHERE o.date_peremption IS NOT NULL AND o.date_peremption < ?
        GROUP BY o.id
        ORDER BY o.date_peremption ASC
    """
    objets_peremption = db.execute(objets_peremption_query, (now_str, date_limite, )).fetchall()
    
    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    
    return render_template("alertes.html",
                           objets_stock=objets_stock,
                           objets_peremption=objets_peremption,
                           date_actuelle=datetime.now(),
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)

@main_bp.route("/fournisseurs")
@login_required
def voir_fournisseurs():
    db = get_db()
    fournisseurs = db.execute(
        "SELECT * FROM fournisseurs ORDER BY nom").fetchall()
    return render_template("fournisseurs.html", fournisseurs=fournisseurs)

@main_bp.route("/budget/voir")
@login_required
def voir_budget():
    db = get_db()
    now = datetime.now()
    
    # Logique de l'année scolaire : commence en septembre.
    annee_scolaire_actuelle = now.year if now.month >= 9 else now.year - 1
    
    budget_actuel = db.execute(
        "SELECT * FROM budgets WHERE annee = ? AND cloture = 0",
        (annee_scolaire_actuelle, )).fetchone()

    depenses = []
    total_depenses = 0
    solde = 0

    if budget_actuel:
        depenses = db.execute(
            """SELECT d.id, d.contenu, d.montant, d.date_depense,
                      d.est_bon_achat, d.fournisseur_id, f.nom as fournisseur_nom
            FROM depenses d
            LEFT JOIN fournisseurs f ON d.fournisseur_id = f.id
            WHERE d.budget_id = ?
            ORDER BY d.date_depense DESC""",
            (budget_actuel['id'], )).fetchall()

        total_depenses_result = db.execute(
            "SELECT SUM(montant) as total FROM depenses WHERE budget_id = ?",
            (budget_actuel['id'], )).fetchone()
        total_depenses = (total_depenses_result['total']
                          if total_depenses_result['total'] is not None else 0)
        solde = budget_actuel['montant_initial'] - total_depenses

    return render_template("budget_voir.html",
                           budget_actuel=budget_actuel,
                           depenses=depenses,
                           total_depenses=total_depenses,
                           solde=solde)

@main_bp.route("/gestion_armoires")
@login_required
def gestion_armoires():
    db = get_db()
    armoires = db.execute("""
        SELECT a.id, a.nom, COUNT(o.id) as count FROM armoires a
        LEFT JOIN objets o ON a.id = o.armoire_id
        GROUP BY a.id, a.nom ORDER BY a.nom
        """).fetchall()
    categories = get_all_categories(db)
    return render_template("gestion_armoires.html",
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)


@main_bp.route("/gestion_categories")
@login_required
def gestion_categories():
    db = get_db()
    categories = db.execute("""
        SELECT c.id, c.nom, COUNT(o.id) as count FROM categories c
        LEFT JOIN objets o ON c.id = o.categorie_id
        GROUP BY c.id, c.nom ORDER BY c.nom
        """).fetchall()
    armoires = get_all_armoires(db)
    return render_template("gestion_categories.html",
                           categories=categories,
                           armoires=armoires,
                           now=datetime.now)

@main_bp.route("/a-propos")
@login_required
def a_propos():
    return render_template("a_propos.html")

@main_bp.route("/objet/<int:objet_id>/telecharger_fds")
@login_required
def telecharger_fds_objet(objet_id):
    db = get_db()
    objet = db.execute(
        "SELECT fds_nom_original, fds_nom_securise FROM objets WHERE id = ?",
        (objet_id, )).fetchone()
    if objet and objet['fds_nom_securise']:
        try:
            return send_file(os.path.join(current_app.config['FDS_UPLOAD_FOLDER'],
                                          objet['fds_nom_securise']),
                             as_attachment=True,
                             download_name=objet['fds_nom_original'])
        except FileNotFoundError:
            flash("Le fichier FDS n'a pas été trouvé sur le serveur.", "error")
            return redirect(url_for('inventaire.details_objet', objet_id=objet_id))
    else:
        flash("Cet objet n'a pas de FDS associée.", "error")
        return redirect(url_for('inventaire.details_objet', objet_id=objet_id))

@main_bp.route('/uploads/images/<path:filename>')
@login_required
def serve_image(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'icons'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')