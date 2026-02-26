# ============================================================
# FICHIER : views/admin_budget.py
# Gestion budget, dépenses, fournisseurs, échéances
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from io import BytesIO
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from extensions import limiter
from db import db, Budget, Depense, Fournisseur, Echeance, Historique
from utils import admin_required, log_action, allowed_file

admin_budget_bp = Blueprint('admin_budget', __name__, url_prefix='/admin')

@admin_budget_bp.route("/echeances", methods=['GET'])
@admin_required
def gestion_echeances():
    etablissement_id = session['etablissement_id']
    echeances = db.session.execute(db.select(Echeance).filter_by(etablissement_id=etablissement_id).order_by(Echeance.date_echeance.asc())).scalars().all()
    breadcrumbs = [{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Échéances'}]
    return render_template("admin_echeances.html", echeances=echeances, breadcrumbs=breadcrumbs, date_actuelle=date.today())

@admin_budget_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    etablissement_id = session['etablissement_id']
    intitule = request.form.get('intitule', '').strip()
    date_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()

    if not intitule or not date_str:
        flash("Champs obligatoires manquants.", "warning")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        date_echeance = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.add(Echeance(intitule=intitule, date_echeance=date_echeance, details=details or None, etablissement_id=etablissement_id))
        db.session.commit()
        flash("Échéance ajoutée.", "success")
    except ValueError:
        flash("Format de date invalide.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur ajout échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_budget_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        echeance.intitule = request.form.get('intitule', '').strip()
        echeance.date_echeance = datetime.strptime(request.form.get('date_echeance'), '%Y-%m-%d').date()
        echeance.details = request.form.get('details', '').strip() or None
        echeance.traite = 1 if 'traite' in request.form else 0
        db.session.commit()
        flash("Échéance modifiée.", "success")
    except ValueError:
        flash("Format de date invalide.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur modif échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

@admin_budget_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    etablissement_id = session['etablissement_id']
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance introuvable.", "danger")
        return redirect(url_for('admin.gestion_echeances'))
    try:
        db.session.delete(echeance)
        db.session.commit()
        flash("Échéance supprimée.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur suppression échéance", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.gestion_echeances'))

# ============================================================
# GESTION BUDGET
# ============================================================
@admin_budget_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    etablissement_id = session['etablissement_id']
    now = datetime.now()
    annee_scolaire_actuelle = now.year if now.month >= 8 else now.year - 1
    try:
        annee_selectionnee = int(request.args.get('annee', annee_scolaire_actuelle))
    except ValueError:
        annee_selectionnee = annee_scolaire_actuelle

    budgets_archives = db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id).order_by(Budget.annee.desc())).scalars().all()
    budget_affiche = db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id, annee=annee_selectionnee)).scalar_one_or_none()
    if not budget_affiche and session.get('user_role') != 'admin':
        flash("Le budget n'a pas encore été défini par l'administrateur.", "info")
        return redirect(url_for('main.index'))

    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_affiche:
        depenses = db.session.execute(
            db.select(Depense).filter_by(budget_id=budget_affiche.id).options(joinedload(Depense.fournisseur)).order_by(Depense.date_depense.desc())
        ).scalars().all()
        total_depenses = sum(d.montant for d in depenses)
        solde = budget_affiche.montant_initial - total_depenses
        if date.today() >= date(budget_affiche.annee + 1, 6, 1): cloture_autorisee = True

    budget_actuel_pour_modales = budget_affiche if budget_affiche and not budget_affiche.cloture else db.session.execute(db.select(Budget).filter_by(etablissement_id=etablissement_id, cloture=False).order_by(Budget.annee.desc())).scalars().first()
    annee_proposee = annee_scolaire_actuelle
    if budgets_archives and budgets_archives[0].annee >= annee_scolaire_actuelle: annee_proposee = budgets_archives[0].annee + 1
    fournisseurs = db.session.execute(db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)).scalars().all()
    
    return render_template("budget.html", breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Budget'}], 
                           budget_affiche=budget_affiche, budget_actuel_pour_modales=budget_actuel_pour_modales,
                           annee_proposee_pour_creation=annee_proposee, depenses=depenses, total_depenses=total_depenses,
                           solde=solde, fournisseurs=fournisseurs, budgets_archives=budgets_archives,
                           annee_selectionnee=annee_selectionnee, cloture_autorisee=cloture_autorisee, now=now)

@admin_budget_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    etablissement_id = session['etablissement_id']
    try:
        montant = float(request.form.get('montant_initial', '0').replace(',', '.'))
        annee = int(request.form.get('annee'))
        if montant < 0: raise ValueError("Montant négatif.")
        
        budget = db.session.execute(db.select(Budget).filter_by(annee=annee, etablissement_id=etablissement_id)).scalar_one_or_none()
        if budget:
            budget.montant_initial = montant
            budget.cloture = False
            flash(f"Budget {annee} mis à jour.", "success")
        else:
            db.session.add(Budget(annee=annee, montant_initial=montant, etablissement_id=etablissement_id))
            flash(f"Budget {annee} créé.", "success")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur définition budget", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.budget', annee=annee if 'annee' in locals() else None))

@admin_budget_bp.route("/budget/depense/ajouter", methods=['POST'])
@admin_required
def ajouter_depense():
    etablissement_id = session['etablissement_id']
    
    try:
        # 1. Validation Budget
        budget_id = int(request.form.get('budget_id'))
        budget = db.session.get(Budget, budget_id)
        
        if not budget or budget.etablissement_id != etablissement_id:
            raise ValueError("Budget invalide ou accès interdit.")
        
        if budget.cloture:
            raise ValueError("Impossible d'ajouter une dépense à un budget clôturé.")

        # 2. Récupération données
        est_bon_achat = 'est_bon_achat' in request.form
        montant_str = request.form.get('montant', '0').replace(',', '.')
        contenu = request.form.get('contenu', '').strip()
        date_str = request.form.get('date_depense')
        
        # 3. Validation montant
        try:
            montant = round(float(montant_str), 2)
        except ValueError:
            raise ValueError("Le format du montant est invalide.")

        MONTANT_MAX = current_app.config.get('DEPENSE_MONTANT_MAX', 1_000_000)
        if montant <= 0 or montant > MONTANT_MAX:
            raise ValueError(f"Le montant doit être positif et inférieur à {MONTANT_MAX:,.0f} €.")
        
        # 4. Validation contenu
        if not contenu:
            raise ValueError("La description ne peut pas être vide.")
        if len(contenu) > 200:
            raise ValueError("La description est trop longue (max 200 caractères).")
        
        # 5. Validation date
        try:
            date_depense = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Format de date invalide.")

        date_min = (datetime.now() - timedelta(days=365*10)).date()
        if date_depense < date_min or date_depense > datetime.now().date():
            raise ValueError("La date doit être comprise entre il y a 10 ans et aujourd'hui.")
        
        # 6. Validation fournisseur
        fournisseur_id = None
        if not est_bon_achat:
            fournisseur_id_raw = request.form.get('fournisseur_id')
            if fournisseur_id_raw:
                try:
                    f_id = int(fournisseur_id_raw)
                    fournisseur = db.session.query(Fournisseur).filter_by(
                        id=f_id, 
                        etablissement_id=etablissement_id
                    ).first()
                    if not fournisseur:
                        raise ValueError("Fournisseur invalide ou introuvable.")
                    fournisseur_id = f_id
                except (ValueError, TypeError):
                    raise ValueError("ID Fournisseur invalide.")

        # 7. Création de la dépense
        db.session.add(Depense(
            date_depense=date_depense,
            contenu=contenu,
            montant=montant,
            est_bon_achat=est_bon_achat,
            fournisseur_id=fournisseur_id,
            budget_id=budget.id,
            etablissement_id=etablissement_id
        ))
        db.session.commit()
        
        current_app.logger.info(f"Dépense créée pour établissement {etablissement_id}")
        flash("Dépense ajoutée avec succès.", "success")
        
    except ValueError as e:
        flash(str(e), "error")
    except IntegrityError:
        db.session.rollback()
        flash("Erreur de cohérence des données.", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur ajout dépense: {e}", exc_info=True)
        flash("Erreur technique lors de l'ajout.", "error")
    
    return redirect(url_for('admin.budget'))

@admin_budget_bp.route("/budget/depense/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    etablissement_id = session['etablissement_id']
    depense = db.session.get(Depense, id)
    if depense and depense.etablissement_id == etablissement_id:
        try:
            db.session.delete(depense)
            db.session.commit()
            flash("Dépense supprimée.", "success")
        except Exception:
            db.session.rollback()
            current_app.logger.error("Erreur suppression dépense", exc_info=True)
            flash("Erreur technique.", "danger")
    else:
        flash("Dépense introuvable.", "danger")
    return redirect(url_for('admin.budget'))
    

@admin_budget_bp.route("/budget/depense/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_depense(id):
    etablissement_id = session['etablissement_id']
    
    # 1. Verrouillage + récupération (SELECT ... FOR UPDATE)
    depense = db.session.query(Depense).with_for_update().filter_by(id=id).first()

    # 2. Vérifications IDOR
    if not depense or depense.etablissement_id != etablissement_id:
        flash("Dépense introuvable ou accès interdit.", "error")
        return redirect(url_for('admin.budget'))
    
    if depense.budget.etablissement_id != etablissement_id:
        flash("Accès interdit (Incohérence Budget).", "error")
        return redirect(url_for('admin.budget'))

    # 3. Vérification clôture
    if depense.budget.cloture:
        flash("Impossible de modifier une dépense d'un budget clôturé.", "warning")
        return redirect(url_for('admin.budget'))

    try:
        # 4. Récupération données
        est_bon_achat = 'est_bon_achat' in request.form
        montant_str = request.form.get('montant', '0').replace(',', '.')
        contenu = request.form.get('contenu', '').strip()
        date_str = request.form.get('date_depense')
        
        # 5. Validation montant
        try:
            montant = round(float(montant_str), 2)
        except ValueError:
            raise ValueError("Le format du montant est invalide.")

        # Utilisation d'une config ou valeur par défaut
        MONTANT_MAX = current_app.config.get('DEPENSE_MONTANT_MAX', 1_000_000)
        if montant <= 0 or montant > MONTANT_MAX:
            raise ValueError(f"Le montant doit être positif et inférieur à {MONTANT_MAX:,.0f} €.")
        
        # 6. Validation contenu
        if not contenu:
            raise ValueError("La description ne peut pas être vide.")
        if len(contenu) > 200:
            raise ValueError("La description est trop longue (max 200 caractères).")
        
        # 7. Validation date
        try:
            date_depense = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Format de date invalide.")

        # Règle métier : pas de date future, pas de date trop ancienne (> 10 ans)
        date_min = (datetime.now() - timedelta(days=365*10)).date()
        if date_depense < date_min or date_depense > datetime.now().date():
            raise ValueError("La date doit être comprise entre il y a 10 ans et aujourd'hui.")
        
        # 8. Validation fournisseur
        fournisseur_id = None
        if not est_bon_achat:
            fournisseur_id_raw = request.form.get('fournisseur_id')
            if fournisseur_id_raw:
                try:
                    f_id = int(fournisseur_id_raw)
                    # Vérification stricte de l'appartenance du fournisseur
                    fournisseur = db.session.query(Fournisseur).filter_by(
                        id=f_id, 
                        etablissement_id=etablissement_id
                    ).first()
                    
                    if not fournisseur:
                        raise ValueError("Fournisseur invalide ou introuvable.")
                    fournisseur_id = f_id
                except (ValueError, TypeError):
                    raise ValueError("ID Fournisseur invalide.")

        # 9. Mise à jour
        depense.date_depense = date_depense
        depense.contenu = contenu
        depense.montant = montant
        depense.est_bon_achat = est_bon_achat
        depense.fournisseur_id = fournisseur_id

        db.session.commit()
        
        # 10. Log audit
        current_app.logger.info(
            f"Dépense {id} modifiée par User {session.get('user_id')} (Etab {etablissement_id})"
        )
        flash("Dépense modifiée avec succès.", "success")

    except ValueError as e:
        flash(str(e), "error")
    except IntegrityError:
        db.session.rollback()
        flash("Erreur de cohérence des données.", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur modification dépense {id}: {e}", exc_info=True)
        flash("Erreur technique lors de la modification.", "error")

    return redirect(url_for('admin.budget'))



@admin_budget_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    etablissement_id = session['etablissement_id']
    try:
        budget = db.session.get(Budget, int(request.form.get('budget_id')))
        if budget and budget.etablissement_id == etablissement_id:
            budget.cloture = True
            db.session.commit()
            flash("Budget clôturé.", "success")
        else:
            flash("Budget introuvable.", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur clôture budget", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin.budget'))

@admin_budget_bp.route("/budget/exporter", methods=['GET'])
@admin_required
def exporter_budget():
    etablissement_id = session['etablissement_id']
    date_debut_str = request.args.get('date_debut')
    date_fin_str = request.args.get('date_fin')
    format_type = request.args.get('format')
    
    redirect_url = url_for('main.voir_budget')

    if not all([date_debut_str, date_fin_str, format_type]):
        flash("Paramètres manquants.", "error")
        return redirect(redirect_url)
    
    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        depenses = db.session.execute(
            db.select(Depense).options(joinedload(Depense.fournisseur))
            .filter_by(etablissement_id=etablissement_id)
            .filter(Depense.date_depense >= date_debut, Depense.date_depense <= date_fin)
            .order_by(Depense.date_depense.asc())
        ).scalars().all()
        
        if not depenses:
            flash("Aucune dépense sur cette période.", "warning")
            return redirect(redirect_url)
        
        data_export = []
        total = 0.0
        for d in depenses:
            nom_fournisseur = "Petit matériel" if d.est_bon_achat else (d.fournisseur.nom if d.fournisseur else "Inconnu")
            data_export.append({
                'date': d.date_depense.strftime('%d/%m/%Y'),
                'fournisseur': nom_fournisseur,
                'contenu': d.contenu or "-",
                'montant': d.montant
            })
            total += d.montant
        
        metadata = {
            'etablissement': session.get('nom_etablissement', 'Mon Établissement'),
            'date_debut': date_debut.strftime('%d/%m/%Y'),
            'date_fin': date_fin.strftime('%d/%m/%Y'),
            'date_generation': datetime.now().strftime('%d/%m/%Y à %H:%M'),
            'nombre_depenses': len(data_export),
            'total': total
        }
        
        if format_type == 'excel': 
            return generer_budget_excel_pro(data_export, metadata)
        else: 
            return generer_budget_pdf_pro(data_export, metadata)
    
    except Exception as e:
        current_app.logger.error(f"Erreur export budget: {e}", exc_info=True)
        flash("Erreur technique lors de l'export.", "error")
        return redirect(redirect_url)

# ============================================================
# GESTION FOURNISSEURS
# ============================================================
@admin_budget_bp.route("/fournisseurs", methods=['GET'])
@admin_required
def gestion_fournisseurs():
    etablissement_id = session['etablissement_id']
    fournisseurs = db.session.execute(
        db.select(Fournisseur, func.count(Depense.id).label('depenses_count'))
        .outerjoin(Depense, Fournisseur.id == Depense.fournisseur_id)
        .filter(Fournisseur.etablissement_id == etablissement_id)
        .group_by(Fournisseur.id).order_by(Fournisseur.nom)
    ).all()
    return render_template("admin_fournisseurs.html", fournisseurs=fournisseurs, breadcrumbs=[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Fournisseurs'}])

@admin_budget_bp.route("/fournisseurs/ajouter", methods=["POST"])
@admin_required
def ajouter_fournisseur():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom")
    site_web = request.form.get("site_web")
    
    try:
        logo_filename = None
        
        # 1. Gestion Fichier (Sécurisée avec filetype)
        if 'logo_file' in request.files:
            file = request.files['logo_file']
            if file and file.filename != '':
                # A. Vérification Taille
                file.seek(0, 2)
                if file.tell() > MAX_FILE_SIZE:
                    raise ValueError("Image trop volumineuse (Max 10Mo).")
                file.seek(0)
                
                # B. Vérification Type (Via module filetype)
                header = file.read(261) # filetype a besoin de 261 bytes max
                file.seek(0)
                kind = filetype.guess(header)
                
                if kind is None or kind.extension not in ['jpg', 'png', 'gif']:
                    raise ValueError("Format image non supporté (JPG, PNG, GIF uniquement).")
                
                # C. Upload
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"{ts}_{filename}"
                
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'fournisseurs')
                os.makedirs(upload_folder, exist_ok=True)
                    
                file.save(os.path.join(upload_folder, unique_filename))
                logo_filename = unique_filename

        # 2. Gestion URL (Si pas de fichier)
        if not logo_filename:
            logo_url = request.form.get("logo_url", "").strip()
            if logo_url:
                if validate_url(logo_url):
                    logo_filename = logo_url
                else:
                    raise ValueError("URL du logo invalide.")

        # 3. Insertion DB
        new_fournisseur = Fournisseur(
            nom=nom,
            site_web=site_web,
            logo=logo_filename,
            etablissement_id=etablissement_id
        )
        db.session.add(new_fournisseur)
        db.session.commit()
        flash("Fournisseur ajouté avec succès.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur ajout fournisseur", exc_info=True)
        flash("Erreur technique lors de l'ajout.", "error")

    return redirect(url_for('main.voir_fournisseurs'))

@admin_budget_bp.route("/fournisseurs/modifier/<int:id>", methods=["POST"])
@admin_required
def modifier_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    
    if not fournisseur or fournisseur.etablissement_id != etablissement_id:
        flash("Fournisseur introuvable.", "error")
        return redirect(url_for('main.voir_fournisseurs'))

    try:
        fournisseur.nom = request.form.get("nom")
        fournisseur.site_web = request.form.get("site_web")

        # 1. Gestion Fichier (Sécurisée avec filetype)
        if 'logo_file' in request.files:
            file = request.files['logo_file']
            if file and file.filename != '':
                file.seek(0, 2)
                if file.tell() > MAX_FILE_SIZE:
                    raise ValueError("Image trop volumineuse (Max 10Mo).")
                file.seek(0)
                
                header = file.read(261)
                file.seek(0)
                kind = filetype.guess(header)
                
                if kind is None or kind.extension not in ['jpg', 'png', 'gif']:
                    raise ValueError("Format image non supporté.")
                
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"{ts}_{filename}"
                
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'fournisseurs')
                os.makedirs(upload_folder, exist_ok=True)
                    
                file.save(os.path.join(upload_folder, unique_filename))
                fournisseur.logo = unique_filename
        
        # 2. Gestion URL (Seulement si renseignée et pas de fichier uploadé)
        logo_url = request.form.get("logo_url", "").strip()
        if logo_url and 'logo_file' in request.files and request.files['logo_file'].filename == '':
            if validate_url(logo_url):
                fournisseur.logo = logo_url
            else:
                raise ValueError("URL du logo invalide.")

        db.session.commit()
        flash("Fournisseur modifié.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Erreur modif fournisseur", exc_info=True)
        flash("Erreur technique.", "error")

    return redirect(url_for('main.voir_fournisseurs'))

@admin_budget_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    etablissement_id = session['etablissement_id']
    fournisseur = db.session.get(Fournisseur, id)
    if fournisseur and fournisseur.etablissement_id == etablissement_id:
        if fournisseur.depenses:
            flash("Impossible : lié à des dépenses.", "danger")
        else:
            try:
                db.session.delete(fournisseur)
                db.session.commit()
                flash("Fournisseur supprimé.", "success")
            except Exception:
                db.session.rollback()
                current_app.logger.error("Erreur suppression fournisseur", exc_info=True)
                flash("Erreur technique.", "danger")
    else:
        flash("Fournisseur introuvable.", "danger")
    return redirect(url_for('admin.gestion_fournisseurs'))
