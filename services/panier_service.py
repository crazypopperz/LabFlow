# -*- coding: utf-8 -*-
import logging
import uuid
import re
import json
from datetime import datetime, timedelta, date, timezone
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
    MAX_QTY_PER_ITEM = 9999 # Valeur par défaut si KitService non dispo
    MAX_CRENEAUX = 10       # Limite de créneaux simultanés

    def __init__(self, etablissement_id: int):
        self.etablissement_id = etablissement_id
        self.stock_service = StockService(etablissement_id)
        # On récupère la constante de KitService si disponible
        if hasattr(KitService, 'MAX_QTY_PER_ITEM'):
            self.MAX_QTY_PER_ITEM = KitService.MAX_QTY_PER_ITEM

    def _get_active_panier(self, user_id: int, create_if_missing: bool = True, with_lock: bool = False) -> Optional[Panier]:
        """Récupère le panier actif avec gestion d'expiration."""
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
        elif panier:
            # Refresh TTL
            panier.date_expiration = now + timedelta(hours=self.PANIER_TTL_HOURS)
            
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
        """
        Récupère le contenu (Lecture Seule).
        CORRECTION : Le total compte les CRÉNEAUX UNIQUES.
        """
        panier = self._get_active_panier(user_id, create_if_missing=False)
        
        if not panier or not panier.items:
            return {'panier_id': None, 'items': [], 'total': 0}

        # Optimisation : Chargement en lot des noms
        objet_ids = [i.id_item for i in panier.items if i.type == 'objet']
        kit_ids = [i.id_item for i in panier.items if i.type == 'kit']
        
        objets_map = {}
        if objet_ids:
            objs = db.session.execute(select(Objet).filter(Objet.id.in_(objet_ids))).scalars().all()
            objets_map = {o.id: o for o in objs}
            
        kits_map = {}
        if kit_ids:
            kits = db.session.execute(select(Kit).filter(Kit.id.in_(kit_ids))).scalars().all()
            kits_map = {k.id: k for k in kits}

        items_data = []
        creneaux_uniques = set()

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
                if kit: nom = kit.nom

            recurrence = None
            if item.recurrence_data:
                try: recurrence = json.loads(item.recurrence_data)
                except: pass

            items_data.append({
                'id': item.id,
                'type': item.type,
                'id_item': item.id_item,
                'nom': nom,
                'image': image,
                'quantite': item.quantite,
                'date': item.date_reservation.isoformat(),
                'date_reservation': item.date_reservation.isoformat(),
                'heure_debut': item.heure_debut,
                'heure_fin': item.heure_fin,
                'recurrence': recurrence
            })
            
            # Signature unique du créneau
            creneaux_uniques.add((item.date_reservation, item.heure_debut, item.heure_fin))

        return {
            'id_panier': panier.id,
            'expiration': panier.date_expiration.isoformat(),
            'items': items_data,
            'total': len(creneaux_uniques) # C'est ici que ça change tout !
        }

    def ajouter_item(self, user_id: int, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ajoute un item au panier (Sécurisé)."""
        try:
            required = ['type', 'id', 'quantite', 'date', 'heure_debut', 'heure_fin']
            if not all(k in item_data for k in required):
                raise PanierServiceError("Données manquantes.")

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
            
            # Vérification limite items
            if len(panier.items) >= self.MAX_ITEMS_PANIER:
                raise PanierServiceError(f"Panier plein (Max {self.MAX_ITEMS_PANIER}).")

            # Vérification limite créneaux
            creneaux_actuels = set((i.date_reservation, i.heure_debut, i.heure_fin) for i in panier.items)
            nouveau_creneau = (start_dt.date(), item_data['heure_debut'], item_data['heure_fin'])
            if nouveau_creneau not in creneaux_actuels and len(creneaux_actuels) >= self.MAX_CRENEAUX:
                raise PanierServiceError(f"Limite de {self.MAX_CRENEAUX} créneaux atteinte.")

            # Vérification Stock
            check_item = [{'type': item_type, 'id': item_id, 'quantite': qte}]
            try:
                # On passe le panier actuel pour déduire ce qu'on a déjà pris
                # (Attention : il faut convertir les items du panier au format attendu par get_disponibilites)
                panier_items_fmt = []
                for pi in panier.items:
                    panier_items_fmt.append({
                        'type': pi.type, 'id': pi.id_item, 'quantite': pi.quantite,
                        'date_reservation': pi.date_reservation.isoformat(),
                        'heure_debut': pi.heure_debut, 'heure_fin': pi.heure_fin
                    })
                
                self.stock_service.get_disponibilites(start_dt, end_dt, panier_items=panier_items_fmt)
            except StockServiceError as e:
                raise PanierServiceError(f"Indisponible : {str(e)}")

            # Ajout ou Mise à jour
            existing_item = next((i for i in panier.items if 
                           i.id_item == item_id and 
                           i.type == item_type and
                           i.date_reservation == start_dt.date() and
                           i.heure_debut == item_data['heure_debut'] and
                           i.heure_fin == item_data['heure_fin']), None)
            
            if existing_item:
                new_total = existing_item.quantite + qte
                if new_total > self.MAX_QTY_PER_ITEM:
                    raise PanierServiceError("Quantité totale excessive.")
                existing_item.quantite = new_total
            else:
                recurrence = item_data.get('recurrence')
                new_item = PanierItem(
                    id_panier=panier.id,
                    type=item_type,
                    id_item=item_id,
                    quantite=qte,
                    date_reservation=start_dt.date(),
                    heure_debut=item_data['heure_debut'],
                    heure_fin=item_data['heure_fin'],
                    recurrence_data=json.dumps(recurrence) if recurrence else None
                )
                db.session.add(new_item)

            db.session.commit()
            return self.get_contenu(user_id)

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
            if not panier: raise PanierServiceError("Panier introuvable.")

            item = db.session.get(PanierItem, item_id)
            if not item or item.id_panier != panier.id:
                raise PanierServiceError("Item introuvable.")
            
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


    def _generer_dates_recurrentes(self, start_dt: datetime, end_dt: datetime, recurrence: dict) -> list:
        """Génère la liste des créneaux récurrents."""
        from datetime import timedelta
        dates = [(start_dt, end_dt)]  # Inclut le créneau de base
        
        type_rec = recurrence.get('type', 'hebdo')
        date_fin = recurrence.get('date_fin')
        nb_occ = recurrence.get('nb_occurrences')
        
        # Limite de sécurité
        MAX_OCCURRENCES = 52
        
        if date_fin:
            try:
                limite = datetime.strptime(date_fin, '%Y-%m-%d')
                limite = limite.replace(hour=23, minute=59)
            except ValueError:
                return dates
        elif nb_occ:
            limite = None
            max_iter = min(int(nb_occ) - 1, MAX_OCCURRENCES)
        else:
            return dates

        current = start_dt
        iterations = 0
        
        while True:
            # Calcul du prochain créneau
            if type_rec == 'hebdo':
                current = current + timedelta(weeks=1)
            elif type_rec == 'bi_hebdo':
                current = current + timedelta(weeks=2)
            elif type_rec == 'mensuel':
                month = current.month + 1
                year = current.year + (1 if month > 12 else 0)
                month = month if month <= 12 else 1
                try:
                    current = current.replace(year=year, month=month)
                except ValueError:
                    import calendar
                    last_day = calendar.monthrange(year, month)[1]
                    current = current.replace(year=year, month=month, day=last_day)
            elif type_rec == 'quotidien_ouvre':
                current = current + timedelta(days=1)
                # Sauter weekend
                while current.weekday() >= 5:
                    current = current + timedelta(days=1)
            else:
                break

            duration = end_dt - start_dt
            next_end = current + duration

            # Vérification limite
            if date_fin and current > limite:
                break
            if not date_fin:
                iterations += 1
                if iterations >= max_iter:
                    break

            dates.append((current, next_end))

            # Sécurité absolue
            if len(dates) >= MAX_OCCURRENCES:
                break

        return dates

    def valider_panier(self, user_id: int) -> Dict[str, Any]:
        """CHECKOUT ATOMIQUE & SÉCURISÉ."""
        try:
            panier = self._get_active_panier(user_id, create_if_missing=False, with_lock=True)
            
            if not panier or not panier.items:
                raise PanierServiceError("Panier vide ou expiré.")

            # Groupement par créneau
            creneaux = {}
            for item in panier.items:
                key = (item.date_reservation, item.heure_debut, item.heure_fin)
                if key not in creneaux: creneaux[key] = []
                creneaux[key].append(item)

            resultats = []
            audit_details = []

            for (d_res, h_deb, h_fin), items_list in creneaux.items():
                start_dt, end_dt = self._parse_and_validate_dates(d_res.isoformat(), h_deb, h_fin)

                # Vérification IDOR
                for it in items_list:
                    self._verify_item_ownership(it.type, it.id_item)

                # Préparation données pour StockService
                items_dict = [{'type': i.type, 'id': i.id_item, 'quantite': i.quantite} for i in items_list]

                # Récurrence : générer tous les créneaux
                recurrence = None
                if items_list[0].recurrence_data:
                    try: recurrence = json.loads(items_list[0].recurrence_data)
                    except: pass

                if recurrence:
                    creneaux_a_creer = self._generer_dates_recurrentes(start_dt, end_dt, recurrence)
                else:
                    creneaux_a_creer = [(start_dt, end_dt)]

                # Créer l'entrée de récurrence si nécessaire
                recurrence_row_id = None
                if recurrence:
                    from db import ReservationRecurrence
                    rec_row = ReservationRecurrence(
                        etablissement_id=self.etablissement_id,
                        utilisateur_id=user_id,
                        type_recurrence=recurrence.get('type', 'hebdo'),
                        date_debut=creneaux_a_creer[0][0].date(),
                        date_fin=datetime.strptime(recurrence['date_fin'], '%Y-%m-%d').date() if recurrence.get('date_fin') else None,
                        nb_occurrences=recurrence.get('nb_occurrences'),
                        heure_debut=h_deb,
                        heure_fin=h_fin
                    )
                    db.session.add(rec_row)
                    db.session.flush()  # Pour obtenir l'id
                    recurrence_row_id = rec_row.id

                for (s_dt, e_dt) in creneaux_a_creer:
                    # 1. Vérification Atomique
                    self.stock_service.verify_stock_atomic(items_dict, s_dt, e_dt, user_id)

                    # 2. Création Réservation
                    groupe_id = str(uuid.uuid4())

                    for item in items_list:
                        resa = Reservation(
                            utilisateur_id=user_id,
                            etablissement_id=self.etablissement_id,
                            quantite_reservee=item.quantite,
                            debut_reservation=s_dt,
                            fin_reservation=e_dt,
                            groupe_id=groupe_id,
                            statut='confirmée'
                        )
                        if recurrence_row_id:
                            resa.recurrence_id = recurrence_row_id
                        if item.type == 'kit': resa.kit_id = item.id_item
                        else: resa.objet_id = item.id_item

                        db.session.add(resa)
                        audit_details.append(f"{item.type}#{item.id_item} (x{item.quantite}) [{s_dt.strftime('%H:%M')}-{e_dt.strftime('%H:%M')}]")

                    resultats.append(groupe_id)

            # 3. Nettoyage
            db.session.execute(delete(PanierItem).where(PanierItem.id_panier == panier.id))
            
            # Audit
            audit_json = json.dumps(audit_details)
            audit = AuditLog(
                id_utilisateur=user_id,
                etablissement_id=self.etablissement_id,
                action="CHECKOUT",
                table_cible="reservations",
                id_enregistrement=resultats[0] if resultats else None,
                details=f"Items: {len(audit_details)}. Groupes: {len(resultats)}"
            )
            db.session.add(audit)

            db.session.commit()
            return {
                "success": True, 
                "groupes": resultats,
                "count": len(resultats) 
            }

        except (PanierServiceError, StockServiceError) as e:
            db.session.rollback()
            logger.warning(f"Checkout FAILED | User {user_id} | {e}")
            raise PanierServiceError(str(e))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Checkout CRITICAL DB ERROR | User {user_id} | {e}")
            raise PanierServiceError("Erreur technique validation.")