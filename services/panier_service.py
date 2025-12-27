# -*- coding: utf-8 -*-
import logging
import uuid
import re
import json
# AJOUT DE 'timezone' DANS LES IMPORTS
from datetime import datetime, timedelta, date, time, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from db import db, Panier, PanierItem, Reservation, AuditLog, Objet, Kit
from services.stock_service import StockService, StockServiceError
from services.kit_service import KitService

logger = logging.getLogger(__name__)

class PanierServiceError(Exception):
    """Exception métier pour la gestion du panier."""
    pass

class PanierService:
    PANIER_TTL_HOURS = 24
    MAX_ITEMS_PANIER = 50
    MAX_QTY_PER_ITEM = KitService.MAX_QTY_PER_ITEM

    def __init__(self, etablissement_id: int):
        self.etablissement_id = etablissement_id
        self.stock_service = StockService(etablissement_id)

    def _get_active_panier(self, user_id: int, create_if_missing: bool = True, with_lock: bool = False) -> Optional[Panier]:
        """
        Récupère le panier actif.
        """
        # CORRECTION CRITIQUE : On utilise une date "Aware" (UTC) pour matcher la DB
        now = datetime.now(timezone.utc)
        
        stmt = select(Panier).filter_by(
            id_utilisateur=user_id,
            etablissement_id=self.etablissement_id,
            statut='actif'
        )
        
        if with_lock:
            stmt = stmt.with_for_update()

        panier = db.session.execute(stmt).scalar_one_or_none()

        # Rotation si expiré
        if panier and panier.date_expiration < now:
            panier.statut = 'expiré'
            # On ne commit pas ici pour laisser la transaction appelante gérer
            panier = None

        if not panier and create_if_missing:
            panier = Panier(
                id=str(uuid.uuid4()),
                id_utilisateur=user_id,
                etablissement_id=self.etablissement_id,
                date_expiration=now + timedelta(hours=self.PANIER_TTL_HOURS),
                statut='actif'
            )
            db.session.add(panier)
            db.session.flush()
            
        return panier

    def _verify_item_ownership(self, item_type: str, item_id: int):
        """SÉCURITÉ IDOR : Vérifie l'appartenance à l'établissement."""
        exists = False
        if item_type == 'objet':
            exists = db.session.execute(
                select(Objet.id).filter_by(id=item_id, etablissement_id=self.etablissement_id)
            ).scalar()
        elif item_type == 'kit':
            exists = db.session.execute(
                select(Kit.id).filter_by(id=item_id, etablissement_id=self.etablissement_id)
            ).scalar()
        
        if not exists:
            logger.warning(f"SECURITY: IDOR Attempt. Etab {self.etablissement_id} tried accessing {item_type} {item_id}")
            raise PanierServiceError("Élément introuvable ou accès refusé.")

    def _parse_and_validate_dates(self, date_str: str, h_debut: str, h_fin: str) -> Tuple[datetime, datetime]:
        """Valide format et règles métier (Passé, Futur, Durée)."""
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            raise PanierServiceError("Format date invalide.")
        if not re.match(r'^\d{2}:\d{2}$', h_debut) or not re.match(r'^\d{2}:\d{2}$', h_fin):
            raise PanierServiceError("Format heure invalide.")

        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            t_start = datetime.strptime(h_debut, "%H:%M").time()
            t_end = datetime.strptime(h_fin, "%H:%M").time()
            
            start_dt = datetime.combine(d, t_start)
            end_dt = datetime.combine(d, t_end)
        except ValueError:
            raise PanierServiceError("Date/Heure incohérente.")

        if start_dt >= end_dt:
            raise PanierServiceError("Début doit être avant Fin.")

        # Règles métier StockService
        # Ici on utilise datetime.now() simple car StockService attend du Naive (par défaut)
        # ou gère lui-même la conversion. Pour être sûr, on reste en Naive pour la logique métier locale.
        now = datetime.now() 
        
        if start_dt < now - timedelta(minutes=StockService.PAST_BUFFER_MINUTES):
            raise PanierServiceError("Impossible de réserver dans le passé.")
        if start_dt > now + timedelta(days=StockService.MAX_FUTURE_DAYS):
            raise PanierServiceError(f"Limite de réservation : {StockService.MAX_FUTURE_DAYS} jours.")
        
        duration = (end_dt - start_dt).total_seconds() / 3600
        if duration > StockService.MAX_RESERVATION_DURATION_HOURS:
            raise PanierServiceError(f"Durée max dépassée ({StockService.MAX_RESERVATION_DURATION_HOURS}h).")

        return start_dt, end_dt

    def get_contenu(self, user_id: int) -> Dict[str, Any]:
        """Récupère le contenu (Lecture Seule)."""
        panier = self._get_active_panier(user_id, create_if_missing=False)
        
        if not panier or not panier.items:
            return {
                'panier_id': None,
                'expiration': None,
                'items': [],
                'total': 0
            }

        objet_ids = [i.id_item for i in panier.items if i.type == 'objet']
        kit_ids = [i.id_item for i in panier.items if i.type == 'kit']

        objets_map = {}
        kits_map = {}

        if objet_ids:
            objs = db.session.execute(select(Objet).filter(Objet.id.in_(objet_ids))).scalars().all()
            objets_map = {o.id: o for o in objs}
        
        if kit_ids:
            kits = db.session.execute(select(Kit).filter(Kit.id.in_(kit_ids))).scalars().all()
            kits_map = {k.id: k for k in kits}

        items_data = []
        total_items = 0

        for item in panier.items:
            nom = "Élément supprimé"
            image = None
            
            if item.type == 'objet':
                obj = objets_map.get(item.id_item)
                if obj:
                    nom = obj.nom
                    image = obj.image_url
            elif item.type == 'kit':
                kit = kits_map.get(item.id_item)
                if kit:
                    nom = kit.nom

            items_data.append({
                'id': item.id,
                'type': item.type,
                'id_item': item.id_item,
                'nom': nom,
                'image': image,
                'quantite': item.quantite,
                'date': item.date_reservation.isoformat(),
                'heure_debut': item.heure_debut,
                'heure_fin': item.heure_fin
            })
            total_items += item.quantite

        return {
            'panier_id': panier.id,
            'expiration': panier.date_expiration.isoformat(),
            'items': items_data,
            'total': total_items
        }

    def ajouter_item(self, user_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ajoute un item au panier (Sécurisé)."""
        try:
            required = ['type', 'id', 'quantite', 'date', 'heure_debut', 'heure_fin']
            if not all(k in item_data for k in required):
                raise PanierServiceError("Données manquantes.")

            if not isinstance(item_data['type'], str):
                raise PanierServiceError("Format type invalide.")

            try:
                qte = int(item_data['quantite'])
                item_id = int(item_data['id'])
                item_type = item_data['type']
            except (ValueError, TypeError):
                raise PanierServiceError("Types invalides.")

            if item_type not in ['objet', 'kit']:
                raise PanierServiceError("Type inconnu.")

            if qte <= 0 or qte > self.MAX_QTY_PER_ITEM:
                raise PanierServiceError(f"Quantité invalide (Max {self.MAX_QTY_PER_ITEM}).")

            start_dt, end_dt = self._parse_and_validate_dates(
                item_data['date'], item_data['heure_debut'], item_data['heure_fin']
            )

            self._verify_item_ownership(item_type, item_id)

            panier = self._get_active_panier(user_id, create_if_missing=True)
            
            if len(panier.items) >= self.MAX_ITEMS_PANIER:
                raise PanierServiceError(f"Panier plein (Max {self.MAX_ITEMS_PANIER}).")

            check_item = [{'type': item_type, 'id': item_id, 'quantite': qte}]
            try:
                self.stock_service.get_disponibilites(start_dt, end_dt, panier_items=check_item)
            except StockServiceError as e:
                raise PanierServiceError(f"Indisponible : {str(e)}")

            existing_item = None
            for it in panier.items:
                if (it.type == item_type and 
                    it.id_item == item_id and
                    it.date_reservation.isoformat() == item_data['date'] and
                    it.heure_debut == item_data['heure_debut'] and
                    it.heure_fin == item_data['heure_fin']):
                    existing_item = it
                    break
            
            if existing_item:
                new_total = existing_item.quantite + qte
                if new_total > self.MAX_QTY_PER_ITEM:
                    raise PanierServiceError("Quantité totale excessive.")
                existing_item.quantite = new_total
            else:
                new_item = PanierItem(
                    id_panier=panier.id,
                    type=item_type,
                    id_item=item_id,
                    quantite=qte,
                    date_reservation=start_dt.date(),
                    heure_debut=item_data['heure_debut'],
                    heure_fin=item_data['heure_fin']
                )
                db.session.add(new_item)

            # Refresh TTL (UTC)
            panier.date_expiration = datetime.now(timezone.utc) + timedelta(hours=self.PANIER_TTL_HOURS)
            db.session.flush()
            
            db.session.commit()
            return {"success": True, "message": "Ajouté"}

        except PanierServiceError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erreur interne ajouter_item User {user_id}")
            raise PanierServiceError("Erreur interne.")

    def retirer_item(self, user_id: int, item_id: int) -> Dict[str, Any]:
        """Retire un item (Sécurisé)."""
        try:
            panier = self._get_active_panier(user_id, create_if_missing=False)
            if not panier:
                raise PanierServiceError("Panier introuvable.")

            item = db.session.get(PanierItem, item_id)
            if not item:
                raise PanierServiceError("Item introuvable.")
            
            if item.id_panier != panier.id:
                logger.warning(f"SECURITY: IDOR Delete Attempt User {user_id} Item {item_id}")
                raise PanierServiceError("Action interdite.")

            db.session.delete(item)
            db.session.commit()
            return {"success": True}
        except SQLAlchemyError:
            db.session.rollback()
            raise PanierServiceError("Erreur suppression.")

    def vider_panier(self, user_id: int) -> Dict[str, Any]:
        """Vide le panier."""
        try:
            panier = self._get_active_panier(user_id, create_if_missing=False)
            if panier:
                db.session.execute(delete(PanierItem).where(PanierItem.id_panier == panier.id))
                db.session.commit()
            return {"success": True}
        except SQLAlchemyError:
            db.session.rollback()
            raise PanierServiceError("Erreur vidage panier.")

    def valider_panier(self, user_id: int) -> Dict[str, Any]:
        """CHECKOUT ATOMIQUE & SÉCURISÉ."""
        try:
            panier = self._get_active_panier(user_id, create_if_missing=False, with_lock=True)
            
            if not panier or not panier.items:
                raise PanierServiceError("Panier vide ou expiré.")

            creneaux: Dict[Tuple[date, str, str], List[Dict[str, Any]]] = {}
            for item in panier.items:
                key = (item.date_reservation, item.heure_debut, item.heure_fin)
                if key not in creneaux:
                    creneaux[key] = []
                creneaux[key].append({
                    'type': item.type,
                    'id': item.id_item,
                    'quantite': item.quantite
                })

            groupe_id = str(uuid.uuid4())
            reservations_created = []
            audit_details = []

            for (d_res, h_deb, h_fin), items_list in creneaux.items():
                start_dt, end_dt = self._parse_and_validate_dates(
                    d_res.isoformat(), h_deb, h_fin
                )

                for it in items_list:
                    self._verify_item_ownership(it['type'], it['id'])

                self.stock_service.verify_stock_atomic(
                    items=items_list,
                    start_dt=start_dt,
                    end_dt=end_dt,
                    user_id=user_id
                )

                for it in items_list:
                    resa = Reservation(
                        utilisateur_id=user_id,
                        etablissement_id=self.etablissement_id,
                        quantite_reservee=it['quantite'],
                        debut_reservation=start_dt,
                        fin_reservation=end_dt,
                        groupe_id=groupe_id,
                        statut='confirmée'
                    )
                    if it['type'] == 'kit':
                        resa.kit_id = it['id']
                    else:
                        resa.objet_id = it['id']
                    
                    db.session.add(resa)
                    reservations_created.append(resa)
                    audit_details.append(f"{it['type']}#{it['id']} (x{it['quantite']}) [{h_deb}-{h_fin}]")

            db.session.execute(delete(PanierItem).where(PanierItem.id_panier == panier.id))
            
            audit_json = json.dumps(audit_details)
            audit = AuditLog(
                id_utilisateur=user_id,
                etablissement_id=self.etablissement_id,
                action="CHECKOUT",
                table_cible="reservations",
                id_enregistrement=groupe_id,
                details=f"Items: {len(reservations_created)}. Détails: {audit_json}"
            )
            db.session.add(audit)

            db.session.commit()
            
            logger.info(f"Checkout SUCCESS | User {user_id} | Group {groupe_id}")
            return {
                "success": True, 
                "reservations_count": len(reservations_created),
                "groupe_id": groupe_id
            }

        except (PanierServiceError, StockServiceError) as e:
            db.session.rollback()
            logger.warning(f"Checkout FAILED | User {user_id} | {e}")
            raise PanierServiceError(str(e))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Checkout CRITICAL DB ERROR | User {user_id} | {e}")
            raise PanierServiceError("Erreur technique validation.")