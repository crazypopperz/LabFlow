import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from db import db, Objet, Kit, Reservation
from services.kit_service import KitService, KitServiceError

logger = logging.getLogger(__name__)

class StockServiceError(Exception):
    """Exception métier pour le stock."""
    pass

class StockService:
    MAX_KIT_QUANTITY = 9999
    
    # Règles de validation temporelle
    MAX_RESERVATION_DURATION_HOURS = 12
    MAX_FUTURE_DAYS = 365
    PAST_BUFFER_MINUTES = 15  # Tolérance pour le décalage d'horloge

    def __init__(self, etablissement_id: int):
        self.etablissement_id = etablissement_id

    def _normalize_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise les items pour KitService (quantite vs quantity)."""
        clean_items = []
        for item in items:
            qty = item.get('quantite') if 'quantite' in item else item.get('quantity')
            if qty is not None and 'type' in item and 'id' in item:
                clean_items.append({
                    'type': item['type'],
                    'id': item['id'],
                    'quantite': qty
                })
        return clean_items

    def _validate_dates(self, start_dt: datetime, end_dt: datetime):
        """Validation centralisée des règles de dates."""
        now = datetime.now()
        
        # 1. Cohérence de base
        if start_dt >= end_dt:
            raise StockServiceError("La date de début doit être antérieure à la date de fin.")
        
        # 2. Pas dans le passé (avec tolérance)
        if start_dt < now - timedelta(minutes=self.PAST_BUFFER_MINUTES):
            raise StockServiceError("Impossible de réserver dans le passé.")
            
        # 3. Pas trop loin dans le futur
        if start_dt > now + timedelta(days=self.MAX_FUTURE_DAYS):
            raise StockServiceError(f"Les réservations sont limitées à {self.MAX_FUTURE_DAYS} jours à l'avance.")
            
        # 4. Durée maximale
        duration = (end_dt - start_dt).total_seconds() / 3600
        if duration > self.MAX_RESERVATION_DURATION_HOURS:
            raise StockServiceError(f"La durée maximale d'une réservation est de {self.MAX_RESERVATION_DURATION_HOURS} heures.")

    def _get_reservations_actives(self, start_dt: datetime, end_dt: datetime) -> List[Reservation]:
        """Récupère les réservations actives (chevauchement de dates)."""
        try:
            # ⚠️ IMPORTANT : Vérifiez que Reservation.statut existe dans db.py
            stmt = (
                select(Reservation)
                .options(
                    joinedload(Reservation.kit).joinedload(Kit.objets_assoc),
                    joinedload(Reservation.objet)
                )
                .filter(
                    Reservation.etablissement_id == self.etablissement_id,
                    Reservation.statut == 'confirmée', 
                    Reservation.debut_reservation < end_dt,
                    Reservation.fin_reservation > start_dt
                )
            )
            return db.session.execute(stmt).unique().scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"DB Error fetching reservations: {e}")
            raise StockServiceError("Impossible de lire les réservations.") from e

    def verify_stock_atomic(
        self, 
        items: List[Dict[str, Any]], 
        start_dt: datetime, 
        end_dt: datetime, 
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Vérifie le stock ET verrouille les lignes (SELECT FOR UPDATE NOWAIT).
        """
        # 1. Validations
        self._validate_dates(start_dt, end_dt)
        
        items_propres = self._normalize_items(items)
        if not items_propres:
            return {'objets_map': {}, 'besoins': {}}

        try:
            # 2. Calcul des besoins
            besoins_demandes = KitService.decomposer_items(items_propres, self.etablissement_id)
            if not besoins_demandes:
                return {'objets_map': {}, 'besoins': {}}

            # 3. Lecture de l'existant
            reservations_existantes = self._get_reservations_actives(start_dt, end_dt)
            
            items_reserves_existants = []
            for r in reservations_existantes:
                if r.kit_id:
                    items_reserves_existants.append({'type': 'kit', 'id': r.kit_id, 'quantite': r.quantite_reservee})
                elif r.objet_id:
                    items_reserves_existants.append({'type': 'objet', 'id': r.objet_id, 'quantite': r.quantite_reservee})

            conso_existante = KitService.decomposer_items(items_reserves_existants, self.etablissement_id)

            # 4. Verrouillage Pessimiste (Trié + NoWait)
            objet_ids_to_lock = sorted(list(besoins_demandes.keys()))
            
            stmt = (
                select(Objet)
                .filter(
                    Objet.id.in_(objet_ids_to_lock),
                    Objet.etablissement_id == self.etablissement_id
                )
                .with_for_update(nowait=True)
            )
            
            objets_db = db.session.execute(stmt).scalars().all()
            objets_map = {obj.id: obj for obj in objets_db}

            # 5. Sécurité IDOR
            if len(objets_db) != len(objet_ids_to_lock):
                missing = set(objet_ids_to_lock) - set(objets_map.keys())
                logger.warning(f"SECURITY: IDOR Attempt? User {user_id} Etab {self.etablissement_id} requested missing objects: {missing}")
                raise StockServiceError("Certains objets demandés sont introuvables ou non autorisés.")

            # 6. Vérification Quantités
            for obj_id, qte_demandee in besoins_demandes.items():
                obj = objets_map[obj_id]
                stock_total = obj.quantite_physique
                stock_pris = conso_existante.get(obj_id, 0)
                disponible = stock_total - stock_pris

                if disponible < qte_demandee:
                    logger.info(f"STOCK REFUSÉ | User: {user_id} | Objet: {obj.id} | Demandé: {qte_demandee} | Dispo: {disponible}")
                    raise StockServiceError(f"Stock insuffisant pour '{obj.nom}'. Disponible: {disponible}")

            return {
                'objets_map': objets_map,
                'besoins': besoins_demandes
            }

        except OperationalError as e:
            logger.warning(f"Concurrency conflict for User {user_id}: {e}")
            raise StockServiceError("Le stock est actuellement modifié par une autre personne. Veuillez réessayer dans un instant.")
            
        except KitServiceError as e:
            logger.error(f"KitService Error for User {user_id}: {e}")
            raise StockServiceError(str(e))
            
        except SQLAlchemyError as e:
            logger.error(f"DB Critical Error for User {user_id}: {e}")
            raise StockServiceError("Erreur technique lors de la vérification du stock.")

    def get_disponibilites(self, start_dt: datetime, end_dt: datetime, panier_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Calcule les stocks disponibles (Lecture seule).
        """
        # Validation des dates identique à la réservation
        self._validate_dates(start_dt, end_dt)

        try:
            reservations = self._get_reservations_actives(start_dt, end_dt)
            
            items_reserves = []
            for r in reservations:
                if r.kit_id:
                    items_reserves.append({'type': 'kit', 'id': r.kit_id, 'quantite': r.quantite_reservee})
                elif r.objet_id:
                    items_reserves.append({'type': 'objet', 'id': r.objet_id, 'quantite': r.quantite_reservee})

            if panier_items:
                panier_propre = self._normalize_items(panier_items)
                items_reserves.extend(panier_propre)

            conso_totale = KitService.decomposer_items(items_reserves, self.etablissement_id)

            all_objets = db.session.execute(
                select(Objet)
                .options(joinedload(Objet.armoire))
                .filter_by(etablissement_id=self.etablissement_id)
            ).scalars().all()

            objets_data = []
            stock_map = {}

            for obj in all_objets:
                conso = conso_totale.get(obj.id, 0)
                dispo = max(0, obj.quantite_physique - conso)
                stock_map[obj.id] = dispo
                
                objets_data.append({
                    'id': obj.id,
                    'nom': obj.nom,
                    'stock': obj.quantite_physique,
                    'disponible': dispo,
                    'image': obj.image_url,
                    'armoire': obj.armoire.nom if obj.armoire else "Non rangé"
                })

            all_kits = db.session.execute(
                select(Kit)
                .options(joinedload(Kit.objets_assoc))
                .filter_by(etablissement_id=self.etablissement_id)
            ).unique().scalars().all()

            kits_data = []
            for kit in all_kits:
                max_possible = self.MAX_KIT_QUANTITY
                if not kit.objets_assoc:
                    max_possible = 0
                else:
                    for comp in kit.objets_assoc:
                        if comp.quantite > 0:
                            stock_obj = stock_map.get(comp.objet_id, 0)
                            possible = stock_obj // comp.quantite
                            if possible < max_possible:
                                max_possible = possible
                
                kits_data.append({
                    'id': kit.id,
                    'nom': kit.nom,
                    'description': kit.description,
                    'disponible': int(max_possible)
                })

            return {'objets': objets_data, 'kits': kits_data}

        except KitServiceError as e:
            # Erreur métier connue
            raise StockServiceError(str(e))
            
        except SQLAlchemyError as e:
            # Erreur DB
            logger.error(f"DB Error in get_disponibilites: {e}")
            raise StockServiceError("Erreur d'accès aux données de stock.")
            
        except Exception as e:
            # Erreur inconnue (Code, Logique, etc.)
            logger.exception("Erreur inattendue dans get_disponibilites")
            raise StockServiceError("Une erreur interne est survenue.") from e