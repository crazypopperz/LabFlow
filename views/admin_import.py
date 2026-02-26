# ============================================================
# FICHIER : views/admin_import.py
# Sauvegarde, restauration, import/export, rapports
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from datetime import datetime
from io import BytesIO
import os
import json
import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from extensions import limiter
from db import db, Objet, Armoire, Categorie, Utilisateur, Historique, Etablissement, Reservation, InventaireArchive
from utils import admin_required, log_action, allowed_file

admin_import_bp = Blueprint('admin_import', __name__, url_prefix='/admin')

@admin_import_bp.route("/sauvegardes")
@admin_required
def gestion_sauvegardes():
    etablissement_id = session['etablissement_id']
    params = get_etablissement_params(etablissement_id)
    if params.get('licence_statut') != 'PRO':
        flash("Réservé à la version PRO.", "warning")
        return redirect(url_for('admin.admin'))
    return render_template("admin_backup.html", breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Sauvegardes'}])

@admin_import_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    etablissement_id = session['etablissement_id']
    params = get_etablissement_params(etablissement_id)
    if params.get('licence_statut') != 'PRO':
        flash("Réservé PRO.", "warning")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        data = {
            'metadata': {'version': '1.0', 'date': datetime.now().isoformat(), 'etablissement': session.get('nom_etablissement')},
            'armoires': [], 'categories': [], 'fournisseurs': [], 'objets': [], 'budget': [], 'depenses': [], 'echeances': []
        }
        
        # Extraction des données (simplifiée pour la lisibilité)
        for a in db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars():
            data['armoires'].append({'id': a.id, 'nom': a.nom})
        for c in db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars():
            data['categories'].append({'id': c.id, 'nom': c.nom})
        for f in db.session.execute(db.select(Fournisseur).filter_by(etablissement_id=etablissement_id)).scalars():
            data['fournisseurs'].append({'id': f.id, 'nom': f.nom, 'site_web': f.site_web, 'logo': f.logo})
        for o in db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars():
            data['objets'].append({
                'id': o.id, 'nom': o.nom, 'quantite': o.quantite_physique, 'seuil': o.seuil,
                'armoire_id': o.armoire_id, 'categorie_id': o.categorie_id, 'date_peremption': o.date_peremption,
                'image_url': o.image_url, 'fds_url': o.fds_url
            })
        for b in db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id)).scalars():
            b_data = {'id': b.id, 'annee': b.annee, 'montant': b.montant_initial, 'cloture': b.cloture}
            data['budget'].append(b_data)
            for d in b.depenses:
                data['depenses'].append({
                    'budget_id': b.id, 'date': d.date_depense, 'contenu': d.contenu,
                    'montant': d.montant, 'est_bon_achat': d.est_bon_achat, 'fournisseur_id': d.fournisseur_id
                })
        for e in db.session.execute(db.select(Echeance).filter_by(etablissement_id=etablissement_id)).scalars():
            data['echeances'].append({'intitule': e.intitule, 'date': e.date_echeance, 'details': e.details, 'traite': e.traite})

        json_str = json.dumps(data, default=json_serial, indent=4)
        buffer = BytesIO()
        buffer.write(json_str.encode('utf-8'))
        buffer.seek(0)
        log_action('backup_download', "Export JSON")
        safe_etab = sanitize_filename(session.get('nom_etablissement', 'Backup'))
        return send_file(buffer, as_attachment=True, download_name=f"Sauvegarde_{safe_etab}_{date.today()}.json", mimetype='application/json')

    except Exception:
        current_app.logger.error("Erreur backup", exc_info=True)
        flash("Erreur technique.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

@admin_import_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    etablissement_id = session['etablissement_id']
    if 'fichier' not in request.files:
        flash("Aucun fichier.", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))
        
    fichier = request.files['fichier']
    
    # CORRECTION : Vérification taille fichier avant lecture
    fichier.seek(0, 2)
    if fichier.tell() > MAX_JSON_SIZE:
        flash("Fichier JSON trop volumineux (Max 5Mo).", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))
    fichier.seek(0)

    if fichier.filename == '' or not allowed_file(fichier.filename) or not fichier.filename.endswith('.json'):
        flash("Fichier invalide (.json requis).", "error")
        return redirect(url_for('admin.gestion_sauvegardes'))

    try:
        data = json.load(fichier)
        
        # CORRECTION : Transaction atomique (Tout ou rien)
        with db.session.begin_nested():
            map_armoires = {}
            map_categories = {}
            map_fournisseurs = {}
            map_budgets = {}

            # Nettoyage
            for model in [KitObjet, Historique, Reservation, Suggestion, Depense, Objet, Kit, Budget, Echeance, Armoire, Categorie, Fournisseur]:
                db.session.query(model).filter_by(etablissement_id=etablissement_id).delete()
            db.session.flush()

            # Reconstruction
            for a in data.get('armoires', []):
                new_a = Armoire(nom=a['nom'], etablissement_id=etablissement_id)
                db.session.add(new_a)
                db.session.flush()
                map_armoires[a['id']] = new_a.id

            for c in data.get('categories', []):
                new_c = Categorie(nom=c['nom'], etablissement_id=etablissement_id)
                db.session.add(new_c)
                db.session.flush()
                map_categories[c['id']] = new_c.id

            for f in data.get('fournisseurs', []):
                new_f = Fournisseur(nom=f['nom'], site_web=f.get('site_web'), logo=f.get('logo'), etablissement_id=etablissement_id)
                db.session.add(new_f)
                db.session.flush()
                map_fournisseurs[f['id']] = new_f.id

            for o in data.get('objets', []):
                new_armoire_id = map_armoires.get(o['armoire_id'])
                new_cat_id = map_categories.get(o['categorie_id'])
                if not new_armoire_id or not new_cat_id: continue 
                
                date_perim = None
                if o.get('date_peremption'):
                    try: date_perim = datetime.fromisoformat(o['date_peremption']).date()
                    except: pass

                db.session.add(Objet(
                    nom=o['nom'], quantite_physique=o['quantite'], seuil=o['seuil'],
                    armoire_id=new_armoire_id, categorie_id=new_cat_id, date_peremption=date_perim,
                    image_url=o.get('image_url'), fds_url=o.get('fds_url'), etablissement_id=etablissement_id
                ))

            for b in data.get('budget', []):
                new_b = Budget(annee=b['annee'], montant_initial=b['montant'], cloture=b['cloture'], etablissement_id=etablissement_id)
                db.session.add(new_b)
                db.session.flush()
                map_budgets[b['id']] = new_b.id

            for d in data.get('depenses', []):
                new_budget_id = map_budgets.get(d['budget_id'])
                if not new_budget_id: continue
                new_fournisseur_id = map_fournisseurs.get(d['fournisseur_id']) if d.get('fournisseur_id') else None
                try: date_dep = datetime.fromisoformat(d['date']).date()
                except: date_dep = date.today()
                db.session.add(Depense(
                    budget_id=new_budget_id, fournisseur_id=new_fournisseur_id, contenu=d['contenu'],
                    montant=d['montant'], date_depense=date_dep, est_bon_achat=d.get('est_bon_achat', False),
                    etablissement_id=etablissement_id
                ))

            for e in data.get('echeances', []):
                try: date_ech = datetime.fromisoformat(e['date']).date()
                except: continue
                db.session.add(Echeance(intitule=e['intitule'], date_echeance=date_ech, details=e.get('details'), traite=e.get('traite', 0), etablissement_id=etablissement_id))

        db.session.commit()
        log_action('backup_restore', "Import JSON")
        flash("Restauration réussie !", "success")

    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur import DB", exc_info=True)
        flash("Erreur critique lors de l'importation.", "error")

    return redirect(url_for('admin.gestion_sauvegardes'))

# ============================================================
# IMPORT EXCEL
# ============================================================
@admin_import_bp.route("/importer", methods=['GET'])
@admin_required
def importer_page():
    etablissement_id = session['etablissement_id']
    armoires = db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()
    categories = db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()
    return render_template("admin_import.html", breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Import'}], armoires=armoires, categories=categories)

@admin_import_bp.route("/telecharger_modele")
@admin_required
def telecharger_modele_excel():
    etablissement_id = session['etablissement_id']
    armoires = db.session.execute(db.select(Armoire.nom).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)).scalars().all()
    categories = db.session.execute(db.select(Categorie.nom).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventaire"
    ws.append(["Nom", "Quantité", "Seuil", "Armoire", "Catégorie", "Date Péremption", "Image (URL)"])
    
    # Styles et validations (simplifié)
    ws_data = wb.create_sheet("Data_Listes")
    ws_data.sheet_state = 'hidden'
    for i, nom in enumerate(armoires, 1): ws_data.cell(row=i, column=1, value=nom)
    for i, nom in enumerate(categories, 1): ws_data.cell(row=i, column=2, value=nom)
    
    if armoires:
        dv = DataValidation(type="list", formula1=f"'Data_Listes'!$A$1:$A${len(armoires)}", allow_blank=True)
        ws.add_data_validation(dv)
        dv.add('D2:D1000')
    if categories:
        dv = DataValidation(type="list", formula1=f"'Data_Listes'!$B$1:$B${len(categories)}", allow_blank=True)
        ws.add_data_validation(dv)
        dv.add('E2:E1000')

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='modele_import.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_import_bp.route("/importer", methods=['POST'])
@admin_required
@limiter.limit("10 per minute")
def importer_fichier():
    etablissement_id = session['etablissement_id']
    if 'fichier_excel' not in request.files:
        flash("Aucun fichier.", "error")
        return redirect(url_for('admin.importer_page'))

    fichier = request.files['fichier_excel']
    if fichier.filename == '' or not allowed_file(fichier.filename) or not fichier.filename.endswith('.xlsx'):
        flash("Fichier invalide (.xlsx requis).", "error")
        return redirect(url_for('admin.importer_page'))

    # Check size
    fichier.seek(0, 2)
    if fichier.tell() > MAX_FILE_SIZE:
        flash("Fichier trop volumineux.", "error")
        return redirect(url_for('admin.importer_page'))
    fichier.seek(0)

    try:
        wb = load_workbook(fichier)
        ws = wb.active
        
        # 1. Validation des en-têtes
        headers = {cell.value: idx for idx, cell in enumerate(ws[1], 0) if cell.value}
        required_cols = {'Nom', 'Quantité', 'Seuil', 'Armoire', 'Catégorie'}
        
        if not required_cols.issubset(headers.keys()):
            flash(f"Colonnes manquantes. Requis : {', '.join(required_cols)}", "error")
            return redirect(url_for('admin.importer_page'))

        existing_objets = {o.nom.lower() for o in db.session.execute(db.select(Objet).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        armoires_map = {a.nom.lower(): a.id for a in db.session.execute(db.select(Armoire).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        categories_map = {c.nom.lower(): c.id for c in db.session.execute(db.select(Categorie).filter_by(etablissement_id=etablissement_id)).scalars().all()}
        
        success_count = 0
        errors = []
        
        # 2. Lecture avec limite de lignes
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if i > MAX_IMPORT_ROWS:
                errors.append(f"Limite de {MAX_IMPORT_ROWS} lignes atteinte. Le reste a été ignoré.")
                break
                
            if not row: continue
            
            # Récupération via le mapping des colonnes
            try:
                nom = row[headers['Nom']]
                qte = row[headers['Quantité']]
                seuil = row[headers['Seuil']]
                arm_nom = row[headers['Armoire']]
                cat_nom = row[headers['Catégorie']]
                
                # Colonnes optionnelles
                date_val = row[headers['Date Péremption']] if 'Date Péremption' in headers else None
                img_val = row[headers['Image (URL)']] if 'Image (URL)' in headers else None
            except IndexError:
                continue # Ligne malformée

            if not all([nom, qte is not None, seuil is not None]):
                errors.append(f"Ligne {i}: Données obligatoires manquantes")
                continue
                
            if str(nom).lower() in existing_objets: continue
            
            arm_id = armoires_map.get(str(arm_nom).lower().strip()) if arm_nom else None
            cat_id = categories_map.get(str(cat_nom).lower().strip()) if cat_nom else None
            
            if not arm_id or not cat_id:
                errors.append(f"Ligne {i}: Armoire ou Catégorie inconnue")
                continue
                
            date_perim = None
            if date_val:
                if isinstance(date_val, datetime): date_perim = date_val.date()
                elif isinstance(date_val, str):
                    try: date_perim = datetime.strptime(date_val.split(' ')[0], '%Y-%m-%d').date()
                    except: pass

            db.session.add(Objet(
                nom=str(nom), quantite_physique=int(qte), seuil=int(seuil),
                armoire_id=arm_id, categorie_id=cat_id, date_peremption=date_perim,
                image_url=str(img_val) if img_val else None,
                etablissement_id=etablissement_id
            ))
            success_count += 1
            
        if errors:
            db.session.rollback()
            for e in errors[:5]: flash(e, "error")
            if len(errors) > 5: flash(f"... et {len(errors)-5} autres erreurs.", "error")
        else:
            db.session.commit()
            log_action('import_excel', f"{success_count} objets importés")
            flash(f"{success_count} objets importés.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur import Excel", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('admin.importer_page'))

# MODULE RAPPORTS & ACTIVITÉ (Version Durcie)
# ============================================================

# Constantes de sécurité pour les rapports
MAX_EXPORT_DAYS = 366      # Limite la plage à 1 an
MAX_EXPORT_ROWS = 5000     # Limite le nombre de lignes pour éviter le crash RAM (ReportLab/OpenPyXL)
ALLOWED_FORMATS = {'excel', 'pdf'}

@admin_import_bp.route("/rapports")
@admin_required
def rapports():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des paramètres d'URL
    page = request.args.get('page', 1, type=int)
    filtre_action = request.args.get('action', 'all') # all, creation, modification, deplacement, suppression
    search_query = request.args.get('q', '').strip()
    
    # 2. Construction de la requête de base
    stmt = (
        db.select(Historique, Utilisateur.nom_utilisateur, Objet.nom.label('objet_nom'))
        .outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)
        .outerjoin(Objet, Historique.objet_id == Objet.id)
        .filter(Historique.etablissement_id == etablissement_id)
        .order_by(Historique.timestamp.desc())
    )

    # 3. Application des filtres
    if filtre_action == 'creation':
        stmt = stmt.filter(Historique.action == 'Création')
    elif filtre_action == 'suppression':
        stmt = stmt.filter(Historique.action == 'Suppression')
    elif filtre_action == 'modification':
        # Exclure les déplacements (qui sont techniquement des modifs)
        stmt = stmt.filter(
            Historique.action == 'Modification',
            ~Historique.details.ilike('%Déplacé%'),
            ~Historique.details.ilike('%Armoire%')
        )
    elif filtre_action == 'deplacement':
        stmt = stmt.filter(
            Historique.action == 'Modification',
            (Historique.details.ilike('%Déplacé%') | Historique.details.ilike('%Armoire%'))
        )

    # 4. Recherche textuelle
    if search_query:
        stmt = stmt.filter(
            (Historique.details.ilike(f'%{search_query}%')) |
            (Objet.nom.ilike(f'%{search_query}%')) |
            (Utilisateur.nom_utilisateur.ilike(f'%{search_query}%'))
        )

    # 5. Pagination (50 items par page)
    pagination = db.paginate(stmt, page=page, per_page=50)

    # 6. Formatage des données pour la vue
    logs = []
    for item in pagination.items:
        # Détection du type pour gérer le cas où paginate renvoie un objet ou un tuple
        if isinstance(item, Historique):
            # Cas : Modèle seul
            h = item
            user_name = h.utilisateur.nom_utilisateur if h.utilisateur else "Utilisateur supprimé"
            
            # Récupération manuelle du nom de l'objet (si nécessaire)
            obj_name = "Objet supprimé"
            if h.objet_id:
                obj = db.session.get(Objet, h.objet_id)
                if obj: obj_name = obj.nom
        else:
            # Cas : Tuple (Historique, nom_user, nom_objet)
            h, user_name, obj_name = item

        # Détection du type pour les badges (si pas déjà filtré)
        type_badge = 'secondary'
        if h.action == 'Création': type_badge = 'success'
        elif h.action == 'Suppression': type_badge = 'danger'
        elif 'Déplacé' in (h.details or ''): type_badge = 'info'
        elif h.action == 'Modification': type_badge = 'warning'

        logs.append({
            'date': h.timestamp,
            'user': user_name or "Utilisateur supprimé",
            'objet': obj_name or "Objet supprimé",
            'action': h.action,
            'details': h.details,
            'type_badge': type_badge
        })

    breadcrumbs = [
        {'text': 'Admin', 'url': url_for('admin.admin')}, 
        {'text': 'Historique Complet'}
    ]

    return render_template("rapports.html", 
                           logs=logs, 
                           pagination=pagination, 
                           filtre_actif=filtre_action,
                           search_query=search_query,
                           breadcrumbs=breadcrumbs)


@admin_import_bp.route("/exporter_rapports", methods=['GET'])
@admin_required
@limiter.limit("5 per minute")
def exporter_rapports():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des paramètres
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')
    format_type = request.args.get('format')
    group_by = request.args.get('group_by', 'date')
    
    # NOUVEAU : Récupération des actions cochées (liste)
    # Flask récupère les checkbox multiples avec getlist
    selected_actions = request.args.getlist('actions') 

    if not all([date_debut_str, date_fin_str, format_type]):
        flash("Paramètres manquants.", "warning")
        return redirect(url_for('admin.rapports'))

    if format_type not in ALLOWED_FORMATS:
        flash("Format non supporté.", "error")
        return redirect(url_for('admin.rapports'))

    try:
        # 2. Parsing Dates
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
        date_fin = date_fin.replace(hour=23, minute=59, second=59)

        if date_debut > date_fin:
            flash("Dates incohérentes.", "warning")
            return redirect(url_for('admin.rapports'))
            
        if (date_fin - date_debut).days > MAX_EXPORT_DAYS:
            flash(f"Période limitée à {MAX_EXPORT_DAYS} jours.", "warning")
            return redirect(url_for('admin.rapports'))

        # 3. Construction Requête
        query = db.select(
            Historique,
            Utilisateur.nom_utilisateur,
            Objet.nom.label('objet_nom')
        ).outerjoin(Utilisateur, Historique.utilisateur_id == Utilisateur.id)\
         .outerjoin(Objet, Historique.objet_id == Objet.id)\
         .filter(Historique.etablissement_id == etablissement_id)\
         .filter(Historique.timestamp >= date_debut)\
         .filter(Historique.timestamp <= date_fin)

        # --- LOGIQUE DE FILTRE ET TRI ---
        if group_by == 'action':
            # Si des actions spécifiques sont cochées, on filtre
            if selected_actions:
                query = query.filter(Historique.action.in_(selected_actions))
            
            # On trie par Action puis par Date
            query = query.order_by(Historique.action.asc(), Historique.timestamp.desc())
        else:
            # Tri chronologique standard
            query = query.order_by(Historique.timestamp.desc())

        # Protection RAM
        query = query.limit(MAX_EXPORT_ROWS)
        resultats = db.session.execute(query).all()

        if not resultats:
            flash("Aucune donnée trouvée pour ces critères.", "info")
            return redirect(url_for('admin.rapports'))

        # 4. Préparation Données
        data_export = []
        for h, user_name, obj_name in resultats:
            data_export.append({
                'date': h.timestamp.strftime('%d/%m/%Y'),
                'heure': h.timestamp.strftime('%H:%M'),
                'utilisateur': user_name or "Inconnu",
                'action': h.action,
                'objet': obj_name or "-",
                'details': h.details or ""
            })

        # Métadonnées enrichies
        filtre_info = "Tous types"
        if group_by == 'action' and selected_actions:
            filtre_info = ", ".join(selected_actions)

        metadata = {
            'etablissement': session.get('nom_etablissement', 'LabFlow'),
            'periode': f"Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}",
            'total': len(data_export),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'filtre': filtre_info # On pourra l'afficher dans le PDF si on veut
        }

        log_action('export_rapport', f"Format: {format_type}, Rows: {len(data_export)}")

        if format_type == 'excel':
            return generer_rapport_excel(data_export, metadata)
        else:
            return generer_rapport_pdf(data_export, metadata)

    except Exception as e:
        current_app.logger.error(f"Erreur export: {e}", exc_info=True)
        flash("Erreur technique lors de la génération.", "error")
        return redirect(url_for('admin.rapports'))



