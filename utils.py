import sqlite3
import os
from db import get_db
from flask import current_app, session, flash, redirect, url_for, request, g
from functools import wraps
from datetime import datetime, timedelta
from fpdf import FPDF

def is_setup_needed(app):
    """
    Vérifie si l'application a besoin d'être configurée.
    La configuration est considérée comme terminée s'il existe au moins un utilisateur admin.
    """
    db_path = app.config['DATABASE']

    if not os.path.exists(db_path):
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM utilisateurs WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        conn.close()
        
        return admin_count == 0

    except sqlite3.OperationalError:
        return True

# --- DÉCORATEURS DE SÉCURITÉ ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash("Accès réservé aux administrateurs.", "error")
            return redirect(url_for('inventaire.index'))
        return f(*args, **kwargs)
    return decorated_function

def pro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db = get_db()
        try:
            licence_row = db.execute("SELECT valeur FROM parametres WHERE cle = ?", ('licence_statut', )).fetchone()
            is_pro = licence_row and licence_row['valeur'] == 'PRO'
        except sqlite3.Error:
            is_pro = False
        if not is_pro:
            flash("Cette fonctionnalité est réservée à la version Pro.", "warning")
            return redirect(url_for('inventaire.index'))
        return f(*args, **kwargs)
    return decorated_function

def limit_objets_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db = get_db()
        licence_row = db.execute("SELECT valeur FROM parametres WHERE cle = ?", ('licence_statut', )).fetchone()
        is_pro = licence_row and licence_row['valeur'] == 'PRO'
        if not is_pro:
            count = db.execute("SELECT COUNT(id) FROM objets").fetchone()[0]
            if count >= 50:
                flash("La version gratuite est limitée à 50 objets. Passez à la version Pro pour en ajouter davantage.", "warning")
                return redirect(request.referrer or url_for('inventaire.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_alerte_info(db):
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        query_stock = """
            SELECT COUNT(*) FROM (
            SELECT 
                o.seuil,
                (o.quantite_physique - COALESCE(SUM(r.quantite_reservee), 0)) as quantite_disponible
            FROM objets o
            LEFT JOIN reservations r ON o.id = r.objet_id AND r.fin_reservation > ?
            WHERE o.en_commande = 0
            GROUP BY o.id
            HAVING quantite_disponible <= o.seuil
            )
        """
        result_stock = db.execute(query_stock, (now_str,)).fetchone()
        count_stock = result_stock[0] if result_stock else 0

        query_peremption = "SELECT COUNT(*) FROM objets WHERE date_peremption IS NOT NULL AND date_peremption < ? AND traite = 0"
        result_peremption = db.execute(query_peremption, (date_limite,)).fetchone()
        count_peremption = result_peremption[0] if result_peremption else 0
        
        total_alertes = count_stock + count_peremption
        
        return {
            "alertes_stock": count_stock,
            "alertes_peremption": count_peremption,
            "alertes_total": total_alertes
        }

    except (sqlite3.Error, TypeError) as e:
        print(f"ERREUR dans get_alerte_info: {e}")
        return {'alertes_total': 0, 'alertes_stock': 0, 'alertes_peremption': 0}

def get_items_per_page():
    if 'items_per_page' not in g:
        db = get_db()
        param = db.execute("SELECT valeur FROM parametres WHERE cle = ?", ('items_per_page',)).fetchone()
        g.items_per_page = int(param['valeur']) if param else 10
    return g.items_per_page

class PDFWithFooter(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='R')

def enregistrer_action(objet_id, action, details=""):
    if 'user_id' in session:
        db = get_db()
        try:
            db.execute(
                """INSERT INTO historique (objet_id, utilisateur_id, action,
                   details, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (objet_id, session['user_id'], action, details,
                 datetime.now()))
            db.commit()
        except sqlite3.Error as e:
            print(f"ERREUR LORS DE L'ENREGISTREMENT DE L'HISTORIQUE : {e}")
            db.rollback()

def annee_scolaire_format(year):
    if isinstance(year, int):
        return f"{year}-{year + 1}"
    return year