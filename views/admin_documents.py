# ============================================================
# FICHIER : views/admin_documents.py
# Documents réglementaires, archives, licence, planning
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os

from markupsafe import Markup
from extensions import limiter, cache
from db import db, DocumentReglementaire, InventaireArchive, Parametre, Objet, Armoire, Categorie
from utils import admin_required, log_action, calculate_license_key, get_etablissement_params
from services.document_service import DocumentService, DocumentServiceError
from collections import defaultdict
from functools import wraps

admin_documents_bp = Blueprint('admin_documents', __name__, url_prefix='/admin')

@admin_documents_bp.route("/documents")
@admin_required
def gestion_documents():
    etablissement_id = session['etablissement_id']
    # Récupération des documents triés par date
    docs = db.session.execute(db.select(DocumentReglementaire).filter_by(etablissement_id=etablissement_id).order_by(DocumentReglementaire.date_upload.desc())).scalars().all()
    # Récupération des archives d'inventaire
    archives = db.session.execute(db.select(InventaireArchive).filter_by(etablissement_id=etablissement_id).order_by(InventaireArchive.date_archive.desc())).scalars().all()
    
    breadcrumbs=[{'text': 'Tableau de Bord', 'url': url_for('inventaire.index')}, {'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Documents et Conformité', 'url': None}]
    return render_template("admin_documents.html", docs=docs, archives=archives, breadcrumbs=breadcrumbs)

@admin_documents_bp.route("/documents/upload", methods=['POST'])
@admin_required
def upload_document():
    etablissement_id = session['etablissement_id']
    if 'fichier' not in request.files: return redirect(url_for('admin_documents.gestion_documents'))
    
    f = request.files['fichier']
    nom = request.form.get('nom')
    type_doc = request.form.get('type_doc')
    
    EXTENSIONS_AUTORISEES_DOCS = {'pdf', 'png', 'jpg', 'jpeg'}

    if f and nom:
        # Validation de l'extension
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in EXTENSIONS_AUTORISEES_DOCS:
            flash(f"Format non autorisé. Formats acceptés : {', '.join(EXTENSIONS_AUTORISEES_DOCS)}", "error")
            return redirect(url_for('admin_documents.gestion_documents'))
        
        # Sécurisation du nom de fichier
        filename = secure_filename(f"{etablissement_id}_{int(datetime.now().timestamp())}_{f.filename}")
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'docs')
        os.makedirs(upload_path, exist_ok=True)
        f.save(os.path.join(upload_path, filename))
        
        doc = DocumentReglementaire(
            etablissement_id=etablissement_id, 
            nom=nom, 
            type_doc=type_doc, 
            fichier_url=f"uploads/docs/{filename}"
        )
        db.session.add(doc)
        db.session.commit()
        flash("Document ajouté avec succès.", "success")
        
    return redirect(url_for('admin_documents.gestion_documents'))


@admin_documents_bp.route("/documents/generer_inventaire")
@admin_required
def generer_inventaire_annuel():
    etablissement_id = session['etablissement_id']
    nom_etablissement = session.get('nom_etablissement', 'Mon Etablissement')
    
    try:
        # 1. Récupération optimisée (Eager Loading)
        stmt = (
            db.select(Objet)
            .options(
                joinedload(Objet.categorie), 
                joinedload(Objet.armoire)
            )
            .filter_by(etablissement_id=etablissement_id)
            .order_by(Objet.nom)
        )
        objets = db.session.execute(stmt).scalars().all()
        
        # 2. Appel du Service
        # On injecte le chemin racine des uploads (static/uploads)
        upload_root = os.path.join(current_app.root_path, 'static', 'uploads')
        doc_service = DocumentService(upload_root)
        
        result = doc_service.generate_inventory_pdf(
            etablissement_name=nom_etablissement,
            etablissement_id=etablissement_id,
            objets=objets
        )
        
        # 3. Enregistrement en Base (Transaction)
        archive = InventaireArchive(
            etablissement_id=etablissement_id,
            titre=result['titre'],
            fichier_url=result['relative_path'],
            nb_objets=result['nb_objets']
        )
        db.session.add(archive)
        db.session.commit()
        
        # Optionnel : Rafraîchir l'objet pour être sûr d'avoir l'ID (si besoin plus tard)
        # db.session.refresh(archive) 
        
        # 4. Feedback avec Lien
        lien = url_for('static', filename=result['relative_path'])
        msg = Markup(f"Inventaire généré avec succès. <a href='{lien}' target='_blank' class='alert-link'>Voir le PDF</a>")
        flash(msg, "success")

    except DocumentServiceError as e:
        # Erreur métier (Liste vide, trop d'objets...)
        flash(str(e), "warning")
        
    except FileSystemError as e:
        # Erreur disque
        current_app.logger.critical(f"Erreur Disque: {e}")
        flash("Erreur système : Impossible d'écrire le fichier.", "error")

    except SQLAlchemyError as e:
        # Erreur base de données
        db.session.rollback()
        current_app.logger.error(f"Erreur DB lors de l'archivage: {e}")
        flash("Erreur lors de l'enregistrement en base de données.", "error")
        
    except Exception as e:
        # Filet de sécurité global
        db.session.rollback() # Sécurité supplémentaire
        current_app.logger.error(f"Erreur critique génération inventaire: {e}", exc_info=True)
        flash("Une erreur technique inattendue est survenue.", "error")
        
    return redirect(url_for('admin_documents.gestion_documents'))



# ============================================================
# LICENCE (Rate Limit Custom)
# ============================================================
class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(list)
        self.last_cleanup = datetime.now()

    def _cleanup_all(self):
        """Supprime les clés vides et obsolètes."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=15)
        
        # On itère sur une copie des clés pour pouvoir supprimer
        for key in list(self.attempts.keys()):
            # On ne garde que les tentatives récentes
            self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]
            # Si la liste est vide, on supprime la clé pour libérer la mémoire
            if not self.attempts[key]:
                del self.attempts[key]
        
        self.last_cleanup = now

    def is_allowed(self, key):
        now = datetime.now()
        
        # Nettoyage opportuniste global (toutes les heures)
        if (now - self.last_cleanup) > timedelta(hours=1):
            self._cleanup_all()
        
        # Nettoyage spécifique à la clé courante
        cutoff = now - timedelta(minutes=15)
        self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]
        
        if len(self.attempts[key]) >= 5: 
            return False
            
        self.attempts[key].append(now)
        return True
    
    def reset(self, key):
        if key in self.attempts: del self.attempts[key]

license_limiter = RateLimiter()

def rate_limit_license(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        eid = session.get('etablissement_id')
        if not eid: return redirect(url_for('main.index'))
        if not license_limiter.is_allowed(eid):
            flash("Trop de tentatives. Réessayez dans 15 min.", "error")
            return redirect(url_for('main.a_propos'))
        return f(*args, **kwargs)
    return wrapped

@admin_documents_bp.route("/activer_licence", methods=["POST"])
@admin_required
@rate_limit_license
def activer_licence():
    etablissement_id = session.get('etablissement_id')
    cle_fournie = request.form.get('licence_cle', '').strip().upper()
    
    if not cle_fournie or len(cle_fournie) < 10:
        flash("Clé invalide.", "error")
        return redirect(url_for('main.a_propos'))
    
    try:
        param_instance = db.session.execute(db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='instance_id')).scalar_one_or_none()
        if not param_instance:
            flash("Erreur critique : Instance ID manquant.", "error")
            return redirect(url_for('main.a_propos'))
        
        cle_attendue = calculate_license_key(param_instance.valeur.strip())
        if not cle_attendue:
            current_app.logger.error("GMLCL_PRO_KEY manquante ou instance_id vide")
            flash("Erreur de configuration serveur.", "error")
            return redirect(url_for("main.a_propos"))
        if not secrets.compare_digest(cle_fournie, cle_attendue):
            flash("Clé incorrecte.", "error")
            return redirect(url_for('main.a_propos'))
        
        # Activation
        param_statut = db.session.execute(db.select(Parametre).filter_by(etablissement_id=etablissement_id, cle='licence_statut')).scalar_one_or_none()
        if not param_statut: db.session.add(Parametre(etablissement_id=etablissement_id, cle='licence_statut', valeur='PRO'))
        else: param_statut.valeur = 'PRO'
        
        db.session.commit()
        try: cache.delete_memoized(get_etablissement_params, etablissement_id)
        except: pass
        license_limiter.reset(etablissement_id)
        flash("Licence PRO activée !", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur activation licence: {type(e).__name__}: {str(e)}", exc_info=True)
        flash("Erreur technique lors de l'activation.", "error")
    
    return redirect(url_for('main.a_propos'))


# ============================================================
@admin_documents_bp.route("/documents/supprimer_archive/<int:archive_id>", methods=['POST'])
@admin_required
def supprimer_archive(archive_id):
    etablissement_id = session['etablissement_id']
    archive = db.session.get(InventaireArchive, archive_id)
    
    # Vérification de sécurité (IDOR)
    if not archive or archive.etablissement_id != etablissement_id:
        flash("Archive introuvable ou accès interdit.", "error")
        return redirect(url_for('admin_documents.gestion_documents'))
        
    try:
        # 1. Suppression du fichier physique sur le disque
        # On reconstruit le chemin absolu : root/static/uploads/...
        full_path = os.path.join(current_app.root_path, 'static', archive.fichier_url)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            
        # 2. Suppression de l'entrée en base de données
        db.session.delete(archive)
        db.session.commit()
        
        flash("Archive supprimée avec succès.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur suppression archive: {e}", exc_info=True)
        flash("Erreur technique lors de la suppression.", "error")
        
    return redirect(url_for('admin_documents.gestion_documents'))

#================================================================
# ROUTE CONFIGURATION PLANNING RESERVATION PAR ADMIN
#================================================================
@admin_documents_bp.route("/config_planning", methods=['POST'])
@admin_required
def config_planning():
    etablissement_id = session['etablissement_id']
    
    # 1. Récupération des données du formulaire
    heure_debut = request.form.get('heure_debut', '08:00')
    heure_fin = request.form.get('heure_fin', '18:00')
    current_app.logger.info(f"[CONFIG_PLANNING] Etab ID {etablissement_id} a soumis : Début={heure_debut}, Fin={heure_fin}")

    try:
        # 2. Validation métier
        if heure_debut >= heure_fin:
            flash("L'heure de début doit être strictement antérieure à l'heure de fin.", "error")
            return redirect(url_for('admin.admin'))

        # 3. Fonction de sauvegarde "Upsert" (Update or Insert) pour chaque paramètre
        def upsert_param(cle, valeur):
            # On cherche si le paramètre existe déjà pour cet établissement
            param = db.session.execute(
                select(Parametre).filter_by(etablissement_id=etablissement_id, cle=cle)
            ).scalar_one_or_none()
            
            if param:
                # Si oui, on met à jour sa valeur
                param.valeur = str(valeur)
                current_app.logger.info(f"Paramètre '{cle}' mis à jour à '{valeur}' pour Etab {etablissement_id}.")
            else:
                # Sinon, on le crée
                db.session.add(Parametre(etablissement_id=etablissement_id, cle=cle, valeur=str(valeur)))
                current_app.logger.info(f"Paramètre '{cle}' créé avec la valeur '{valeur}' pour Etab {etablissement_id}.")

        # 4. Application des sauvegardes
        upsert_param('planning_debut', heure_debut)
        upsert_param('planning_fin', heure_fin)
        
        db.session.commit()
        
        # 5. POINT CRUCIAL : Invalidation explicite du cache
        # C'est cette ligne qui force la fonction `get_etablissement_params` à relire
        # la base de données la prochaine fois qu'elle sera appelée.
        try:
            cache.delete_memoized(get_etablissement_params, etablissement_id)
            current_app.logger.info(f"✅ Cache pour 'get_etablissement_params' (Etab {etablissement_id}) invalidé avec succès.")
        except Exception as e:
            current_app.logger.warning(f"⚠️ Erreur non bloquante lors de l'invalidation du cache : {e}")
        
        flash("La configuration du planning de réservation a été mise à jour.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Erreur critique lors de la configuration du planning : {e}", exc_info=True)
        flash("Une erreur technique est survenue lors de la sauvegarde.", "error")
        
    return redirect(url_for('admin.admin'))
