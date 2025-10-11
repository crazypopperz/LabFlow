# ============================================================
# IMPORTS
# ============================================================

# Imports depuis la bibliothèque standard
import hashlib
import os
from datetime import datetime, date, timedelta
from io import BytesIO
import sqlite3
import shutil

# Imports depuis les bibliothèques tierces (Flask, etc.)
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_file, current_app)
from fpdf import FPDF, XPos, YPos
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Imports depuis nos propres modules
from db import get_db, get_all_armoires, get_all_categories
from utils import admin_required, login_required, PDFWithFooter, annee_scolaire_format
# On importera d'autres fonctions de utils au besoin

# ============================================================
# CRÉATION DU BLUEPRINT POUR L'ADMINISTRATION
# ============================================================
admin_bp = Blueprint(
    'admin', 
    __name__,
    template_folder='../templates',
    url_prefix='/admin'
)

# ============================================================
# LES FONCTIONS DE ROUTES ADMIN
# ============================================================
@admin_bp.route("/")
@admin_required
def admin():
    db = get_db()
    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    return render_template("admin.html",
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)

@admin_bp.route("/importer")
@admin_required
def importer_page():
    db = get_db()
    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    
    breadcrumbs = [
        ('Panneau d\'Administration', url_for('admin.admin')),
        ('Importation en Masse', '#')
    ]

    return render_template("admin_import.html", 
                           breadcrumbs=breadcrumbs,
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)

#=== IMPORTATION FICHIER FICHIER EXCEL IMPORT MATERIEL ===
@admin_bp.route("/telecharger_modele")
@admin_required
def telecharger_modele_excel():

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventaire à Importer"

    headers = [
        "Nom",              # Obligatoire
        "Quantité",         # Obligatoire
        "Seuil",            # Obligatoire
        "Armoire",          # Obligatoire
        "Catégorie",        # Obligatoire
        "Date Péremption"   # Optionnel
    ]
    sheet.append(headers)

    header_font = Font(name='Calibri', bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")
    note_font = Font(name='Calibri', italic=True, color="808080")

    # On applique les styles à la première ligne (les en-têtes)
    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill

    # On ajuste la largeur des colonnes
    sheet.column_dimensions['A'].width = 40  # Nom
    sheet.column_dimensions['B'].width = 15  # Quantité
    sheet.column_dimensions['C'].width = 15  # Seuil
    sheet.column_dimensions['D'].width = 25  # Armoire
    sheet.column_dimensions['E'].width = 25  # Catégorie
    sheet.column_dimensions['F'].width = 25  # Date Péremption

    # On ajoute une note de format dans la cellule F2
    note_cell = sheet['F2']
    note_cell.value = "Format : AAAA-MM-JJ"
    note_cell.font = note_font

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='modele_import_inventaire.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@admin_bp.route("/importer", methods=['POST'])
@admin_required
def importer_fichier():
    # Pour l'instant, cette fonction ne fait rien d'utile.
    # Nous la compléterons à la prochaine étape.
    flash("La fonctionnalité d'importation est en cours de développement.", "info")
    return redirect(url_for('admin.importer_page'))

#=== GESTION UTILISATEURS ===
@admin_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    db = get_db()
    utilisateurs = db.execute(
        "SELECT id, nom_utilisateur, role, email FROM utilisateurs "
        "ORDER BY nom_utilisateur").fetchall()
    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
    {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin','icon_svg': icon_svg},
    {'text': 'Gestion Quotidienne'},
    {'text': 'Gestion des Utilisateurs'} # Le dernier n'a pas besoin de lien
    ]
    return render_template("admin_utilisateurs.html",
                           utilisateurs=utilisateurs,
                           breadcrumbs=breadcrumbs,
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)


#=== MODIFIER EMAIL ===
@admin_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    email = request.form.get('email', '').strip()
    if not email or '@' not in email:
        flash("Veuillez fournir une adresse e-mail valide.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    db = get_db()
    user = db.execute("SELECT nom_utilisateur FROM utilisateurs WHERE id = ?",
                      (id_user, )).fetchone()
    if not user:
        flash("Utilisateur non trouvé.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        db.execute("UPDATE utilisateurs SET email = ? WHERE id = ?",
                   (email, id_user))
        db.commit()
        flash(
            f"L'adresse e-mail pour '{user['nom_utilisateur']}' a été "
            "mise à jour.", "success")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))


#=== SUPPRIMER UTILISATEUR ===
@admin_bp.route("/utilisateurs/supprimer/<int:id_user>", methods=["POST"])
@admin_required
def supprimer_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    db = get_db()
    user = db.execute("SELECT nom_utilisateur FROM utilisateurs WHERE id = ?",
                      (id_user, )).fetchone()
    if user:
        db.execute("DELETE FROM utilisateurs WHERE id = ?", (id_user, ))
        db.commit()
        flash(f"L'utilisateur '{user['nom_utilisateur']}' a été supprimé.",
              "success")
    else:
        flash("Utilisateur non trouvé.", "error")
    return redirect(url_for('admin.gestion_utilisateurs'))


#=== PROMOUVOIR UTILISATEUR ===
@admin_bp.route("/utilisateurs/promouvoir/<int:id_user>", methods=["POST"])
@admin_required
def promouvoir_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Action non autorisée sur votre propre compte.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    password = request.form.get('password')
    db = get_db()
    admin_actuel = db.execute(
        "SELECT mot_de_passe FROM utilisateurs WHERE id = ?",
        (session['user_id'], )).fetchone()
    if not admin_actuel or not check_password_hash(
            admin_actuel['mot_de_passe'], password):
        flash(
            "Mot de passe administrateur incorrect. "
            "La passation de pouvoir a échoué.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    try:
        db.execute("UPDATE utilisateurs SET role = 'admin' WHERE id = ?",
                   (id_user, ))
        db.execute("UPDATE utilisateurs SET role = 'utilisateur' WHERE id = ?",
                   (session['user_id'], ))
        db.commit()
        flash(
            "Passation de pouvoir réussie ! "
            "Vous êtes maintenant un utilisateur standard.", "success")
        return redirect(url_for('auth.logout'))
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Une erreur est survenue lors de la passation de pouvoir : {e}",
              "error")
        return redirect(url_for('admin.gestion_utilisateurs'))


#=== REINITIALISER MDP ===
@admin_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
def reinitialiser_mdp(id_user):
    if id_user == session['user_id']:
        flash(
            "Vous ne pouvez pas réinitialiser votre propre mot de passe ici.",
            "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    nouveau_mdp = request.form.get('nouveau_mot_de_passe')
    if not nouveau_mdp or len(nouveau_mdp) < 4:
        flash(
            "Le nouveau mot de passe est requis et doit contenir "
            "au moins 4 caractères.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    db = get_db()
    user = db.execute("SELECT nom_utilisateur FROM utilisateurs WHERE id = ?",
                      (id_user, )).fetchone()
    if user:
        try:
            db.execute("UPDATE utilisateurs SET mot_de_passe = ? WHERE id = ?",
                       (generate_password_hash(nouveau_mdp,
                                               method='scrypt'), id_user))
            db.commit()
            flash(
                f"Le mot de passe pour l'utilisateur "
                f"'{user['nom_utilisateur']}' a été réinitialisé avec succès.",
                "success")
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Erreur de base de données : {e}", "error")
    else:
        flash("Utilisateur non trouvé.", "error")
    return redirect(url_for('admin.gestion_utilisateurs'))


#===============================
# GESTION KITS
#===============================
@admin_bp.route("/kits")
@admin_required
def gestion_kits():
    db = get_db()
    kits = db.execute("""
        SELECT k.id, k.nom, k.description, COUNT(ko.id) as count
        FROM kits k
        LEFT JOIN kit_objets ko ON k.id = ko.kit_id
        GROUP BY k.id, k.nom, k.description
        ORDER BY k.nom
        """).fetchall()
    armoires = get_all_armoires(db)
    categories = get_all_categories (db)
    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin', 'icon_svg': icon_svg},
        {'text': 'Gestion Quotidienne'},
        {'text': 'Gestion des kits'}
    ]
    return render_template("admin_kits.html",
                           kits=kits,
                           breadcrumbs=breadcrumbs,
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)


#=== AJOUTER KIT ===
@admin_bp.route("/kits/ajouter", methods=["POST"])
@admin_required
def ajouter_kit():
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()
    if not nom:
        flash("Le nom du kit ne peut pas être vide.", "error")
        return redirect(url_for('admin.gestion_kits'))

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO kits (nom, description) VALUES (?, ?)",
            (nom, description))
        db.commit()
        new_kit_id = cursor.lastrowid
        flash(
            f"Le kit '{nom}' a été créé. "
            "Vous pouvez maintenant y ajouter des objets.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=new_kit_id))
    except sqlite3.IntegrityError:
        flash(f"Un kit avec le nom '{nom}' existe déjà.", "error")
        return redirect(url_for('admin.gestion_kits'))


#=== MODIFIER KIT ===
@admin_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    db = get_db()
    kit = db.execute("SELECT id, nom, description FROM kits WHERE id = ?", (kit_id, )).fetchone()
    if not kit:
        flash("Kit non trouvé.", "error")
        return redirect(url_for('admin.gestion_kits'))

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if request.method == "POST":
        objet_id_str = request.form.get("objet_id")
        quantite_str = request.form.get("quantite")

        if objet_id_str and quantite_str:
            try:
                objet_id = int(objet_id_str)
                quantite = int(quantite_str)
                stock_info = db.execute(
                    f"""
                    SELECT o.nom, (o.quantite_physique - COALESCE((SELECT SUM(r.quantite_reservee) FROM reservations r WHERE r.objet_id = o.id AND r.fin_reservation > '{now_str}'), 0)) as quantite_disponible
                    FROM objets o WHERE o.id = ?
                    """, (objet_id,)
                ).fetchone()

                if not stock_info:
                    flash("Objet non trouvé.", "error")
                    return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

                if quantite > stock_info['quantite_disponible']:
                    flash(f"Quantité invalide pour '{stock_info['nom']}'. Vous ne pouvez pas ajouter plus que le stock disponible ({stock_info['quantite_disponible']}).", "error")
                    return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

                existing = db.execute("SELECT id FROM kit_objets WHERE kit_id = ? AND objet_id = ?", (kit_id, objet_id)).fetchone()
                if existing:
                    db.execute("UPDATE kit_objets SET quantite = ? WHERE id = ?", (quantite, existing['id']))
                else:
                    db.execute("INSERT INTO kit_objets (kit_id, objet_id, quantite) VALUES (?, ?, ?)", (kit_id, objet_id, quantite))
                db.commit()
                flash(f"L'objet '{stock_info['nom']}' a été ajouté/mis à jour dans le kit.", "success")

            except (ValueError, TypeError):
                flash("Données invalides.", "error")
            
            return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

        for key, value in request.form.items():
            if key.startswith("quantite_"):
                try:
                    kit_objet_id = int(key.split("_")[1])
                    new_quantite = int(value)

                    objet_info = db.execute(
                        f"""
                        SELECT o.nom, o.id as objet_id, (o.quantite_physique - COALESCE((SELECT SUM(r.quantite_reservee) FROM reservations r WHERE r.objet_id = o.id AND r.fin_reservation > '{now_str}'), 0)) as quantite_disponible
                        FROM kit_objets ko JOIN objets o ON ko.objet_id = o.id
                        WHERE ko.id = ?
                        """, (kit_objet_id,)
                    ).fetchone()

                    if not objet_info: continue

                    if new_quantite > objet_info['quantite_disponible']:
                         flash(f"Quantité invalide pour '{objet_info['nom']}'. Vous ne pouvez pas dépasser le stock disponible ({objet_info['quantite_disponible']}).", "error")
                    else:
                        db.execute("UPDATE kit_objets SET quantite = ? WHERE id = ?", (new_quantite, kit_objet_id))
                        flash(f"Quantité pour '{objet_info['nom']}' mise à jour.", "success")
                
                except (ValueError, TypeError):
                    flash("Une quantité fournie est invalide.", "error")
        
        db.commit()
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

    objets_in_kit = db.execute(
        f"""
        SELECT ko.id, o.nom, 
               (o.quantite_physique - COALESCE((SELECT SUM(r.quantite_reservee) FROM reservations r WHERE r.objet_id = o.id AND r.fin_reservation > '{now_str}'), 0)) as stock_disponible, 
               ko.quantite
        FROM kit_objets ko
        JOIN objets o ON ko.objet_id = o.id
        WHERE ko.kit_id = ?
        ORDER BY o.nom
        """, (kit_id, )).fetchall()

    objets_disponibles = db.execute(
        f"""
        SELECT id, nom, (quantite_physique - COALESCE((SELECT SUM(r.quantite_reservee) FROM reservations r WHERE r.objet_id = objets.id AND r.fin_reservation > '{now_str}'), 0)) as quantite_disponible 
        FROM objets
        WHERE id NOT IN (SELECT objet_id FROM kit_objets WHERE kit_id = ?)
        ORDER BY nom
        """, (kit_id, )).fetchall()

    armoires = get_all_armoires (db)
    categories = get_all_categories(db)
    
    breadcrumbs = [
    {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin'},
    {'text': 'Gestion des Kits', 'endpoint': 'admin.gestion_kits'},
    {'text': kit['nom']}
    ]

    return render_template("admin_kit_modifier.html",
                           kit=kit,
                           breadcrumbs=breadcrumbs,
                           objets_in_kit=objets_in_kit,
                           objets_disponibles=objets_disponibles,
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)


#=== RETIRER OBJET DUN KIT ===
@admin_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=['GET', 'POST'])
@admin_required
def retirer_objet_kit(kit_objet_id):
    db = get_db()
    kit_objet = db.execute("SELECT kit_id FROM kit_objets WHERE id = ?",
                           (kit_objet_id, )).fetchone()
    if kit_objet:
        kit_id = kit_objet['kit_id']
        db.execute("DELETE FROM kit_objets WHERE id = ?", (kit_objet_id, ))
        db.commit()
        flash("Objet retiré du kit.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))
    flash("Erreur : objet du kit non trouvé.", "error")
    return redirect(url_for('admin.gestion_kits'))


#=== SUPPRIMER KIT ===
@admin_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    db = get_db()
    kit = db.execute("SELECT nom FROM kits WHERE id = ?",
                     (kit_id, )).fetchone()
    if kit:
        db.execute("DELETE FROM kits WHERE id = ?", (kit_id, ))
        db.commit()
        flash(f"Le kit '{kit['nom']}' a été supprimé.", "success")
    else:
        flash("Kit non trouvé.", "error")
    return redirect(url_for('admin.gestion_kits'))
    
    
#===================================
# GESTION FOURNISSEURS 
#===================================
@admin_bp.route("/fournisseurs", methods=['GET', 'POST'])
@admin_required
def gestion_fournisseurs():
    db = get_db()
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        site_web = request.form.get('site_web', '').strip()
        logo_name = None

        if not nom:
            flash("Le nom du fournisseur est obligatoire.", "error")
            return redirect(url_for('admin.gestion_fournisseurs'))

        if 'logo' in request.files:
            logo = request.files['logo']
            if logo and logo.filename != '':
                filename = secure_filename(logo.filename)
                upload_path = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_path, exist_ok=True)
                logo.save(os.path.join(upload_path, filename))
                logo_name = filename

        try:
            db.execute(
                "INSERT INTO fournisseurs (nom, site_web, logo) "
                "VALUES (?, ?, ?)", (nom, site_web or None, logo_name))
            db.commit()
            flash(f"Le fournisseur '{nom}' a été ajouté.", "success")
        except sqlite3.IntegrityError:
            flash(f"Un fournisseur avec le nom '{nom}' existe déjà.", "error")
        except sqlite3.Error as e:
            flash(f"Erreur de base de données : {e}", "error")
        return redirect(url_for('admin.gestion_fournisseurs'))

    fournisseurs = db.execute(
        "SELECT * FROM fournisseurs ORDER BY nom").fetchall()
    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
    {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin','icon_svg': icon_svg},
    {'text': 'Gestion Quotidienne'},
    {'text': 'Gestion des Fournisseurs', 'endpoint': 'admin.gestion_fournisseurs'}
    ]
    return render_template("admin_fournisseurs.html",
                            breadcrumbs=breadcrumbs,
                            fournisseurs=fournisseurs)


@admin_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    db = get_db()
    fournisseur = db.execute("SELECT logo, nom FROM fournisseurs WHERE id = ?",
                             (id, )).fetchone()
    if fournisseur:
        if fournisseur['logo']:
            try:
                logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], fournisseur['logo'])
                if os.path.exists(logo_path):
                    os.remove(logo_path)
            except OSError:
                pass

        db.execute("DELETE FROM fournisseurs WHERE id = ?", (id, ))
        db.commit()
        flash(f"Le fournisseur '{fournisseur['nom']}' a été supprimé.",
              "success")
    else:
        flash("Fournisseur non trouvé.", "error")
    return redirect(url_for('admin.gestion_fournisseurs'))


@admin_bp.route("/fournisseurs/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_fournisseur(id):
    db = get_db()
    fournisseur_avant = db.execute("SELECT * FROM fournisseurs WHERE id = ?",
                                   (id, )).fetchone()
    if not fournisseur_avant:
        flash("Fournisseur non trouvé.", "error")
        return redirect(url_for('admin.gestion_fournisseurs'))

    nom = request.form.get('nom', '').strip()
    site_web = request.form.get('site_web', '').strip()
    logo_name = fournisseur_avant['logo']

    upload_path = current_app.config['UPLOAD_FOLDER']

    if not nom:
        flash("Le nom du fournisseur est obligatoire.", "error")
        return redirect(url_for('admin.gestion_fournisseurs'))

    if request.form.get('supprimer_logo'):
        if logo_name:
            try:
                logo_path = os.path.join(upload_path, logo_name)
                if os.path.exists(logo_path):
                    os.remove(logo_path)
            except OSError:
                pass
        logo_name = None
    elif 'logo' in request.files:
        nouveau_logo = request.files['logo']
        if nouveau_logo and nouveau_logo.filename != '':
            if logo_name:
                try:
                    logo_path = os.path.join(upload_path, logo_name)
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                except OSError:
                    pass
            filename = secure_filename(nouveau_logo.filename)
            os.makedirs(upload_path, exist_ok=True)
            nouveau_logo.save(os.path.join(upload_path, filename))
            logo_name = filename

    try:
        db.execute(
            "UPDATE fournisseurs SET nom = ?, site_web = ?, logo = ? "
            "WHERE id = ?", (nom, site_web or None, logo_name, id))
        db.commit()
        flash(f"Le fournisseur '{nom}' a été mis à jour.", "success")
    except sqlite3.IntegrityError:
        flash(f"Un autre fournisseur avec le nom '{nom}' existe déjà.",
              "error")
    except sqlite3.Error as e:
        flash(f"Erreur de base de données : {e}", "error")
    
    return redirect(url_for('admin.gestion_fournisseurs'))


#==================================
# GESTION DU BUDGET
#==================================
@admin_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    db = get_db()
    now = datetime.now()
    annee_scolaire_actuelle = now.year if now.month >= 8 else now.year - 1

    budgets_archives = db.execute(
        "SELECT annee FROM budgets ORDER BY annee DESC").fetchall()

    annee_a_afficher_str = request.args.get('annee', type=str)
    
    if annee_a_afficher_str:
        annee_a_afficher = int(annee_a_afficher_str)
    else:
        annee_a_afficher = annee_scolaire_actuelle

    budget_a_afficher = db.execute("SELECT * FROM budgets WHERE annee = ?",
                                   (annee_a_afficher, )).fetchone()
    if not budget_a_afficher and not budgets_archives:
        try:
            cursor = db.execute(
                "INSERT INTO budgets (annee, montant_initial, cloture) VALUES (?, ?, 0)",
                (annee_a_afficher, 0.0)
            )
            db.commit()
            budget_id = cursor.lastrowid
            budget_a_afficher = db.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
            budgets_archives = db.execute("SELECT annee FROM budgets ORDER BY annee DESC").fetchall()
        except sqlite3.IntegrityError:
            db.rollback()
            budget_a_afficher = db.execute("SELECT * FROM budgets WHERE annee = ?", (annee_a_afficher,)).fetchone()

    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_a_afficher:
        depenses = db.execute(
            """SELECT d.id, d.contenu, d.montant, d.date_depense,
                      d.est_bon_achat, d.fournisseur_id, f.nom as fournisseur_nom
               FROM depenses d
               LEFT JOIN fournisseurs f ON d.fournisseur_id = f.id
               WHERE d.budget_id = ?
               ORDER BY d.date_depense DESC""",
            (budget_a_afficher['id'], )).fetchall()

        total_depenses_result = db.execute(
            "SELECT SUM(montant) as total FROM depenses WHERE budget_id = ?",
            (budget_a_afficher['id'], )).fetchone()
        total_depenses = (total_depenses_result['total'] if total_depenses_result['total'] is not None else 0)
        solde = budget_a_afficher['montant_initial'] - total_depenses
        annee_fin_budget = budget_a_afficher['annee'] + 1
        date_limite_cloture = date(annee_fin_budget, 6, 1)
        if date.today() >= date_limite_cloture:
            cloture_autorisee = True

    budget_actuel_pour_modales = db.execute(
        "SELECT * FROM budgets WHERE annee = ? AND cloture = 0",
        (annee_scolaire_actuelle, )).fetchone()

    annee_proposee_pour_creation = annee_scolaire_actuelle
    if not budget_actuel_pour_modales:
        derniere_annee_budget = db.execute("SELECT MAX(annee) as max_annee FROM budgets").fetchone()
        if derniere_annee_budget and derniere_annee_budget['max_annee'] is not None:
            annee_proposee_pour_creation = derniere_annee_budget['max_annee'] + 1
        else:
            annee_proposee_pour_creation = annee_scolaire_actuelle

    fournisseurs = db.execute(
        "SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
    {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin','icon_svg': icon_svg},
    {'text': 'Gestion Quotidienne'},
    {'text': 'Gestion des Budget', 'endpoint': 'admin.budget'}
    ]
    return render_template(
        "budget.html",
        budget_affiche=budget_a_afficher,
        breadcrumbs=breadcrumbs,
        budget_actuel_pour_modales=budget_actuel_pour_modales,
        annee_proposee_pour_creation=annee_proposee_pour_creation,
        depenses=depenses,
        total_depenses=total_depenses,
        solde=solde,
        fournisseurs=fournisseurs,
        budgets_archives=budgets_archives,
        annee_selectionnee=annee_a_afficher,
        cloture_autorisee=cloture_autorisee,
        now=datetime.now)


@admin_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    db = get_db()
    montant = request.form.get('montant_initial')
    annee = request.form.get('annee')

    if not montant or not annee:
        flash("L'année et le montant sont obligatoires.", "error")
        return redirect(url_for('admin.budget'))

    try:
        montant_float = float(montant.replace(',', '.'))
        annee_int = int(annee)

        existing_budget = db.execute(
            "SELECT id FROM budgets WHERE annee = ?", (annee_int,)
        ).fetchone()
        if existing_budget:
            db.execute(
                "UPDATE budgets SET montant_initial = ?, cloture = 0 WHERE id = ?",
                (montant_float, existing_budget['id'])
            )
        else:
            db.execute(
                "INSERT INTO budgets (annee, montant_initial) VALUES (?, ?)",
                (annee_int, montant_float)
            )

        db.commit()
        flash(
            f"Le budget pour l'année scolaire {annee_scolaire_format(annee_int)} a été défini à "
            f"{montant_float:.2f} €.", "success"
        )
    except ValueError:
        flash("Le montant ou l'année saisi(e) est invalide.", "error")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.budget', annee=annee))


@admin_bp.route("/budget/ajouter_depense", methods=['POST'])
@admin_required
def ajouter_depense():
    db = get_db()
    budget_id = request.form.get('budget_id')
    fournisseur_id = request.form.get('fournisseur_id')
    contenu = request.form.get('contenu', '').strip()
    montant = request.form.get('montant')
    date_depense = request.form.get('date_depense')
    est_bon_achat = 1 if request.form.get('est_bon_achat') == 'on' else 0

    if not all([budget_id, contenu, montant, date_depense]):
        flash("Tous les champs sont obligatoires pour ajouter une dépense.",
              "error")
        return redirect(url_for('admin.budget'))

    if est_bon_achat:
        fournisseur_id = None
    elif not fournisseur_id:
        flash(
            "Veuillez sélectionner un fournisseur ou cocher la case "
            "'Bon d'achat'.", "error")
        return redirect(url_for('admin.budget'))

    try:
        montant_float = float(montant.replace(',', '.'))
        db.execute(
            """INSERT INTO depenses (budget_id, fournisseur_id, contenu,
               montant, date_depense, est_bon_achat)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (budget_id, fournisseur_id, contenu, montant_float, date_depense,
             est_bon_achat))
        db.commit()
        flash("La dépense a été ajoutée avec succès.", "success")
    except ValueError:
        flash("Le montant saisi est invalide.", "error")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.budget'))


@admin_bp.route("/budget/modifier_depense/<int:id>", methods=['POST'])
@admin_required
def modifier_depense(id):
    db = get_db()
    depense = db.execute("SELECT id FROM depenses WHERE id = ?",
                         (id, )).fetchone()
    if not depense:
        flash("Dépense non trouvée.", "error")
        return redirect(url_for('admin.budget'))

    fournisseur_id = request.form.get('fournisseur_id')
    contenu = request.form.get('contenu', '').strip()
    montant = request.form.get('montant')
    date_depense = request.form.get('date_depense')
    est_bon_achat = 1 if request.form.get('est_bon_achat') == 'on' else 0

    if not all([contenu, montant, date_depense]):
        flash("Les champs contenu, montant et date sont obligatoires.",
              "error")
        return redirect(request.referrer or url_for('admin.budget'))

    if est_bon_achat:
        fournisseur_id = None
    elif not fournisseur_id:
        flash(
            "Veuillez sélectionner un fournisseur ou cocher la case "
            "'Bon d'achat'.", "error")
        return redirect(request.referrer or url_for('admin.budget'))

    try:
        montant_float = float(montant.replace(',', '.'))
        db.execute(
            """UPDATE depenses SET fournisseur_id = ?, contenu = ?,
               montant = ?, date_depense = ?, est_bon_achat = ?
               WHERE id = ?""", (fournisseur_id, contenu, montant_float,
                                 date_depense, est_bon_achat, id))
        db.commit()
        flash("La dépense a été modifiée avec succès.", "success")
    except ValueError:
        flash("Le montant saisi est invalide.", "error")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(request.referrer or url_for('admin.budget'))


@admin_bp.route("/budget/supprimer_depense/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    db = get_db()
    depense = db.execute("SELECT id FROM depenses WHERE id = ?",
                         (id, )).fetchone()
    if depense:
        try:
            db.execute("DELETE FROM depenses WHERE id = ?", (id, ))
            db.commit()
            flash("La dépense a été supprimée avec succès.", "success")
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Erreur de base de données : {e}", "error")
    else:
        flash("Dépense non trouvée.", "error")

    return redirect(request.referrer or url_for('admin.budget'))


@admin_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    budget_id = request.form.get('budget_id')
    db = get_db()
    
    budget = db.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()

    if not budget:
        flash("Budget non trouvé.", "error")
        return redirect(url_for('admin.budget'))

    # --- VÉRIFICATION DE SÉCURITÉ CÔTÉ SERVEUR ---
    annee_fin_budget = budget['annee'] + 1
    date_limite_cloture = date(annee_fin_budget, 6, 1)
    if date.today() < date_limite_cloture:
        flash(f"La clôture du budget {annee_scolaire_format(budget['annee'])} n'est autorisée qu'à partir du {date_limite_cloture.strftime('%d/%m/%Y')}.", "error")
        return redirect(url_for('admin.budget', annee=budget['annee']))

    if budget['cloture']:
        flash(f"Le budget pour l'année scolaire {annee_scolaire_format(budget['annee'])} est déjà clôturé.", "warning")
        return redirect(url_for('admin.budget'))

    try:
        db.execute("UPDATE budgets SET cloture = 1 WHERE id = ?", (budget_id,))
        db.commit()
        flash(f"Le budget pour l'année scolaire {annee_scolaire_format(budget['annee'])} a été clôturé avec succès.", "success")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.budget'))

@admin_bp.route("/exporter_budget")
@admin_required
def exporter_budget():
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    format_type = request.args.get('format')

    if not all([date_debut, date_fin, format_type]):
        flash("Tous les champs sont requis pour l'export.", "error")
        return redirect(url_for('admin.budget'))

    db = get_db()
    depenses_data = db.execute("""
        SELECT 
            d.date_depense, 
            d.contenu, 
            d.montant, 
            CASE 
                WHEN d.est_bon_achat = 1 THEN 'Petit matériel bon achat' 
                ELSE f.nom 
            END as fournisseur_nom
        FROM depenses d
        LEFT JOIN fournisseurs f ON d.fournisseur_id = f.id
        WHERE d.date_depense BETWEEN ? AND ?
        ORDER BY d.date_depense ASC
    """, (date_debut, date_fin)).fetchall()

    if not depenses_data:
        flash("Aucune dépense trouvée pour la période sélectionnée.", "warning")
        return redirect(url_for('admin.budget'))

    if format_type == 'pdf':
        buffer = generer_budget_pdf(depenses_data, date_debut, date_fin)
        return send_file(buffer, as_attachment=True, download_name='rapport_depenses.pdf', mimetype='application/pdf')
    elif format_type == 'excel':
        buffer = generer_budget_excel(depenses_data, date_debut, date_fin)
        return send_file(buffer, as_attachment=True, download_name='rapport_depenses.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    flash("Format d'exportation non valide.", "error")
    return redirect(url_for('admin.budget'))

#=======================================
# GESTION DES ARMOIRES ET CATEGORIES
#=======================================
@admin_bp.route("/ajouter", methods=["POST"])
@admin_required
def ajouter():
    type_objet = request.form.get("type")
    nom = request.form.get("nom", "").strip()
    redirect_to = ("main.gestion_armoires"
                   if type_objet == "armoire" else "main.gestion_categories")
    if not nom:
        flash("Le nom ne peut pas être vide.", "error")
        return redirect(url_for(redirect_to))
    table_name = "armoires" if type_objet == "armoire" else "categories"
    db = get_db()
    try:
        db.execute(f"INSERT INTO {table_name} (nom) VALUES (?)", (nom, ))
        db.commit()
        flash(f"L'élément '{nom}' a été créé.", "success")
    except sqlite3.IntegrityError:
        flash(f"L'élément '{nom}' existe déjà.", "error")
    return redirect(url_for(redirect_to))

@admin_bp.route("/supprimer/<type_objet>/<int:id>", methods=["POST"])
@admin_required
def supprimer(type_objet, id):
    db = get_db()
    redirect_to = ("main.gestion_armoires"
                   if type_objet == "armoire" else "main.gestion_categories")
    if type_objet == "armoire":
        if db.execute("SELECT COUNT(id) FROM objets WHERE armoire_id = ?",
                      (id, )).fetchone()[0] > 0:
            flash(
                "Impossible de supprimer. Cette armoire contient encore "
                "des objets.", "error")
            return redirect(url_for(redirect_to))
    table_map = {"armoire": "armoires", "categorie": "categories"}
    if type_objet in table_map:
        table_name = table_map[type_objet]
        nom_element = db.execute(f"SELECT nom FROM {table_name} WHERE id = ?",
                                 (id, )).fetchone()
        db.execute(f"DELETE FROM {table_name} WHERE id = ?", (id, ))
        db.commit()
        if nom_element:
            flash(
                f"L'élément '{nom_element['nom']}' a été supprimé avec succès.",
                "success")
    else:
        flash("Type d'élément à supprimer non valide.", "error")
    return redirect(url_for(redirect_to))
                           

@admin_bp.route("/modifier_armoire", methods=["POST"])
@admin_required
def modifier_armoire():
    data = request.get_json()
    armoire_id, nouveau_nom = data.get("id"), data.get("nom")
    if not all([armoire_id, nouveau_nom, nouveau_nom.strip()]):
        return jsonify(success=False, error="Données invalides"), 400
    db = get_db()
    try:
        db.execute("UPDATE armoires SET nom = ? WHERE id = ?",
                   (nouveau_nom.strip(), armoire_id))
        db.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom.strip())
    except sqlite3.IntegrityError:
        return jsonify(success=False,
                       error="Ce nom d'armoire existe déjà."), 500


@admin_bp.route("/modifier_categorie", methods=["POST"])
@admin_required
def modifier_categorie():
    data = request.get_json()
    categorie_id, nouveau_nom = data.get("id"), data.get("nom")
    if not all([categorie_id, nouveau_nom, nouveau_nom.strip()]):
        return jsonify(success=False, error="Données invalides"), 400
    db = get_db()
    try:
        db.execute("UPDATE categories SET nom = ? WHERE id = ?",
                   (nouveau_nom.strip(), categorie_id))
        db.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom.strip())
    except sqlite3.IntegrityError:
        return jsonify(success=False,
                       error="Ce nom de catégorie existe déjà."), 500


#========================================
# GESTION RAPPORTS ET EXPORTS
#========================================
@admin_bp.route("/rapports", methods=['GET'])
@admin_required
def rapports():
    db = get_db()
    dernieres_actions = db.execute("""
        SELECT h.timestamp, h.action, o.nom as objet_nom, u.nom_utilisateur
        FROM historique h
        JOIN objets o ON h.objet_id = o.id
        JOIN utilisateurs u ON h.utilisateur_id = u.id
        ORDER BY h.timestamp DESC
        LIMIT 5
        """).fetchall()

    armoires = get_all_armoires(db)
    categories = get_all_categories(db)
    
    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
    {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin','icon_svg': icon_svg},
    {'text': 'Analyses et exports'},
    {'text': 'Exporter un rapport d\'activité', 'endpoint': 'admin.rapports'}
    ]
    return render_template("rapports.html",
                           dernieres_actions=dernieres_actions,
                           breadcrumbs=breadcrumbs,
                           armoires=armoires,
                           categories=categories,
                           now=datetime.now)

@admin_bp.route("/rapports/exporter", methods=['GET'])
@admin_required
def exporter_rapports():
    db = get_db()
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    group_by = request.args.get('group_by')
    format_type = request.args.get('format')

    if not all([date_debut, date_fin, group_by, format_type]):
        flash("Tous les champs sont requis pour générer un rapport.", "error")
        return redirect(url_for('admin.rapports'))

    try:
        date_fin_dt = datetime.strptime(date_fin, '%Y-%m-%d') + timedelta(days=1)
        date_fin_str = date_fin_dt.strftime('%Y-%m-%d')
    except ValueError:
        flash("Format de date invalide.", "error")
        return redirect(url_for('admin.rapports'))

    query = """
        SELECT h.timestamp, h.action, h.details, o.nom as objet_nom,
               u.nom_utilisateur
        FROM historique h
        JOIN objets o ON h.objet_id = o.id
        JOIN utilisateurs u ON h.utilisateur_id = u.id
        WHERE h.timestamp >= ? AND h.timestamp < ?
    """
    order_clause = "ORDER BY h.timestamp ASC"
    if group_by == 'action':
        order_clause = "ORDER BY h.action ASC, h.timestamp ASC"
    query += order_clause

    historique_data = db.execute(query, (date_debut, date_fin_str)).fetchall()

    if not historique_data:
        flash("Aucune donnée d'historique trouvée pour la période sélectionnée.", "warning")
        return redirect(url_for('admin.rapports'))

    if format_type == 'pdf':
        buffer = generer_rapport_pdf(historique_data, date_debut, date_fin, group_by)
        return send_file(buffer,
                         as_attachment=True,
                         download_name='rapport_activite.pdf',
                         mimetype='application/pdf')
    elif format_type == 'excel':
        buffer = generer_rapport_excel(historique_data, date_debut, date_fin, group_by)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='rapport_activite.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    flash("Format d'exportation non valide.", "error")
    return redirect(url_for('admin.rapports'))

def generer_rapport_pdf(data, date_debut, date_fin, group_by):
    pdf = PDFWithFooter()
    pdf.alias_nb_pages()
    pdf.add_page(orientation='L')
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Rapport d\'Activite', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(
        0, 10,
        f"Periode du {datetime.strptime(date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')} "
        f"au {datetime.strptime(date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)

    col_widths = {"date": 25, "heure": 15, "user": 35, "action": 60, "objet": 60, "details": 75}
    table_width = sum(col_widths.values())
    line_height = 7 # Hauteur de ligne fixe

    def draw_header():
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(col_widths["date"], 8, 'Date', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.cell(col_widths["heure"], 8, 'Heure', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.cell(col_widths["user"], 8, 'Utilisateur', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.cell(col_widths["action"], 8, 'Action', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.cell(col_widths["objet"], 8, 'Objet Concerne', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.cell(col_widths["details"], 8, 'Details', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)

    draw_header()

    current_group = None
    
    for item in data:
        if pdf.get_y() > 190: # Marge de sécurité pour le saut de page
            pdf.add_page(orientation='L')
            draw_header()
            if current_group:
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(230, 240, 255)
                pdf.cell(table_width, 8, f"Type d'action : {current_group}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)

        if group_by == 'action' and item['action'] != current_group:
            current_group = item['action']
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_fill_color(230, 240, 255)
            pdf.cell(table_width, 8, f"Type d'action : {current_group}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)

        pdf.set_font('Helvetica', '', 8)
        timestamp_dt = datetime.fromisoformat(item['timestamp'])
        
        pdf.cell(col_widths["date"], line_height, timestamp_dt.strftime('%d/%m/%Y'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths["heure"], line_height, timestamp_dt.strftime('%H:%M'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths["user"], line_height, item['nom_utilisateur'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths["action"], line_height, item['action'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths["objet"], line_height, item['objet_nom'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        pdf.cell(col_widths["details"], line_height, item['details'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

    return BytesIO(pdf.output())


def generer_rapport_excel(data, date_debut, date_fin, group_by):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rapport d'Activite"

    title_font = Font(name='Calibri', size=16, bold=True)
    subtitle_font = Font(name='Calibri', size=11, italic=True, color="6c7a89")
    header_font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568",
                              end_color="4A5568",
                              fill_type="solid")
    group_font = Font(name='Calibri', size=11, bold=True, color="2D3748")
    group_fill = PatternFill(start_color="E2E8F0",
                             end_color="E2E8F0",
                             fill_type="solid")
    even_row_fill = PatternFill(start_color="F7FAFC",
                                end_color="F7FAFC",
                                fill_type="solid")

    center_align = Alignment(horizontal='center',
                             vertical='center',
                             wrap_text=True)
    left_align = Alignment(horizontal='left',
                           vertical='center',
                           wrap_text=True)

    thin_border_side = Side(style='thin', color="4A5568")
    thick_border_side = Side(style='medium', color="000000")

    cell_border = Border(left=thin_border_side,
                         right=thin_border_side,
                         top=thin_border_side,
                         bottom=thin_border_side)

    start_col = 2
    headers = [
        "Date", "Heure", "Utilisateur", "Action", "Objet Concerne", "Details"
    ]
    end_col = start_col + len(headers) - 1

    sheet.merge_cells(start_row=2,
                      start_column=start_col,
                      end_row=2,
                      end_column=end_col)
    title_cell = sheet.cell(row=2, column=start_col)
    title_cell.value = "Rapport d'Activite"
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal='center')

    sheet.merge_cells(start_row=3,
                      start_column=start_col,
                      end_row=3,
                      end_column=end_col)
    subtitle_cell = sheet.cell(row=3, column=start_col)
    subtitle_cell.value = (
        f"Periode du "
        f"{datetime.strptime(date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')} au "
        f"{datetime.strptime(date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')}")
    subtitle_cell.font = subtitle_font
    subtitle_cell.alignment = Alignment(horizontal='center')

    header_row = 5
    for i, header_text in enumerate(headers, start=start_col):
        cell = sheet.cell(row=header_row, column=i, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = cell_border

    row_index = header_row + 1
    current_group = None
    last_date_str = None
    is_even = False

    for item in data:
        if group_by == 'action' and item['action'] != current_group:
            current_group = item['action']
            last_date_str = None
            cell = sheet.cell(row=row_index,
                              column=start_col,
                              value=f"Type d'action : {current_group}")
            sheet.merge_cells(start_row=row_index,
                              start_column=start_col,
                              end_row=row_index,
                              end_column=end_col)
            for c in range(start_col, end_col + 1):
                sheet.cell(row=row_index, column=c).fill = group_fill
                sheet.cell(row=row_index, column=c).font = group_font
                sheet.cell(row=row_index, column=c).border = cell_border
            row_index += 1
            is_even = False

        timestamp_dt = datetime.fromisoformat(item['timestamp'])
        current_date_str = timestamp_dt.strftime('%d/%m/%Y')

        date_str_display = current_date_str
        if group_by == 'date' and current_date_str == last_date_str:
            date_str_display = ""

        row_data = [
            date_str_display,
            timestamp_dt.strftime('%H:%M'), item['nom_utilisateur'],
            item['action'], item['objet_nom'], item['details']
        ]

        for col_index, value in enumerate(row_data, start=start_col):
            cell = sheet.cell(row=row_index, column=col_index, value=value)
            cell.border = cell_border
            if col_index in [
                    start_col, start_col + 1, start_col + 2, start_col + 3
            ]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align
            if is_even:
                cell.fill = even_row_fill

        last_date_str = current_date_str
        row_index += 1
        is_even = not is_even

    end_row_index = row_index - 1
    if end_row_index >= header_row:
        for row in sheet.iter_rows(min_row=header_row,
                                   max_row=end_row_index,
                                   min_col=start_col,
                                   max_col=end_col):
            for cell in row:
                new_border = Border(left=cell.border.left,
                                    right=cell.border.right,
                                    top=cell.border.top,
                                    bottom=cell.border.bottom)
                if cell.row == header_row:
                    new_border.top = thick_border_side
                if cell.row == end_row_index:
                    new_border.bottom = thick_border_side
                if cell.column == start_col:
                    new_border.left = thick_border_side
                if cell.column == end_col:
                    new_border.right = thick_border_side
                cell.border = new_border

    column_widths = {'B': 15, 'C': 10, 'D': 25, 'E': 50, 'F': 40, 'G': 60}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width

    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=start_col)

    if end_row_index >= header_row:
        sheet.auto_filter.ref = (
            f"{sheet.cell(row=header_row, column=start_col).coordinate}:"
            f"{sheet.cell(row=end_row_index, column=end_col).coordinate}")

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


@admin_bp.route("/exporter_inventaire")
@admin_required
def exporter_inventaire():
    db = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    inventaire_data = db.execute("""
        SELECT 
            o.nom, 
            c.nom AS categorie,
            a.nom AS armoire,
            (o.quantite_physique - COALESCE(SUM(r.quantite_reservee), 0)) as quantite_disponible,
            o.seuil,
            o.date_peremption
        FROM objets o 
        JOIN armoires a ON o.armoire_id = a.id
        JOIN categories c ON o.categorie_id = c.id
        LEFT JOIN reservations r ON o.id = r.objet_id AND r.fin_reservation > ?
        GROUP BY o.id, o.nom, c.nom, a.nom, o.seuil, o.date_peremption
        ORDER BY c.nom, o.nom
    """, (now_str,)).fetchall()
        
    format_type = request.args.get('format')
    if format_type == 'pdf':
        buffer = generer_inventaire_pdf(inventaire_data)
        return send_file(buffer, as_attachment=True, download_name='inventaire_complet.pdf', mimetype='application/pdf')
    elif format_type == 'excel':
        buffer = generer_inventaire_excel(inventaire_data)
        return send_file(buffer, as_attachment=True, download_name='inventaire_complet.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    flash("Format d'exportation non valide.","error")
    return redirect(url_for('admin.admin'))


def generer_inventaire_pdf(data):
    pdf = PDFWithFooter()
    pdf.alias_nb_pages()
    pdf.add_page(orientation='L')
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Inventaire Complet du Laboratoire', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 10, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    # En-têtes du tableau
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(50, 8, 'Catégorie', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(80, 8, 'Nom de l\'objet', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(25, 8, 'Qté Dispo', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(20, 8, 'Seuil', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(50, 8, 'Armoire', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(30, 8, 'Péremption', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
    
    # Regrouper données par catégorie
    grouped_data = {}
    for item in data:
        cat = item['categorie']
        if cat not in grouped_data:
            grouped_data[cat] = []
        grouped_data[cat].append(item)

    pdf.set_font('Helvetica', '', 8)
    for categorie, items in sorted(grouped_data.items()):
        row_count = len(items)
        start_y = pdf.get_y()
        start_x = pdf.get_x()
        for i, item in enumerate(items):
            date_peremption_str = ""
            if item['date_peremption']:
                try:
                    date_obj = datetime.strptime(item['date_peremption'], '%Y-%m-%d')
                    date_peremption_str = date_obj.strftime('%d/%m/%Y')
                except (ValueError, TypeError):
                    date_peremption_str = item['date_peremption']
                    
            pdf.set_x(start_x + 50)
            
            pdf.cell(80, 7, item['nom'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            pdf.cell(25, 7, str(item['quantite_disponible']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            pdf.cell(20, 7, str(item['seuil']), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            pdf.cell(50, 7, item['armoire'].encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            pdf.cell(30, 7, date_peremption_str, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        end_y = pdf.get_y()
        total_height = end_y - start_y

        pdf.set_y(start_y)
        pdf.set_x(start_x)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.multi_cell(50, total_height, categorie.encode('latin-1', 'replace').decode('latin-1'), border=1, align='C')
        pdf.set_font('Helvetica', '', 8)

        pdf.set_y(end_y)
        
    return BytesIO(pdf.output())

def generer_inventaire_excel(data):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventaire Complet"

    title_font = Font(name='Calibri', size=16, bold=True)
    header_font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    category_align = Alignment(horizontal='left', vertical='center')

    sheet.merge_cells('A1:F1')
    sheet['A1'] = 'Inventaire Complet du Laboratoire'
    sheet['A1'].font = title_font
    sheet['A1'].alignment = center_align
    sheet.merge_cells('A2:F2')
    sheet['A2'] = f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"

    headers = ["Catégorie", "Nom de l'objet", "Quantité Disponible", "Seuil", "Armoire", "Date de Péremption"]
    for i, header_text in enumerate(headers, start=1):
        cell = sheet.cell(row=4, column=i, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    row_index = 5
    current_category = None
    start_merge_row = 5

    for item in data:
        if item['categorie'] != current_category:
            if current_category is not None:
                if start_merge_row < row_index - 1:
                    sheet.merge_cells(start_row=start_merge_row, start_column=1, end_row=row_index - 1, end_column=1)
                    sheet.cell(row=start_merge_row, column=1).alignment = category_align
            
            current_category = item['categorie']
            start_merge_row = row_index

        sheet.cell(row=row_index, column=1, value=item['categorie'])
        sheet.cell(row=row_index, column=2, value=item['nom']).alignment = left_align
        sheet.cell(row=row_index, column=3, value=item['quantite_disponible']).alignment = center_align
        sheet.cell(row=row_index, column=4, value=item['seuil']).alignment = center_align
        
        armoire_cell = sheet.cell(row=row_index, column=5, value=item['armoire'])
        armoire_cell.alignment = center_align
        
        date_cell = sheet.cell(row=row_index, column=6)
        if item['date_peremption']:
            date_cell.value = datetime.strptime(item['date_peremption'], '%Y-%m-%d')
            date_cell.number_format = 'DD/MM/YYYY'
        date_cell.alignment = center_align
        
        row_index += 1

    if current_category is not None and start_merge_row < row_index - 1:
        sheet.merge_cells(start_row=start_merge_row, start_column=1, end_row=row_index - 1, end_column=1)
        sheet.cell(row=start_merge_row, column=1).alignment = category_align

    sheet.column_dimensions['A'].width = 30
    sheet.column_dimensions['B'].width = 50
    sheet.column_dimensions['C'].width = 20
    sheet.column_dimensions['D'].width = 10
    sheet.column_dimensions['E'].width = 30
    sheet.column_dimensions['F'].width = 20
    
    sheet.freeze_panes = 'A5'
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


#===============================================
# GESTION ECHEANCES
#===============================================
@admin_bp.route("/echeances")
@admin_required
def gestion_echeances():
    db = get_db()
    echeances_brutes = db.execute(
        "SELECT * FROM echeances ORDER BY date_echeance ASC").fetchall()

    icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px"><path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/></svg>'
    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'endpoint': 'admin.admin', 'icon_svg': icon_svg},
        {'text': 'Gestion Quotidienne'},
        {'text': 'Gestion des Echéances', 'endpoint': 'admin.gestion_echeances'}
        ]
    echeances_converties = []
    for echeance in echeances_brutes:
        echeance_dict = dict(echeance)
        echeance_dict['date_echeance'] = datetime.strptime(
            echeance['date_echeance'], '%Y-%m-%d').date()
        echeances_converties.append(echeance_dict)
        
    return render_template("admin_echeances.html",
                           echeances=echeances_converties,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=datetime.now().date(),
                           url_ajout=url_for('admin.ajouter_echeance'))


@admin_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    intitule = request.form.get('intitule', '').strip()
    date_echeance = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()

    if not all([intitule, date_echeance]):
        flash("L'intitulé et la date d'échéance sont obligatoires.", "error")
        return redirect(url_for('admin.gestion_echeances'))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO echeances (intitule, date_echeance, details) "
            "VALUES (?, ?, ?)", (intitule, date_echeance, details or None))
        db.commit()
        flash("L'échéance a été ajoutée avec succès.", "success")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.gestion_echeances'))


@admin_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    db = get_db()
    echeance = db.execute("SELECT id FROM echeances WHERE id = ?",
                          (id, )).fetchone()
    if not echeance:
        flash("Échéance non trouvée.", "error")
        return redirect(url_for('admin.gestion_echeances'))

    intitule = request.form.get('intitule', '').strip()
    date_echeance = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()
    traite = 1 if request.form.get('traite') == 'on' else 0

    if not all([intitule, date_echeance]):
        flash("L'intitulé et la date d'échéance sont obligatoires.", "error")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        db.execute(
            "UPDATE echeances SET intitule = ?, date_echeance = ?, "
            "details = ?, traite = ? WHERE id = ?",
            (intitule, date_echeance, details or None, traite, id))
        db.commit()
        flash("L'échéance a été modifiée avec succès.", "success")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.gestion_echeances'))


@admin_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    db = get_db()
    echeance = db.execute("SELECT id FROM echeances WHERE id = ?",
                          (id, )).fetchone()
    if echeance:
        try:
            db.execute("DELETE FROM echeances WHERE id = ?", (id, ))
            db.commit()
            flash("L'échéance a été supprimée avec succès.", "success")
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Erreur de base de données : {e}", "error")
    else:
        flash("Échéance non trouvée.", "error")

    return redirect(url_for('admin.gestion_echeances'))


#=======================================
# LICENCE
#=======================================
@admin_bp.route("/activer_licence", methods=["POST"])
@admin_required
def activer_licence():
    licence_cle_fournie = request.form.get('licence_cle', '').strip()
    db = get_db()

    instance_id_row = db.execute(
        "SELECT valeur FROM parametres WHERE cle = 'instance_id'").fetchone()
    if not instance_id_row:
        flash(
            "Erreur critique : Identifiant d'instance manquant. "
            "Impossible de vérifier la licence.", "error")
        return redirect(url_for('admin.admin'))

    instance_id = instance_id_row['valeur']

    chaine_a_verifier = f"{instance_id}-{current_app.config['CLE_PRO_SECRETE']}"
    cle_valide_calculee = hashlib.sha256(
        chaine_a_verifier.encode('utf-8')).hexdigest()

    if licence_cle_fournie == cle_valide_calculee[:16]:
        try:
            db.execute("UPDATE parametres SET valeur = 'PRO' "
                       "WHERE cle = 'licence_statut'")
            db.execute(
                "UPDATE parametres SET valeur = ? WHERE cle = 'licence_cle'",
                (licence_cle_fournie, ))
            db.commit()
            flash(
                "Licence Pro activée avec succès ! Toutes les "
                "fonctionnalités sont maintenant débloquées.", "success")
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Erreur de base de données lors de l'activation : {e}",
                  "error")
    else:
        flash(
            "La clé de licence fournie est invalide ou ne correspond pas à "
            "cette installation.", "error")

    return redirect(url_for('admin.admin'))


@admin_bp.route("/reset_licence", methods=["POST"])
@admin_required
def reset_licence():
    admin_password = request.form.get('admin_password')
    db = get_db()

    admin_user = db.execute(
        "SELECT mot_de_passe FROM utilisateurs WHERE id = ?",
        (session['user_id'], )).fetchone()

    if not admin_user or not check_password_hash(admin_user['mot_de_passe'],
                                                 admin_password):
        flash(
            "Mot de passe administrateur incorrect. "
            "La réinitialisation a été annulée.", "error")
        return redirect(url_for('admin.admin'))

    try:
        db.execute(
            "UPDATE parametres SET valeur = 'FREE' WHERE cle = 'licence_statut'"
        )
        db.execute(
            "UPDATE parametres SET valeur = '' WHERE cle = 'licence_cle'")
        db.commit()
        flash("La licence a été réinitialisée au statut GRATUIT.", "success")
    except sqlite3.Error as e:
        db.rollback()
        flash(f"Erreur de base de données lors de la réinitialisation : {e}",
              "error")

    return redirect(url_for('admin.admin'))
    
    
#==============================
# BASE DE DONNEES
#==============================
@admin_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    db = get_db()
    licence_row = db.execute("SELECT valeur FROM parametres WHERE cle = ?",
                             ('licence_statut', )).fetchone()
    is_pro = licence_row and licence_row['valeur'] == 'PRO'

    if not is_pro:
        flash(
            "Le téléchargement de la base de données est une fonctionnalité "
            "de la version Pro.", "warning")
        return redirect(url_for('admin.admin'))

    return send_file(current_app.config['DATABASE'], as_attachment=True)


@admin_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    if 'fichier' not in request.files:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.admin'))
    fichier = request.files.get("fichier")
    if not fichier or fichier.filename == '':
        flash("Aucun fichier selecté.", "error")
        return redirect(url_for('admin.admin'))
    if fichier and fichier.filename.endswith(".db"):
        temp_db_path = current_app.config['DATABASE'] + ".tmp"
        fichier.save(temp_db_path)
        shutil.move(temp_db_path, current_app.config['DATABASE'])
        flash("Base de données importée avec succès !", "success")
    else:
        flash("Le fichier fourni n'est pas une base de données valide (.db).",
              "error")
    return redirect(url_for('admin.admin'))


#=============================================
# GENERATION PDF ET EXCEL
#=============================================
def generer_budget_pdf(data, date_debut, date_fin):
    pdf = PDFWithFooter()
    pdf.alias_nb_pages()
    pdf.add_page(orientation='P')
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Rapport des Depenses', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(
        0, 10,
        f"Periode du {datetime.strptime(date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')} "
        f"au {datetime.strptime(date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(25, 8, 'Date', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(50, 8, 'Fournisseur', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(85, 8, 'Contenu de la commande'.encode('latin-1', 'replace').decode('latin-1'), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
    pdf.cell(30, 8, 'Montant (EUR)', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)

    pdf.set_font('Helvetica', '', 9)
    total_depenses = 0
    fill = False
    for item in data:
        pdf.set_fill_color(240, 240, 240)
        date_str = datetime.strptime(item['date_depense'], '%Y-%m-%d').strftime('%d/%m/%Y')
        fournisseur = (item['fournisseur_nom'] or 'N/A').encode('latin-1', 'replace').decode('latin-1')
        contenu = item['contenu'].encode('latin-1', 'replace').decode('latin-1')
        montant = item['montant']
        total_depenses += montant

        pdf.cell(25, 7, date_str, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=fill)
        pdf.cell(50, 7, fournisseur, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=fill)
        pdf.cell(85, 7, contenu, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=fill)
        pdf.cell(30, 7, f"{montant:.2f}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R', fill=fill)
        fill = not fill

    pdf.set_font('Helvetica', 'B', 10)
    total_text = 'Total des depenses'.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(160, 8, total_text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
    pdf.cell(30, 8, f"{total_depenses:.2f}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

    return BytesIO(pdf.output())


def generer_budget_excel(data, date_debut, date_fin):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rapport des Depenses"

    title_font = Font(name='Calibri', size=16, bold=True)
    header_font = Font(name='Calibri', size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568",
                              end_color="4A5568",
                              fill_type="solid")
    total_font = Font(name='Calibri', size=11, bold=True)

    center_align = Alignment(horizontal='center',
                             vertical='center',
                             wrap_text=True)
    right_align = Alignment(horizontal='right', vertical='center')
    thin_border_side = Side(style='thin', color="BFBFBF")
    cell_border = Border(left=thin_border_side,
                         right=thin_border_side,
                         top=thin_border_side,
                         bottom=thin_border_side)
    even_row_fill = PatternFill(start_color="F0F4F8",
                                end_color="F0F4F8",
                                fill_type="solid")

    sheet.merge_cells('B2:E2')
    sheet['B2'] = 'Rapport des Dépenses'
    sheet['B2'].font = title_font
    sheet['B2'].alignment = Alignment(horizontal='center')
    sheet.merge_cells('B3:E3')
    sheet['B3'] = (
        f"Période du "
        f"{datetime.strptime(date_debut, '%Y-%m-%d').strftime('%d/%m/%Y')} au "
        f"{datetime.strptime(date_fin, '%Y-%m-%d').strftime('%d/%m/%Y')}")
    sheet['B3'].font = Font(name='Calibri',
                            size=11,
                            italic=True,
                            color="6c7a89")
    sheet['B3'].alignment = Alignment(horizontal='center')

    headers = ["Date", "Fournisseur", "Contenu de la commande", "Montant (€)"]
    for i, header_text in enumerate(headers, start=2):
        cell = sheet.cell(row=5, column=i, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = cell_border

    row_index = 6
    total_depenses = 0
    is_even = False
    for item in data:
        date_val = datetime.strptime(item['date_depense'], '%Y-%m-%d')
        montant = item['montant']
        total_depenses += montant

        sheet.cell(row=row_index, column=2,
                   value=date_val).number_format = 'DD/MM/YYYY'
        sheet.cell(row=row_index,
                   column=3,
                   value=item['fournisseur_nom'] or 'N/A')
        sheet.cell(row=row_index, column=4, value=item['contenu'])
        sheet.cell(row=row_index, column=5,
                   value=montant).number_format = '#,##0.00'

        for col_idx in range(2, 6):
            cell = sheet.cell(row=row_index, column=col_idx)
            cell.border = cell_border
            if col_idx == 5:
                cell.alignment = right_align
            else:
                cell.alignment = center_align

            if is_even:
                cell.fill = even_row_fill

        is_even = not is_even
        row_index += 1

    total_cell_label = sheet.cell(row=row_index,
                                  column=4,
                                  value="Total des dépenses")
    total_cell_label.font = total_font
    total_cell_label.alignment = right_align
    total_cell_label.border = cell_border

    total_cell_value = sheet.cell(row=row_index,
                                  column=5,
                                  value=total_depenses)
    total_cell_value.font = total_font
    total_cell_value.number_format = '#,##0.00'
    total_cell_value.alignment = right_align
    total_cell_value.border = cell_border

    sheet.column_dimensions['B'].width = 15
    sheet.column_dimensions['C'].width = 30
    sheet.column_dimensions['D'].width = 50
    sheet.column_dimensions['E'].width = 15

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer