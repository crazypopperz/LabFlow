import logging
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from db import db, Kit, KitObjet

logger = logging.getLogger(__name__)

class KitServiceError(Exception):
    """Exception levée lors d'une erreur métier dans le service Kit."""
    pass

class KitService:
    TYPE_KIT = 'kit'
    TYPE_OBJET = 'objet'
    MAX_ITEMS_BATCH = 100
    MAX_QTY_PER_ITEM = 100

    @staticmethod
    def decomposer_items(items_list: List[Dict[str, Any]], etablissement_id: int) -> Dict[int, int]:
        """
        Décompose une liste d'items en besoins unitaires.
        """
        if not items_list:
            return {}

        if len(items_list) > KitService.MAX_ITEMS_BATCH:
            raise KitServiceError(f"Trop d'items ({len(items_list)}). Max autorisé: {KitService.MAX_ITEMS_BATCH}")

        consommation: Dict[int, int] = {}
        kit_ids_to_fetch: Set[int] = set()
        valid_items: List[Tuple[str, int, int]] = []

        try:
            for idx, item in enumerate(items_list):
                qty = item.get('quantite') if 'quantite' in item else item.get('quantity')
                
                if qty is None:
                    logger.warning(f"Item index {idx} ignoré : quantité manquante. Payload: {item}")
                    continue

                try:
                    i_type = str(item.get('type'))
                    i_id = int(item.get('id'))
                    i_qty = int(qty)
                except (ValueError, TypeError):
                    continue

                if i_qty <= 0: continue
                
                if i_qty > KitService.MAX_QTY_PER_ITEM:
                    raise KitServiceError(f"Quantité excessive pour l'item {i_type} #{i_id} ({i_qty}). Max: {KitService.MAX_QTY_PER_ITEM}")

                valid_items.append((i_type, i_id, i_qty))
                
                if i_type == KitService.TYPE_KIT:
                    kit_ids_to_fetch.add(i_id)

            kits_map = {}
            if kit_ids_to_fetch:
                stmt = select(Kit).filter(
                    Kit.id.in_(kit_ids_to_fetch),
                    Kit.etablissement_id == etablissement_id
                )
                kits = db.session.execute(stmt).scalars().all()
                kits_map = {k.id: k for k in kits}

            for i_type, i_id, i_qty in valid_items:
                if i_type == KitService.TYPE_OBJET:
                    consommation[i_id] = consommation.get(i_id, 0) + i_qty
                
                elif i_type == KitService.TYPE_KIT:
                    kit = kits_map.get(i_id)
                    if not kit:
                        logger.warning(f"Kit introuvable ou interdit : ID {i_id} (Etab: {etablissement_id})")
                        raise KitServiceError(f"Le kit demandé (ID {i_id}) est introuvable ou indisponible.")
                    
                    for comp in kit.objets_assoc:
                        total = i_qty * comp.quantite
                        consommation[comp.objet_id] = consommation.get(comp.objet_id, 0) + total
            
            return consommation

        except SQLAlchemyError as e:
            logger.error(f"DB Error in decomposer_items: {e}")
            raise KitServiceError("Erreur base de données lors de la décomposition") from e