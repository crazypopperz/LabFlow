# ============================================================
# IMPORTS
# ============================================================
import hashlib
from datetime import date, datetime
from io import BytesIO
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, jsonify, send_file)
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from db import db, Utilisateur, Parametre, Objet, Armoire, Categorie, Fournisseur, Kit, KitObjet,Budget, Depense, Echeance, Etablissement
from utils import admin_required, login_required, annee_scolaire_format

# ============================================================
# CRÉATION DU BLUEPRINT ADMIN
# ============================================================
admin_bp = Blueprint(
    'admin', 
    __name__,
    template_folder='../templates',
    url_prefix='/admin'
)


#=======================================
# GESTION DES ARMOIRES ET CATEGORIES
#=======================================
@admin_bp.route("/ajouter", methods=["POST"])
@admin_required
def ajouter():
    etablissement_id = session['etablissement_id']
    type_objet = request.form.get("type")
    nom = request.form.get("nom", "").strip()
    
    if not nom:
        flash("Le nom ne peut pas être vide.", "error")
        return redirect(request.referrer)

    Model = Armoire if type_objet == "armoire" else Categorie
    
    try:
        nouvel_element = Model(nom=nom, etablissement_id=etablissement_id)
        db.session.add(nouvel_element)
        db.session.commit()
        flash(f"L'élément '{nom}' a été créé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"L'élément '{nom}' existe déjà.", "error")
    
    redirect_to = "main.gestion_armoires" if type_objet == "armoire" else "main.gestion_categories"
    return redirect(url_for(redirect_to))


@admin_bp.route("/supprimer/<type_objet>/<int:id>", methods=["POST"])
@admin_required
def supprimer(type_objet, id):
    etablissement_id = session['etablissement_id']
    
    if type_objet == "armoire":
        Model = Armoire
        redirect_to = "main.gestion_armoires"
    elif type_objet == "categorie":
        Model = Categorie
        redirect_to = "main.gestion_categories"
    else:
        flash("Type d'élément non valide.", "error")
        return redirect(url_for('admin.admin'))

    element = db.session.get(Model, id)

    if not element or element.etablissement_id != etablissement_id:
        flash("Élément non trouvé ou accès non autorisé.", "error")
        return redirect(url_for(redirect_to))

    if type_objet == "armoire":
        count = db.session.query(Objet).filter_by(armoire_id=id, etablissement_id=etablissement_id).count()
        if count > 0:
            flash(f"Impossible de supprimer '{element.nom}' car elle contient encore {count} objet(s).", "error")
            return redirect(url_for(redirect_to))
    elif type_objet == "categorie":
        count = db.session.query(Objet).filter_by(categorie_id=id, etablissement_id=etablissement_id).count()
        if count > 0:
            flash(f"Impossible de supprimer '{element.nom}' car elle contient encore {count} objet(s).", "error")
            return redirect(url_for(redirect_to))

    try:
        nom_element = element.nom
        db.session.delete(element)
        db.session.commit()
        flash(f"L'élément '{nom_element}' a été supprimé avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue : {e}", "error")
    
    return redirect(url_for(redirect_to))


@admin_bp.route("/modifier_armoire", methods=["POST"])
@admin_required
def modifier_armoire():
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    armoire_id = data.get("id")
    nouveau_nom = data.get("nom", "").strip()

    if not all([armoire_id, nouveau_nom]):
        return jsonify(success=False, error="Données invalides"), 400

    armoire = db.session.get(Armoire, armoire_id)

    if not armoire or armoire.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Armoire non trouvée ou accès non autorisé."), 404

    try:
        armoire.nom = nouveau_nom
        db.session.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom)
    
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Ce nom d'armoire existe déjà."), 409 # 409 Conflict
    
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500


@admin_bp.route("/modifier_categorie", methods=["POST"])
@admin_required
def modifier_categorie():
    etablissement_id = session['etablissement_id']
    data = request.get_json()
    categorie_id = data.get("id")
    nouveau_nom = data.get("nom", "").strip()

    if not all([categorie_id, nouveau_nom]):
        return jsonify(success=False, error="Données invalides"), 400

    categorie = db.session.get(Categorie, categorie_id)

    if not categorie or categorie.etablissement_id != etablissement_id:
        return jsonify(success=False, error="Catégorie non trouvée ou accès non autorisé."), 404

    try:
        categorie.nom = nouveau_nom
        db.session.commit()
        return jsonify(success=True, nouveau_nom=nouveau_nom)
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Ce nom de catégorie existe déjà."), 409
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500



# ============================================================
# ROUTE ADMIN
# ============================================================
@admin_bp.route("/")
@admin_required
def admin():
    licence_info = {'is_pro': True, 'statut': 'Actif (SaaS)', 'instance_id': session.get('etablissement_id')}
    return render_template("admin.html", now=datetime.now(), licence=licence_info)


#==============================================================
# GESTION UTILISATEURS
#==============================================================
@admin_bp.route("/utilisateurs")
@admin_required
def gestion_utilisateurs():
    etablissement_id = session['etablissement_id']
    utilisateurs = db.session.execute(
        db.select(Utilisateur)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Utilisateur.nom_utilisateur)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Utilisateurs'}
    ]
    
    return render_template("admin_utilisateurs.html",
                           utilisateurs=utilisateurs,
                           breadcrumbs=breadcrumbs,
                           now=datetime.now)


@admin_bp.route("/utilisateurs/modifier_email/<int:id_user>", methods=["POST"])
@admin_required
def modifier_email_utilisateur(id_user):
    etablissement_id = session['etablissement_id']
    email = request.form.get('email', '').strip()
    if not email or '@' not in email:
        flash("Veuillez fournir une adresse e-mail valide.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    user = db.session.get(Utilisateur, id_user)
    if not user or user.etablissement_id != etablissement_id:
        flash("Utilisateur non trouvé.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))

    try:
        user.email = email
        db.session.commit()
        flash(f"L'adresse e-mail pour '{user.nom_utilisateur}' a été mise à jour.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur de base de données : {e}", "error")

    return redirect(url_for('admin.gestion_utilisateurs'))


@admin_bp.route("/utilisateurs/supprimer/<int:id_user>", methods=["POST"])
@admin_required
def supprimer_utilisateur(id_user):
    if id_user == session['user_id']:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "error")
        return redirect(url_for('admin.gestion_utilisateurs'))
    
    etablissement_id = session['etablissement_id']
    user = db.session.get(Utilisateur, id_user)
    
    if user and user.etablissement_id == etablissement_id:
        try:
            nom_user = user.nom_utilisateur
            db.session.delete(user)
            db.session.commit()
            flash(f"L'utilisateur '{nom_user}' a été supprimé.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la suppression : {e}", "error")
    else:
        flash("Utilisateur non trouvé.", "error")
        
    return redirect(url_for('admin.gestion_utilisateurs'))


#=============================================================
#=== GESTION UTLISATEURS / A REFACTORISER ENCORE ===
#============================================================
@admin_bp.route("/utilisateurs/promouvoir/<int:id_user>", methods=["POST"])
@admin_required
def promouvoir_utilisateur(id_user):
    flash("Fonctionnalité en cours de migration.", "info")
    return redirect(url_for('admin.gestion_utilisateurs'))

@admin_bp.route("/utilisateurs/reinitialiser_mdp/<int:id_user>", methods=["POST"])
@admin_required
def reinitialiser_mdp(id_user):
    flash("Fonctionnalité en cours de migration.", "info")
    return redirect(url_for('admin.gestion_utilisateurs'))
#=== FIN DE LA PARTIE A REFACTORISER ===


#=============================================================
# GESTION DES KITS
#=============================================================
@admin_bp.route("/kits")
@admin_required
def gestion_kits():
    etablissement_id = session['etablissement_id']
    
    kits_data = db.session.execute(
        db.select(Kit, func.count(KitObjet.id).label('count'))
        .outerjoin(KitObjet, Kit.id == KitObjet.kit_id)
        .filter(Kit.etablissement_id == etablissement_id)
        .group_by(Kit.id)
        .order_by(Kit.nom)
    ).mappings().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Kits'}
    ]
    
    return render_template("admin_kits.html",
                           kits=kits_data,
                           breadcrumbs=breadcrumbs)


@admin_bp.route("/kits/ajouter", methods=["POST"])
@admin_required
def ajouter_kit():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()

    if not nom:
        flash("Le nom du kit ne peut pas être vide.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    try:
        nouveau_kit = Kit(
            nom=nom,
            description=description,
            etablissement_id=etablissement_id
        )
        db.session.add(nouveau_kit)
        db.session.commit()
        flash(f"Le kit '{nom}' a été créé. Vous pouvez maintenant y ajouter des objets.", "success")
        # On redirige directement vers la page de modification
        return redirect(url_for('admin.modifier_kit', kit_id=nouveau_kit.id))
    except IntegrityError:
        db.session.rollback()
        flash(f"Un kit avec le nom '{nom}' existe déjà dans votre établissement.", "danger")
        return redirect(url_for('admin.gestion_kits'))


@admin_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    etablissement_id = session['etablissement_id']
    
    kit = db.session.get(Kit, kit_id)
    if not kit or kit.etablissement_id != etablissement_id:
        flash("Kit non trouvé ou accès non autorisé.", "danger")
        return redirect(url_for('admin.gestion_kits'))

    if request.method == "POST":
        objet_id_str = request.form.get("objet_id")
        if objet_id_str:
            try:
                objet_id = int(objet_id_str)
                quantite = int(request.form.get("quantite", 1))

                objet_a_ajouter = db.session.get(Objet, objet_id)
                if not objet_a_ajouter or objet_a_ajouter.etablissement_id != etablissement_id:
                    flash("Objet non trouvé.", "danger")
                    return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

                association_existante = db.session.execute(
                    db.select(KitObjet).filter_by(kit_id=kit.id, objet_id=objet_id)
                ).scalar_one_or_none()

                if association_existante:
                    association_existante.quantite += quantite
                    flash(f"Quantité de '{objet_a_ajouter.nom}' mise à jour dans le kit.", "success")
                else:
                    nouvelle_association = KitObjet(
                        kit_id=kit.id,
                        objet_id=objet_id,
                        quantite=quantite,
                        etablissement_id=etablissement_id
                    )
                    db.session.add(nouvelle_association)
                    flash(f"L'objet '{objet_a_ajouter.nom}' a été ajouté au kit.", "success")
                
                db.session.commit()

            except (ValueError, TypeError):
                flash("Données invalides pour l'ajout d'objet.", "danger")
        
        else:
            for key, value in request.form.items():
                if key.startswith("quantite_"):
                    try:
                        kit_objet_id = int(key.split("_")[1])
                        nouvelle_quantite = int(value)
                        
                        association = db.session.get(KitObjet, kit_objet_id)
                        if association and association.kit_id == kit.id:
                            if nouvelle_quantite > 0:
                                association.quantite = nouvelle_quantite
                            else:
                                db.session.delete(association)
                    except (ValueError, TypeError):
                        continue
            db.session.commit()
            flash("Quantités mises à jour.", "success")

        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))

    objets_in_kit = db.session.execute(
        db.select(KitObjet).filter_by(kit_id=kit.id).options(joinedload(KitObjet.objet))
    ).scalars().all()

    ids_objets_in_kit = [assoc.objet_id for assoc in objets_in_kit]

    objets_disponibles = db.session.execute(
        db.select(Objet)
        .filter(Objet.etablissement_id == etablissement_id, ~Objet.id.in_(ids_objets_in_kit))
        .order_by(Objet.nom)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Kits', 'url': url_for('admin.gestion_kits')},
        {'text': kit.nom}
    ]

    return render_template("admin_kit_modifier.html",
                           kit=kit,
                           breadcrumbs=breadcrumbs,
                           objets_in_kit=objets_in_kit,
                           objets_disponibles=objets_disponibles)


@admin_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=["POST"])
@admin_required
def retirer_objet_kit(kit_objet_id):
    etablissement_id = session['etablissement_id']
    
    association = db.session.get(KitObjet, kit_objet_id)
    if association and association.etablissement_id == etablissement_id:
        kit_id = association.kit_id
        db.session.delete(association)
        db.session.commit()
        flash("Objet retiré du kit.", "success")
        return redirect(url_for('admin.modifier_kit', kit_id=kit_id))
    
    flash("Erreur : objet du kit non trouvé.", "danger")
    return redirect(url_for('admin.gestion_kits'))


@admin_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    etablissement_id = session['etablissement_id']
    
    kit = db.session.get(Kit, kit_id)
    if kit and kit.etablissement_id == etablissement_id:
        nom_kit = kit.nom
        db.session.delete(kit) # La cascade s'occupe de supprimer les KitObjet
        db.session.commit()
        flash(f"Le kit '{nom_kit}' a été supprimé.", "success")
    else:
        flash("Kit non trouvé.", "danger")
        
    return redirect(url_for('admin.gestion_kits'))



#====================================================================
# GESTION DES ECHEANCES
#====================================================================
@admin_bp.route("/echeances", methods=['GET'])
@admin_required
def gestion_echeances():
    etablissement_id = session['etablissement_id']
    
    echeances = db.session.execute(
        db.select(Echeance)
        .filter_by(etablissement_id=etablissement_id)
        .order_by(Echeance.date_echeance.asc())
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Échéances'}
    ]
    
    return render_template("admin_echeances.html",
                           echeances=echeances,
                           breadcrumbs=breadcrumbs,
                           date_actuelle=date.today())


@admin_bp.route("/echeances/ajouter", methods=['POST'])
@admin_required
def ajouter_echeance():
    etablissement_id = session['etablissement_id']
    intitule = request.form.get('intitule', '').strip()
    date_echeance_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()

    if not intitule or not date_echeance_str:
        flash("L'intitulé et la date d'échéance sont obligatoires.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        date_echeance = datetime.strptime(date_echeance_str, '%Y-%m-%d').date()
        
        nouvelle_echeance = Echeance(
            intitule=intitule,
            date_echeance=date_echeance,
            details=details or None,
            etablissement_id=etablissement_id
        )
        db.session.add(nouvelle_echeance)
        db.session.commit()
        flash("L'échéance a été ajoutée avec succès.", "success")
    except ValueError:
        flash("Le format de la date est invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_echeances'))


@admin_bp.route("/echeances/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_echeance(id):
    etablissement_id = session['etablissement_id']
    
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance non trouvée ou accès non autorisé.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    intitule = request.form.get('intitule', '').strip()
    date_echeance_str = request.form.get('date_echeance')
    details = request.form.get('details', '').strip()
    traite = 1 if 'traite' in request.form else 0

    if not intitule or not date_echeance_str:
        flash("L'intitulé et la date d'échéance sont obligatoires.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        echeance.intitule = intitule
        echeance.date_echeance = datetime.strptime(date_echeance_str, '%Y-%m-%d').date()
        echeance.details = details or None
        echeance.traite = traite
        
        db.session.commit()
        flash("L'échéance a été mise à jour.", "success")
    except ValueError:
        flash("Le format de la date est invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_echeances'))


@admin_bp.route("/echeances/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_echeance(id):
    etablissement_id = session['etablissement_id']
    
    echeance = db.session.get(Echeance, id)
    if not echeance or echeance.etablissement_id != etablissement_id:
        flash("Échéance non trouvée ou accès non autorisé.", "danger")
        return redirect(url_for('admin.gestion_echeances'))

    try:
        db.session.delete(echeance)
        db.session.commit()
        flash("L'échéance a été supprimée avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_echeances'))



#==============================================================
# GESTION BUDGET
#==============================================================
@admin_bp.route("/budget", methods=['GET'])
@admin_required
def budget():
    etablissement_id = session['etablissement_id']
    now = datetime.now()
    annee_scolaire_actuelle = now.year if now.month >= 8 else now.year - 1

    try:
        annee_selectionnee = int(request.args.get('annee', annee_scolaire_actuelle))
    except (ValueError, TypeError):
        annee_selectionnee = annee_scolaire_actuelle

    budgets_archives = db.session.execute(
        db.select(Budget).filter_by(etablissement_id=etablissement_id).order_by(Budget.annee.desc())
    ).scalars().all()

    budget_affiche = db.session.execute(
        db.select(Budget).filter_by(etablissement_id=etablissement_id, annee=annee_selectionnee)
    ).scalar_one_or_none()

    if not budget_affiche and not budgets_archives:
        try:
            budget_affiche = Budget(
                annee=annee_selectionnee,
                montant_initial=0.0,
                etablissement_id=etablissement_id
            )
            db.session.add(budget_affiche)
            db.session.commit()
            budgets_archives.insert(0, budget_affiche)
            flash(f"Aucun budget n'existait. Un budget vide pour l'année {annee_selectionnee}-{annee_selectionnee+1} a été initialisé.", "info")
        except IntegrityError:
            db.session.rollback()
            budget_affiche = db.session.execute(
                db.select(Budget).filter_by(etablissement_id=etablissement_id, annee=annee_selectionnee)
            ).scalar_one_or_none()

    depenses = []
    total_depenses = 0
    solde = 0
    cloture_autorisee = False

    if budget_affiche:
        depenses = sorted(budget_affiche.depenses, key=lambda d: d.date_depense, reverse=True)
        
        total_depenses_result = db.session.query(func.sum(Depense.montant)).filter(Depense.budget_id == budget_affiche.id).scalar()
        total_depenses = total_depenses_result or 0
        solde = budget_affiche.montant_initial - total_depenses
        
        annee_fin_budget = budget_affiche.annee + 1
        date_limite_cloture = date(annee_fin_budget, 6, 1)
        if date.today() >= date_limite_cloture:
            cloture_autorisee = True

    budget_actuel_pour_modales = db.session.execute(
        db.select(Budget).filter_by(etablissement_id=etablissement_id, cloture=False).order_by(Budget.annee.desc())
    ).scalars().first()

    annee_proposee_pour_creation = annee_scolaire_actuelle
    if not budget_actuel_pour_modales and budgets_archives:
        derniere_annee = budgets_archives[0].annee
        annee_proposee_pour_creation = derniere_annee + 1

    fournisseurs = db.session.execute(
        db.select(Fournisseur).filter_by(etablissement_id=etablissement_id).order_by(Fournisseur.nom)
    ).scalars().all()
    
    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion Budgétaire'}
    ]
    return render_template(
        "budget.html",
        breadcrumbs=breadcrumbs,
        budget_affiche=budget_affiche,
        budget_actuel_pour_modales=budget_actuel_pour_modales,
        annee_proposee_pour_creation=annee_proposee_pour_creation,
        depenses=depenses,
        total_depenses=total_depenses,
        solde=solde,
        fournisseurs=fournisseurs,
        budgets_archives=budgets_archives,
        annee_selectionnee=annee_selectionnee,
        cloture_autorisee=cloture_autorisee,
        now=now
    )


@admin_bp.route("/budget/definir", methods=['POST'])
@admin_required
def definir_budget():
    etablissement_id = session['etablissement_id']
    montant_str = request.form.get('montant_initial')
    annee_str = request.form.get('annee')

    if not montant_str or not annee_str:
        flash("L'année et le montant sont obligatoires.", "danger")
        return redirect(url_for('admin.budget'))

    try:
        montant = float(montant_str.replace(',', '.'))
        annee = int(annee_str)
        if montant < 0 or annee < 2020:
            raise ValueError("Valeurs invalides")
    except ValueError:
        flash("Le montant ou l'année saisi(e) est invalide.", "danger")
        return redirect(url_for('admin.budget'))

    try:
        budget_existant = db.session.execute(
            db.select(Budget).filter_by(annee=annee, etablissement_id=etablissement_id)
        ).scalar_one_or_none()

        if budget_existant:
            budget_existant.montant_initial = montant
            budget_existant.cloture = False
            flash(f"Le budget pour l'année scolaire {annee}-{annee+1} a été mis à jour.", 'success')
        else:
            nouveau_budget = Budget(annee=annee, montant_initial=montant, etablissement_id=etablissement_id)
            db.session.add(nouveau_budget)
            flash(f"Le budget pour l'année scolaire {annee}-{annee+1} a été créé.", 'success')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.budget', annee=annee))


@admin_bp.route("/budget/depense/ajouter", methods=['POST'])
@admin_required
def ajouter_depense():
    etablissement_id = session['etablissement_id']
    budget_id = request.form.get('budget_id')
    contenu = request.form.get('contenu', '').strip()
    montant_str = request.form.get('montant')
    date_depense_str = request.form.get('date_depense')
    est_bon_achat = 'est_bon_achat' in request.form
    fournisseur_id = request.form.get('fournisseur_id')

    if not all([budget_id, contenu, montant_str, date_depense_str]):
        flash("Tous les champs sont obligatoires pour ajouter une dépense.", "danger")
        return redirect(request.referrer or url_for('admin.budget'))

    if not est_bon_achat and not fournisseur_id:
        flash("Veuillez sélectionner un fournisseur ou cocher la case 'Bon d'achat'.", "danger")
        return redirect(request.referrer or url_for('admin.budget'))

    try:
        montant = float(montant_str.replace(',', '.'))
        date_depense = datetime.strptime(date_depense_str, '%Y-%m-%d').date()
        if montant <= 0: raise ValueError()
    except (ValueError, TypeError):
        flash("Le montant ou la date est invalide.", "danger")
        return redirect(request.referrer or url_for('admin.budget'))

    budget = db.session.get(Budget, int(budget_id))
    if not budget or budget.etablissement_id != etablissement_id or budget.cloture:
        flash("Impossible d'ajouter une dépense : le budget est introuvable, n'appartient pas à votre établissement ou est clôturé.", 'danger')
        return redirect(url_for('admin.budget'))

    try:
        nouvelle_depense = Depense(
            date_depense=date_depense,
            contenu=contenu,
            montant=montant,
            est_bon_achat=est_bon_achat,
            fournisseur_id=int(fournisseur_id) if fournisseur_id and not est_bon_achat else None,
            budget_id=budget.id,
            etablissement_id=etablissement_id
        )
        db.session.add(nouvelle_depense)
        db.session.commit()
        flash("La dépense a été ajoutée avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")
    
    return redirect(request.referrer or url_for('admin.budget'))


@admin_bp.route("/budget/depense/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_depense(id):
    etablissement_id = session['etablissement_id']
    
    depense = db.session.get(Depense, id)
    if not depense or depense.etablissement_id != etablissement_id:
        flash("Dépense non trouvée ou accès non autorisé.", "danger")
        return redirect(url_for('admin.budget'))

    contenu = request.form.get('contenu', '').strip()
    montant_str = request.form.get('montant')
    date_depense_str = request.form.get('date_depense')
    est_bon_achat = 'est_bon_achat' in request.form
    fournisseur_id = request.form.get('fournisseur_id')

    if not all([contenu, montant_str, date_depense_str]):
        flash("Les champs contenu, montant et date sont obligatoires.", "danger")
        return redirect(request.referrer or url_for('admin.budget'))
    
    try:
        montant = float(montant_str.replace(',', '.'))
        date_depense = datetime.strptime(date_depense_str, '%Y-%m-%d').date()
        if montant <= 0: raise ValueError()
    except (ValueError, TypeError):
        flash("Le montant ou la date est invalide.", "danger")
        return redirect(request.referrer or url_for('admin.budget'))

    try:
        depense.montant = montant
        depense.date_depense = date_depense
        depense.contenu = contenu
        depense.est_bon_achat = est_bon_achat
        depense.fournisseur_id = int(fournisseur_id) if fournisseur_id and not est_bon_achat else None
        
        db.session.commit()
        flash("La dépense a été modifiée avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")
    
    return redirect(request.referrer or url_for('admin.budget'))


@admin_bp.route("/budget/depense/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_depense(id):
    etablissement_id = session['etablissement_id']
    
    depense = db.session.get(Depense, id)
    if depense and depense.etablissement_id == etablissement_id:
        try:
            db.session.delete(depense)
            db.session.commit()
            flash("La dépense a été supprimée avec succès.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Une erreur de base de données est survenue : {e}", "danger")
    else:
        flash("Dépense non trouvée ou accès non autorisé.", "danger")

    return redirect(request.referrer or url_for('admin.budget'))


@admin_bp.route("/budget/cloturer", methods=['POST'])
@admin_required
def cloturer_budget():
    etablissement_id = session['etablissement_id']
    budget_id = request.form.get('budget_id')

    budget = db.session.get(Budget, int(budget_id))
    if not budget or budget.etablissement_id != etablissement_id:
        flash("Budget non trouvé ou accès non autorisé.", "danger")
        return redirect(url_for('admin.budget'))

    annee_fin_budget = budget.annee + 1
    date_limite_cloture = date(annee_fin_budget, 6, 1)
    if date.today() < date_limite_cloture:
        flash(f"La clôture n'est autorisée qu'à partir du {date_limite_cloture.strftime('%d/%m/%Y')}.", "danger")
        return redirect(url_for('admin.budget', annee=budget.annee))

    if budget.cloture:
        flash(f"Le budget pour l'année scolaire {budget.annee}-{budget.annee+1} est déjà clôturé.", "warning")
        return redirect(url_for('admin.budget'))

    try:
        budget.cloture = True
        db.session.commit()
        flash(f"Le budget pour l'année scolaire {budget.annee}-{budget.annee+1} a été clôturé.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")
    
    return redirect(url_for('admin.budget'))



# ============================================================
#  GESTION DES FOURNISSEURS
# ============================================================
@admin_bp.route("/fournisseurs", methods=['GET'])
@admin_required
def gestion_fournisseurs():
    etablissement_id = session['etablissement_id']
    
    fournisseurs = db.session.execute(
        db.select(Fournisseur, func.count(Depense.id).label('depenses_count'))
        .outerjoin(Depense, Fournisseur.id == Depense.fournisseur_id)
        .filter(Fournisseur.etablissement_id == etablissement_id)
        .group_by(Fournisseur.id)
        .order_by(Fournisseur.nom)
    ).mappings().all()

    breadcrumbs = [
        {'text': 'Panneau d\'Administration', 'url': url_for('admin.admin')},
        {'text': 'Gestion des Fournisseurs'}
    ]
    
    return render_template("admin_fournisseurs.html",
                           fournisseurs=fournisseurs,
                           breadcrumbs=breadcrumbs)


@admin_bp.route("/fournisseurs/ajouter", methods=['POST'])
@admin_required
def ajouter_fournisseur():
    etablissement_id = session['etablissement_id']
    nom = request.form.get('nom', '').strip()
    site_web = request.form.get('site_web', '').strip()
    logo_url = request.form.get('logo_url', '').strip()

    if not nom:
        flash("Le nom du fournisseur est obligatoire.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    try:
        nouveau_fournisseur = Fournisseur(
            nom=nom,
            site_web=site_web or None,
            logo=logo_url or None,
            etablissement_id=etablissement_id
        )
        db.session.add(nouveau_fournisseur)
        db.session.commit()
        flash(f"Le fournisseur '{nom}' a été ajouté avec succès.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"Un fournisseur avec le nom '{nom}' existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_fournisseurs'))


@admin_bp.route("/fournisseurs/modifier/<int:id>", methods=['POST'])
@admin_required
def modifier_fournisseur(id):
    etablissement_id = session['etablissement_id']
    
    fournisseur = db.session.get(Fournisseur, id)
    if not fournisseur or fournisseur.etablissement_id != etablissement_id:
        flash("Fournisseur non trouvé ou accès non autorisé.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    nom = request.form.get('nom', '').strip()
    site_web = request.form.get('site_web', '').strip()
    logo_url = request.form.get('logo_url', '').strip()

    if not nom:
        flash("Le nom du fournisseur ne peut pas être vide.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    try:
        fournisseur.nom = nom
        fournisseur.site_web = site_web or None
        fournisseur.logo = logo_url or None
        db.session.commit()
        flash(f"Le fournisseur '{nom}' a été mis à jour.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"Un autre fournisseur avec le nom '{nom}' existe déjà.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_fournisseurs'))


@admin_bp.route("/fournisseurs/supprimer/<int:id>", methods=['POST'])
@admin_required
def supprimer_fournisseur(id):
    etablissement_id = session['etablissement_id']
    
    fournisseur = db.session.get(Fournisseur, id)
    if not fournisseur or fournisseur.etablissement_id != etablissement_id:
        flash("Fournisseur non trouvé ou accès non autorisé.", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    if fournisseur.depenses:
        flash(f"Impossible de supprimer '{fournisseur.nom}' car il est associé à {len(fournisseur.depenses)} dépense(s).", "danger")
        return redirect(url_for('admin.gestion_fournisseurs'))

    try:
        nom_fournisseur = fournisseur.nom
        db.session.delete(fournisseur)
        db.session.commit()
        flash(f"Le fournisseur '{nom_fournisseur}' a été supprimé.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur de base de données est survenue : {e}", "danger")

    return redirect(url_for('admin.gestion_fournisseurs'))















# ============================================================
# === SECTIONS EN ATTENTE DE MIGRATION (PLACEHOLDERS) ===
# ============================================================
# Pour chaque route qui manquait, on crée une fonction vide qui
# affiche un message et redirige vers le panel admin.
# Cela permet à `url_for()` de fonctionner et à la page de se charger.

@admin_bp.route("/importer")
@admin_required
def importer_page():
    flash("L'importation en masse est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/rapports")
@admin_required
def rapports():
    flash("La génération de rapports est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/exporter/<format>")
@admin_required
def exporter_inventaire(format):
    flash("L'exportation de l'inventaire est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/activer_licence", methods=["POST"])
@admin_required
def activer_licence():
    flash("La gestion de licence est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

# --- AJOUTE CE BLOC DE CODE ICI ---
@admin_bp.route("/telecharger_db")
@admin_required
def telecharger_db():
    flash("La sauvegarde de la base de données est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))

@admin_bp.route("/importer_db", methods=["POST"])
@admin_required
def importer_db():
    flash("L'importation de la base de données est en cours de migration.", "info")
    return redirect(url_for('admin.admin'))
# --- FIN DE L'AJOUT ---


@admin_bp.route("/debug/db-state")
@admin_required
def debug_db_state():
    """Affiche l'état actuel de la base de données pour le débogage."""
    current_etablissement_id = session.get('etablissement_id')
    
    # On récupère TOUS les objets, sans filtre, pour voir ce qu'il y a vraiment
    all_objets = db.session.execute(db.select(Objet)).scalars().all()
    
    # On récupère tous les établissements
    all_etablissements = db.session.execute(db.select(Etablissement)).scalars().all()

    return render_template("debug_db_state.html",
                           current_etablissement_id=current_etablissement_id,
                           all_objets=all_objets,
                           all_etablissements=all_etablissements)









'''
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


#==================================
# GESTION DU BUDGET
#==================================
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

#======================================================================
# GESTION DES RAPPORTS (Exports)
#======================================================================
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

@admin_bp.route("/importer", methods=['GET'])
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
        "Nom", "Quantité", "Seuil", "Armoire", "Catégorie", 
        "Date Péremption", "Image (URL)"
    ]
    sheet.append(headers)

    # --- DÉFINITION DES STYLES ---
    header_font = Font(name='Calibri', bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")
    # NOUVEAU : On définit un alignement centré
    center_alignment = Alignment(horizontal='center', vertical='center')
    note_font = Font(name='Calibri', italic=True, color="808080")

    # --- APPLICATION DES STYLES ---
    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment # On applique l'alignement centré

    # --- AJUSTEMENT DES LARGEURS DE COLONNES (CORRIGÉ) ---
    sheet.column_dimensions['A'].width = 40  # Nom
    sheet.column_dimensions['B'].width = 15  # Quantité
    sheet.column_dimensions['C'].width = 15  # Seuil
    sheet.column_dimensions['D'].width = 25  # Armoire
    sheet.column_dimensions['E'].width = 25  # Catégorie
    sheet.column_dimensions['F'].width = 20  # Date Péremption
    sheet.column_dimensions['G'].width = 50  # Image (URL)

    date_header_cell = sheet['F1']
    date_header_cell.comment = Comment("Le format de date doit être AAAA-MM-JJ.", "Note de format")

    # --- GÉNÉRATION DU FICHIER ---
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
    if 'fichier_excel' not in request.files:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('admin.importer_page'))

    fichier = request.files['fichier_excel']
    if fichier.filename == '' or not fichier.filename.endswith('.xlsx'):
        flash("Veuillez sélectionner un fichier Excel (.xlsx) valide.", "error")
        return redirect(url_for('admin.importer_page'))

    db = get_db()
    errors = []
    skipped_items = []
    success_count = 0

    existing_objects = {row['nom'].lower() for row in db.execute("SELECT nom FROM objets").fetchall()}
    armoires_db = {a['nom'].lower(): a['id'] for a in get_all_armoires(db)}
    categories_db = {c['nom'].lower(): c['id'] for c in get_all_categories(db)}

    try:
        workbook = load_workbook(fichier)
        sheet = workbook.active
        
        db.execute("BEGIN")

        for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if all(cell is None for cell in row):
                continue

            if len(row) < 5:
                errors.append(f"Ligne {i}: Manque de colonnes. Assurez-vous que les 5 premières colonnes sont présentes.")
                continue

            nom, quantite, seuil, armoire, categorie = (row[0], row[1], row[2], row[3], row[4])
            date_peremption = row[5] if len(row) > 5 else None
            image_url = row[6] if len(row) > 6 else None

            if not all([nom, quantite, seuil, armoire, categorie]):
                errors.append(f"Ligne {i}: Les champs Nom, Quantité, Seuil, Armoire et Catégorie sont obligatoires.")
                continue

            if str(nom).lower() in existing_objects:
                skipped_items.append(nom)
                continue

            try:
                quantite_int = int(quantite)
                seuil_int = int(seuil)
            except (ValueError, TypeError):
                errors.append(f"Ligne {i}: La quantité et le seuil doivent être des nombres entiers.")
                continue

            armoire_id = armoires_db.get(str(armoire).lower())
            if not armoire_id:
                errors.append(f"Ligne {i}: L'armoire '{armoire}' n'existe pas.")
                continue

            categorie_id = categories_db.get(str(categorie).lower())
            if not categorie_id:
                errors.append(f"Ligne {i}: La catégorie '{categorie}' n'existe pas.")
                continue
            
            date_peremption_db = None
            if date_peremption:
                try:
                    if isinstance(date_peremption, datetime):
                        date_peremption_db = date_peremption.strftime('%Y-%m-%d')
                    else:
                        date_peremption_db = datetime.strptime(str(date_peremption).split(' ')[0], '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    errors.append(f"Ligne {i}: Le format de la date de péremption est invalide (doit être AAAA-MM-JJ).")
                    continue
            
            image_url_db = None
            if image_url:
                image_url = str(image_url).strip()
                valid_extensions = ('.jpg', '.jpeg', '.png', '.svg', '.webp')
                
                try:
                    parsed_url = urlparse(image_url)
                    path = parsed_url.path.lower()
         
                    if (parsed_url.scheme in ['http', 'https'] and 
                        any(ext in path for ext in valid_extensions)):
                        image_url_db = image_url
                    else:
                        errors.append(f"Ligne {i}: L'URL de l'image semble invalide. Elle doit être un lien internet complet (http/https) vers une image (.jpg, .png, etc.).")
                        continue
                except Exception:
                    errors.append(f"Ligne {i}: L'URL de l'image n'a pas pu être analysée.")
                    continue

            db.execute(
                """INSERT INTO objets (nom, quantite_physique, seuil, armoire_id, categorie_id, date_peremption, image_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nom, quantite_int, seuil_int, armoire_id, categorie_id, date_peremption_db, image_url_db)
            )
            success_count += 1

        if errors:
            db.rollback()
            for error in errors:
                flash(error, "error")
        else:
            db.commit()
            if success_count > 0:
                flash(f"Importation réussie ! {success_count} nouvel/nouveaux objet(s) ajouté(s).", "success")
            if skipped_items:
                flash(f"Attention : {len(skipped_items)} objet(s) ont été ignoré(s) car ils existent déjà : {', '.join(skipped_items)}.", "warning")

    except Exception as e:
        db.rollback()
        flash(f"Une erreur inattendue est survenue lors de la lecture du fichier : {e}", "error")

    return redirect(url_for('admin.importer_page'))
'''