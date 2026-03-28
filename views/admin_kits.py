# ============================================================
# FICHIER : views/admin_kits.py
# Gestion des kits (CRUD, composants)
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from extensions import limiter
from db import db, Objet, Kit, KitObjet, Historique
from utils import admin_required, log_action

admin_kits_bp = Blueprint('admin_kits', __name__, url_prefix='/admin')
@admin_kits_bp.route("/kits")
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
    breadcrumbs=[{'text': 'Tableau de Bord', 'url': url_for('inventaire.index')}, {'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Gestion des kits', 'url': None}]
    return render_template("admin_kits.html", kits=kits_data, breadcrumbs=breadcrumbs)

@admin_kits_bp.route("/kits/ajouter", methods=["POST"])
@admin_required
@limiter.limit("10 per minute")
def ajouter_kit():
    etablissement_id = session['etablissement_id']
    nom = request.form.get("nom", "").strip()
    description = request.form.get("description", "").strip()

    if not nom:
        flash("Le nom du kit est requis.", "danger")
        return redirect(url_for('admin_kits.gestion_kits'))

    try:
        nouveau_kit = Kit(nom=nom, description=description, etablissement_id=etablissement_id)
        db.session.add(nouveau_kit)
        db.session.commit()
        flash(f"Kit '{nom}' créé.", "success")
        return redirect(url_for('admin_kits.modifier_kit', kit_id=nouveau_kit.id))
    except IntegrityError:
        db.session.rollback()
        flash("Un kit portant ce nom existe déjà.", "danger")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur ajout kit", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin_kits.gestion_kits'))

@admin_kits_bp.route("/kits/modifier/<int:kit_id>", methods=["GET", "POST"])
@admin_required
def modifier_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    
    if not kit or kit.etablissement_id != etablissement_id:
        flash("Kit introuvable.", "danger")
        return redirect(url_for('admin_kits.gestion_kits'))

    if request.method == "POST":
        try:
            # CAS 1 : Modification du Nom/Description
            if 'nom_kit' in request.form:
                nouveau_nom = request.form.get('nom_kit', '').strip()
                nouvelle_desc = request.form.get('description_kit', '').strip()
                
                if not nouveau_nom:
                    flash("Le nom du kit ne peut pas être vide.", "warning")
                else:
                    kit.nom = nouveau_nom
                    kit.description = nouvelle_desc
                    db.session.commit()
                    flash("Informations du kit mises à jour.", "success")

            # CAS 2 : Ajout d'un objet
            elif request.form.get("objet_id"):
                objet_id = int(request.form.get("objet_id"))
                quantite = int(request.form.get("quantite", 1))
                
                if quantite <= 0: raise ValueError("Quantité > 0 requise.")

                objet = db.session.get(Objet, objet_id)
                if not objet or objet.etablissement_id != etablissement_id:
                    raise ValueError("Objet invalide.")
                
                assoc = db.session.execute(db.select(KitObjet).filter_by(kit_id=kit.id, objet_id=objet_id)).scalar_one_or_none()
                if assoc:
                    assoc.quantite += quantite
                else:
                    db.session.add(KitObjet(kit_id=kit.id, objet_id=objet_id, quantite=quantite, etablissement_id=etablissement_id))
                
                db.session.commit()
                flash(f"Objet '{objet.nom}' ajouté.", "success")

            # CAS 3 : Mise à jour des quantités (Tableau)
            else:
                modifs = 0
                for key, value in request.form.items():
                    if key.startswith("quantite_"):
                        try:
                            # CORRECTION : Validation stricte de l'ID
                            k_id_str = key.split("_")[1]
                            if not k_id_str.isdigit(): continue
                            
                            k_id = int(k_id_str)
                            val = int(value)
                            
                            assoc = db.session.get(KitObjet, k_id)
                            # Vérification supplémentaire d'appartenance
                            if assoc and assoc.kit_id == kit.id:
                                if val > 0:
                                    assoc.quantite = val
                                    modifs += 1
                                else:
                                    db.session.delete(assoc)
                                    modifs += 1
                        except (ValueError, IndexError): 
                            continue
                if modifs > 0:
                    db.session.commit()
                    flash("Quantités mises à jour.", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Erreur modif kit", exc_info=True)
            flash(f"Erreur : {str(e)}", "danger")
            
        return redirect(url_for('admin_kits.modifier_kit', kit_id=kit_id))

    # Chargement des données pour l'affichage
    objets_in_kit = db.session.execute(
        db.select(KitObjet)
        .filter_by(kit_id=kit.id)
        .options(joinedload(KitObjet.objet))
    ).scalars().all()
    
    ids_in_kit = [o.objet_id for o in objets_in_kit]
    
    objets_disponibles = db.session.execute(
        db.select(Objet)
        .filter(Objet.etablissement_id == etablissement_id)
        .filter(~Objet.id.in_(ids_in_kit) if ids_in_kit else True)
        .order_by(Objet.nom)
        .limit(500)
    ).scalars().all()

    breadcrumbs = [
        {'text': 'Admin', 'url': url_for('admin.admin')}, 
        {'text': 'Kits', 'url': url_for('admin_kits.gestion_kits')}, 
        {'text': kit.nom}
    ]
    
    return render_template("admin_kit_modifier.html", 
                           kit=kit, 
                           breadcrumbs=breadcrumbs, 
                           objets_in_kit=objets_in_kit, 
                           objets_disponibles=objets_disponibles)

@admin_kits_bp.route("/kits/retirer_objet/<int:kit_objet_id>", methods=["POST"])
@admin_required
def retirer_objet_kit(kit_objet_id):
    etablissement_id = session['etablissement_id']
    assoc = db.session.get(KitObjet, kit_objet_id)
    if not assoc or assoc.etablissement_id != etablissement_id:
        flash("Objet introuvable.", "danger")
        return redirect(url_for('admin_kits.gestion_kits'))
    kit_id = assoc.kit_id
    try:
        db.session.delete(assoc)
        db.session.commit()
        flash("Objet retiré.", "success")
    except Exception:
        db.session.rollback()
        current_app.logger.error("Erreur retrait objet kit", exc_info=True)
        flash("Erreur technique.", "danger")
    return redirect(url_for('admin_kits.modifier_kit', kit_id=kit_id))

@admin_kits_bp.route("/kits/supprimer/<int:kit_id>", methods=["POST"])
@admin_required
def supprimer_kit(kit_id):
    etablissement_id = session['etablissement_id']
    kit = db.session.get(Kit, kit_id)
    if kit and kit.etablissement_id == etablissement_id:
        try:
            db.session.delete(kit)
            db.session.commit()
            flash("Kit supprimé.", "success")
        except Exception:
            db.session.rollback()
            current_app.logger.error("Erreur suppression kit", exc_info=True)
            flash("Erreur technique.", "danger")
    else:
        flash("Kit introuvable.", "danger")
    return redirect(url_for('admin_kits.gestion_kits'))

