from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from utils import login_required, admin_required
from services.security_service import SecurityService
from db import db, EquipementSecurite, MaintenancePlan, MaintenanceLog, Utilisateur # <--- Ajout Utilisateur

securite_bp = Blueprint('securite', __name__, url_prefix='/securite')
security_service = SecurityService()

@securite_bp.route('/')
@login_required
def index():
    if not session.get('etablissement_id'):
        return redirect(url_for('main.index'))
    equipements = security_service.get_all_equipements(session['etablissement_id'])
    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Sécurité & Maintenance', 'url': None}
    ]
    return render_template('securite/index.html', equipements=equipements, breadcrumbs=breadcrumbs)

@securite_bp.route('/equipement/<int:id>')
@login_required
def voir_equipement(id):
    equipement = db.session.get(EquipementSecurite, id)
    if not equipement or equipement.etablissement_id != session['etablissement_id']:
        return redirect(url_for('securite.index'))

    breadcrumbs = [
        {'text': 'Tableau de Bord', 'url': url_for('inventaire.index')},
        {'text': 'Sécurité', 'url': url_for('securite.index')},
        {'text': equipement.nom, 'url': None}
    ]
    return render_template('securite/details.html', equipement=equipement, breadcrumbs=breadcrumbs, now=datetime.now())

# --- API ACTIONS ---

@securite_bp.route('/api/equipement', methods=['POST'])
@login_required
def ajouter_equipement():
    try:
        data = request.json
        if not data.get('nom') or not data.get('type_equipement'):
            return jsonify({'success': False, 'error': "Champs obligatoires manquants."}), 400
        
        if data.get('date_installation'):
            try:
                data['date_installation'] = datetime.strptime(data['date_installation'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': "Date invalide."}), 400

        security_service.create_equipement(session['etablissement_id'], data)
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Erreur ajout équipement: {e}")
        return jsonify({'success': False, 'error': "Erreur technique."}), 500

@securite_bp.route('/api/equipement/<int:id>/update', methods=['POST'])
@admin_required
def update_equipement(id):
    equipement = db.session.get(EquipementSecurite, id)
    if not equipement or equipement.etablissement_id != session['etablissement_id']:
        return jsonify({'success': False, 'error': "Accès refusé"}), 403
    
    try:
        data = request.json
        equipement.nom = data.get('nom', equipement.nom)
        equipement.numero_serie = data.get('numero_serie')
        equipement.etat_general = data.get('etat_general')
        
        if data.get('date_installation'):
             equipement.date_installation = datetime.strptime(data['date_installation'], '%Y-%m-%d').date()
             
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@securite_bp.route('/api/equipement/<int:id>/add_plan', methods=['POST'])
@admin_required
def add_plan(id):
    equipement = db.session.get(EquipementSecurite, id)
    if not equipement or equipement.etablissement_id != session['etablissement_id']:
        return jsonify({'success': False, 'error': "Accès refusé"}), 403
    
    try:
        data = request.json
        periodicite = int(data.get('periodicite_jours', 365))
        prochaine = datetime.now().date() + timedelta(days=periodicite)
        
        plan = MaintenancePlan(
            equipement_id=id,
            titre=data.get('titre'),
            periodicite_jours=periodicite,
            type_prestataire=data.get('type_prestataire'),
            date_prochaine_action=prochaine,
            alerte_active=True
        )
        db.session.add(plan)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@securite_bp.route('/api/equipement/<int:id>/add_log', methods=['POST'])
@admin_required
def add_log(id):
    equipement = db.session.get(EquipementSecurite, id)
    if not equipement or equipement.etablissement_id != session['etablissement_id']:
        return jsonify({'success': False, 'error': "Accès refusé"}), 403
    
    try:
        data = request.json
        date_inter = datetime.strptime(data.get('date_intervention'), '%Y-%m-%d').date()
        
        log = MaintenanceLog(
            equipement_id=id,
            date_intervention=date_inter,
            operateur=data.get('operateur'),
            resultat=data.get('resultat'),
            observations=data.get('observations')
        )
        db.session.add(log)
        
        if data.get('plan_id'):
            plan = db.session.get(MaintenancePlan, int(data['plan_id']))
            if plan:
                log.plan_id = plan.id
                plan.date_derniere_action = date_inter
                plan.date_prochaine_action = date_inter + timedelta(days=plan.periodicite_jours)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@securite_bp.route('/api/signalement', methods=['POST'])
@login_required
def signaler_dysfonctionnement():
    try:
        data = request.json
        equipement_id = data.get('equipement_id')
        description = data.get('description')
        
        if not equipement_id or not description:
            return jsonify({'success': False, 'error': "Description manquante."}), 400

        # --- CORRECTION NOM UTILISATEUR ---
        user = db.session.get(Utilisateur, session.get('user_id'))
        nom_operateur = user.nom_utilisateur if user else "Utilisateur Inconnu"

        log = MaintenanceLog(
            equipement_id=equipement_id,
            date_intervention=datetime.now().date(),
            operateur=nom_operateur, # Utilisation du vrai nom
            resultat='signalement', 
            observations=description
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Erreur signalement: {e}")
        return jsonify({'success': False, 'error': "Erreur technique."}), 500

@securite_bp.route('/api/traiter_signalement/<int:log_id>/<action>', methods=['POST'])
@admin_required
def traiter_signalement(log_id, action):
    try:
        log = db.session.get(MaintenanceLog, log_id)
        if not log: return jsonify({'success': False, 'error': "Introuvable"}), 404
        
        if action == 'valider':
            log.resultat = 'non_conforme' 
            log.observations += " [Validé par Admin]"
        elif action == 'refuser':
            db.session.delete(log)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500