from db import db, EquipementSecurite, MaintenancePlan, MaintenanceLog
from datetime import date, timedelta
from sqlalchemy import and_

class SecurityService:
    def get_dashboard_stats(self, etablissement_id):
        """
        Calcule les indicateurs pour le widget du Dashboard.
        """
        # 1. Total équipements
        total = EquipementSecurite.query.filter_by(
            etablissement_id=etablissement_id, 
            en_service=True
        ).count()
        
        if total == 0:
            return {'total_equipements': 0, 'alertes': 0, 'taux_conformite': 100}

        # 2. Alertes Maintenance (Dates dépassées)
        today = date.today()
        seuil_alerte = today + timedelta(days=30)
        
        alertes_maintenance = db.session.query(MaintenancePlan).join(EquipementSecurite).filter(
            EquipementSecurite.etablissement_id == etablissement_id,
            EquipementSecurite.en_service == True,
            MaintenancePlan.alerte_active == True,
            MaintenancePlan.date_prochaine_action <= seuil_alerte
        ).count()

        # 3. Alertes Signalements (Pannes signalées par utilisateurs)
        alertes_signalements = db.session.query(MaintenanceLog).join(EquipementSecurite).filter(
            EquipementSecurite.etablissement_id == etablissement_id,
            MaintenanceLog.resultat == 'signalement'
        ).count()

        # Total combiné
        total_alertes = alertes_maintenance + alertes_signalements

        # Calcul Taux
        taux = 100
        if total > 0 and total_alertes > 0:
            taux = int(((total - total_alertes) / total) * 100)
            if taux < 0: taux = 0

        return {
            'total_equipements': total,
            'alertes': total_alertes,
            'taux_conformite': taux
        }

    def get_all_equipements(self, etablissement_id):
        return EquipementSecurite.query.filter_by(etablissement_id=etablissement_id).all()

    def create_equipement(self, etablissement_id, data):
        nouvel_eq = EquipementSecurite(
            etablissement_id=etablissement_id,
            nom=data.get('nom'),
            type_equipement=data.get('type_equipement'),
            localisation=data.get('localisation'),
            numero_serie=data.get('numero_serie'),
            date_installation=data.get('date_installation')
        )
        db.session.add(nouvel_eq)
        db.session.commit()
        return nouvel_eq