# ================================================================
@admin_bp.route("/packs", methods=["GET"])
@admin_required
def packs_onboarding():
    """Page de sélection des packs de matériel."""
    from static.data.packs_onboarding import PACKS_ONBOARDING
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Packs de matériel', 'url': None}
    ]
    return render_template("admin_packs.html", packs=PACKS_ONBOARDING, breadcrumbs=breadcrumbs)


@admin_bp.route("/packs/importer/<pack_id>", methods=["POST"])
@admin_required
def importer_pack(pack_id):
    """Importe un pack : crée armoires, catégories et objets."""
    from static.data.packs_onboarding import PACKS_ONBOARDING
    etablissement_id = session.get('etablissement_id')

    pack = next((p for p in PACKS_ONBOARDING if p["id"] == pack_id), None)
    if not pack:
        return jsonify({"success": False, "error": "Pack introuvable"}), 404

    try:
        stats = {"armoires": 0, "categories": 0, "objets": 0, "ignores": 0}

        # 1. Créer les armoires (si elles n'existent pas déjà)
        armoires_map = {}
        for arm_data in pack["armoires"]:
            existing = db.session.execute(
                db.select(Armoire).filter_by(
                    nom=arm_data["nom"],
                    etablissement_id=etablissement_id
                )
            ).scalar_one_or_none()
            if existing:
                armoires_map[arm_data["nom"]] = existing
            else:
                new_arm = Armoire(
                    nom=arm_data["nom"],
                    description=arm_data["description"],
                    etablissement_id=etablissement_id
                )
                db.session.add(new_arm)
                db.session.flush()
                armoires_map[arm_data["nom"]] = new_arm
                stats["armoires"] += 1

        # 2. Créer les catégories (si elles n'existent pas déjà)
        categories_map = {}
        for cat_nom in pack["categories"]:
            existing = db.session.execute(
                db.select(Categorie).filter_by(
                    nom=cat_nom,
                    etablissement_id=etablissement_id
                )
            ).scalar_one_or_none()
            if existing:
                categories_map[cat_nom] = existing
            else:
                new_cat = Categorie(
                    nom=cat_nom,
                    etablissement_id=etablissement_id
                )
                db.session.add(new_cat)
                db.session.flush()
                categories_map[cat_nom] = new_cat
                stats["categories"] += 1

        # 3. Créer les objets (si ils n'existent pas déjà)
        for obj_data in pack["objets"]:
            existing = db.session.execute(
                db.select(Objet).filter_by(
                    nom=obj_data["nom"],
                    etablissement_id=etablissement_id
                )
            ).scalar_one_or_none()
            if existing:
                stats["ignores"] += 1
                continue

            armoire = armoires_map.get(obj_data["armoire"])
            categorie = categories_map.get(obj_data["categorie"])

            new_obj = Objet(
                nom=obj_data["nom"],
                type_objet=obj_data["type_objet"],
                etablissement_id=etablissement_id,
                armoire_id=armoire.id if armoire else None,
                categorie_id=categorie.id if categorie else None,
                quantite_physique=obj_data["quantite_physique"],
                seuil=obj_data["seuil"],
                unite=obj_data.get("unite", "unité"),
                is_cmr=obj_data.get("is_cmr", False),
                image_url=obj_data.get("image_url"),
                fds_url=obj_data.get("fds_url"),
                en_commande=False,
                traite=False,
            )

            # Champs spécifiques aux produits chimiques
            if obj_data["type_objet"] == "produit":
                new_obj.capacite_initiale = obj_data.get("capacite_initiale")
                new_obj.niveau_actuel = obj_data.get("niveau_actuel")
                new_obj.seuil_pourcentage = obj_data.get("seuil_pourcentage", 50)

            db.session.add(new_obj)
            stats["objets"] += 1

        db.session.commit()
        log_action('import_pack', f"Pack '{pack['nom']}' importé : {stats}")
        cache.delete(f"armoires_{etablissement_id}")
        cache.delete(f"categories_{etablissement_id}")
        return jsonify({
            "success": True,
            "message": f"Pack importé avec succès ! {stats['armoires']} armoires, {stats['categories']} catégories et {stats['objets']} objets créés. {stats['ignores']} éléments ignorés (déjà existants).",
            "stats": stats
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur import pack: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erreur technique lors de l'import"}), 500

@admin_bp.route("/personnalisation", methods=["GET"])
@admin_required
def personnalisation_page():
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Personnalisation', 'url': None}
    ]
    params = get_etablissement_params(session.get('etablissement_id'))
    return render_template("admin_personnalisation.html", breadcrumbs=breadcrumbs, params=params)


@admin_bp.route("/theme", methods=["POST"])
@admin_required
def sauvegarder_theme():
    etablissement_id = session.get('etablissement_id')
    try:
        # Couleur principale
        couleur = request.form.get('couleur_principale', '').strip()
        if couleur and couleur.startswith('#') and len(couleur) in [4, 7]:
            for cle, valeur in [
                ('couleur_principale', couleur),
                ('couleur_secondaire', couleur)
            ]:
                param = db.session.execute(
                    db.select(Parametre).filter_by(
                        etablissement_id=etablissement_id, cle=cle
                    )
                ).scalar_one_or_none()
                if param:
                    param.valeur = valeur
                else:
                    db.session.add(Parametre(
                        etablissement_id=etablissement_id,
                        cle=cle, valeur=valeur
                    ))

        # Upload logo
        logo_file = request.files.get('logo_file')
        if logo_file and logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ['png', 'jpg', 'jpeg', 'svg', 'webp']:
                filename = f"logo_{etablissement_id}.{ext}"
                upload_path = os.path.join(
                    current_app.root_path, 'static', 'uploads', filename
                )
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                logo_file.save(upload_path)
                logo_url = f"uploads/{filename}"

                param = db.session.execute(
                    db.select(Parametre).filter_by(
                        etablissement_id=etablissement_id, cle='logo_url'
                    )
                ).scalar_one_or_none()
                if param:
                    param.valeur = logo_url
                else:
                    db.session.add(Parametre(
                        etablissement_id=etablissement_id,
                        cle='logo_url', valeur=logo_url
                    ))

        db.session.commit()
        # Invalider le cache theme
        from extensions import cache
        from utils import get_etablissement_params
        cache.delete_memoized(get_etablissement_params, etablissement_id)
        flash("Thème mis à jour avec succès.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur sauvegarde thème: {e}")
        flash("Erreur lors de la sauvegarde.", "error")

    return redirect(url_for('admin.personnalisation_page'))

@admin_bp.route("/supprimer_logo", methods=["GET", "POST"])
@admin_required
def supprimer_logo():
    etablissement_id = session.get('etablissement_id')
    try:
        param = db.session.execute(
            db.select(Parametre).filter_by(
                etablissement_id=etablissement_id, cle='logo_url'
            )
        ).scalar_one_or_none()
        if param:
            # Supprimer le fichier
            logo_path = os.path.join(current_app.root_path, 'static', param.valeur)
            if os.path.exists(logo_path):
                os.remove(logo_path)
            db.session.delete(param)
            db.session.commit()
            # Invalider cache
            from extensions import cache
            from utils import get_etablissement_params
            cache.delete_memoized(get_etablissement_params, etablissement_id)
            flash("Logo supprimé avec succès.", "success")
        else:
            flash("Aucun logo à supprimer.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression logo: {e}")
        flash("Erreur lors de la suppression.", "error")
    return redirect(url_for('admin.admin'))

# ================================================================
# EXPORT INVENTAIRE
# ================================================================
@admin_bp.route("/export-inventaire", methods=["GET"])
@admin_required
def export_inventaire_page():
    from db import Armoire, Categorie
    etablissement_id = session.get('etablissement_id')
    armoires = db.session.execute(
        db.select(Armoire).filter_by(etablissement_id=etablissement_id).order_by(Armoire.nom)
    ).scalars().all()
    categories = db.session.execute(
        db.select(Categorie).filter_by(etablissement_id=etablissement_id).order_by(Categorie.nom)
    ).scalars().all()
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Export inventaire', 'url': None}
    ]
    return render_template("admin_export_inventaire.html",
                           breadcrumbs=breadcrumbs,
                           all_armoires=armoires,
                           all_categories=categories)


# ================================================================
# RESET ÉTABLISSEMENT
# ================================================================
@admin_bp.route("/reset", methods=["GET"])
@admin_required
def reset_etablissement_page():
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Administration', 'url': url_for('admin.admin')},
        {'text': 'Reset établissement', 'url': None}
    ]
    etablissement = db.session.execute(
        db.select(Etablissement).filter_by(id=session.get('etablissement_id'))
    ).scalar_one_or_none()
    return render_template("admin_reset.html", breadcrumbs=breadcrumbs, etablissement=etablissement)


@admin_bp.route("/reset", methods=["POST"])
@admin_required
def reset_etablissement():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'JSON requis'}), 415
    etablissement_id = session.get('etablissement_id')
    data = request.get_json()
    confirmation = data.get('confirmation', '')
    elements = data.get('elements', [])

    # Vérification confirmation
    etablissement = db.session.execute(
        db.select(Etablissement).filter_by(id=etablissement_id)
    ).scalar_one_or_none()
    if not etablissement or confirmation != etablissement.nom:
        return jsonify({'success': False, 'error': 'Confirmation incorrecte'}), 400

    try:
        from db import KitObjet, ReservationRecurrence, Salle
        stats = {}

        if 'reservations' in elements:
            count = db.session.execute(
                db.select(db.func.count(Reservation.id))
                .where(Reservation.etablissement_id == etablissement_id)
            ).scalar()
            db.session.execute(
                db.delete(Reservation).where(Reservation.etablissement_id == etablissement_id)
            )
            db.session.execute(
                db.delete(ReservationRecurrence).where(ReservationRecurrence.etablissement_id == etablissement_id)
            )
            stats['reservations'] = count

        if 'kits' in elements:
            kits = db.session.execute(
                db.select(Kit).filter_by(etablissement_id=etablissement_id)
            ).scalars().all()
            for kit in kits:
                db.session.execute(db.delete(KitObjet).where(KitObjet.kit_id == kit.id))
                db.session.delete(kit)
            stats['kits'] = len(kits)

        if 'inventaire' in elements:
            objets = db.session.execute(
                db.select(Objet).filter_by(etablissement_id=etablissement_id)
            ).scalars().all()
            for obj in objets:
                db.session.execute(db.delete(KitObjet).where(KitObjet.objet_id == obj.id))
                db.session.execute(db.delete(Reservation).where(Reservation.objet_id == obj.id))
                db.session.delete(obj)
            stats['inventaire'] = len(objets)

        if 'armoires' in elements:
            count = db.session.execute(
                db.select(db.func.count(Armoire.id))
                .where(Armoire.etablissement_id == etablissement_id)
            ).scalar()
            db.session.execute(
                db.delete(Armoire).where(Armoire.etablissement_id == etablissement_id)
            )
            stats['armoires'] = count

        if 'categories' in elements:
            count = db.session.execute(
                db.select(db.func.count(Categorie.id))
                .where(Categorie.etablissement_id == etablissement_id)
            ).scalar()
            db.session.execute(
                db.delete(Categorie).where(Categorie.etablissement_id == etablissement_id)
            )
            stats['categories'] = count

        if 'salles' in elements:
            count = db.session.execute(
                db.select(db.func.count(Salle.id))
                .where(Salle.etablissement_id == etablissement_id)
            ).scalar()
            db.session.execute(
                db.delete(Salle).where(Salle.etablissement_id == etablissement_id)
            )
            stats['salles'] = count

        if 'fournisseurs' in elements:
            count = db.session.execute(
                db.select(db.func.count(Fournisseur.id))
                .where(Fournisseur.etablissement_id == etablissement_id)
            ).scalar()
            db.session.execute(
                db.delete(Fournisseur).where(Fournisseur.etablissement_id == etablissement_id)
            )
            stats['fournisseurs'] = count

        if 'budget' in elements:
            budgets = db.session.execute(
                db.select(Budget).filter_by(etablissement_id=etablissement_id)
            ).scalars().all()
            for budget in budgets:
                db.session.execute(db.delete(Depense).where(Depense.budget_id == budget.id))
                db.session.delete(budget)
            stats['budget'] = len(budgets)

        db.session.commit()
        log_action('reset_etablissement', f"Reset: {list(elements)}")
        return jsonify({'success': True, 'stats': stats})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur reset: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Erreur technique'}), 500
