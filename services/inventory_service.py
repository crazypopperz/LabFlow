# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError
from db import db, Objet, Categorie, Armoire

logger = logging.getLogger(__name__)

class InventoryServiceError(Exception):
    """Exception métier pour l'inventaire."""
    pass

# --- DTOs (Data Transfer Objects) ---
@dataclass
class InventoryContext:
    armoire_nom: Optional[str]
    categorie_nom: Optional[str]

@dataclass
class InventoryDTO:
    items: List[Dict[str, Any]] # Liste de dicts sérialisés (Performance & Sécurité)
    total_pages: int
    current_page: int
    context: InventoryContext

class InventoryService:
    def __init__(self, etablissement_id: int):
        self.etablissement_id = etablissement_id

    def search_objets(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche rapide pour l'autocomplétion."""
        if not query_text or len(query_text) < 2:
            return []
        
        safe_limit = min(limit, 50)
            
        try:
            stmt = (
                select(Objet)
                .filter(
                    Objet.etablissement_id == self.etablissement_id,
                    Objet.nom.ilike(f"%{query_text}%")
                )
                .limit(safe_limit)
            )
            results = db.session.execute(stmt).scalars().all()
            
            return [{
                'id': obj.id, 
                'nom': obj.nom, 
                'image': obj.image_url,
                'armoire': obj.armoire.nom if obj.armoire else None, 
                'quantite': obj.quantite_physique
            } for obj in results]
        except SQLAlchemyError as e:
            logger.error(f"Search error: {e}")
            raise InventoryServiceError("Erreur lors de la recherche.")

    def get_paginated_inventory(self, page: int, sort_by: str, direction: str, filters: dict) -> InventoryDTO:
        """
        Récupère l'inventaire filtré et paginé sous forme de DTO sérialisé.
        """
        ITEMS_PER_PAGE = 20
        try:
            page = max(1, min(int(page), 1000))
        except (ValueError, TypeError):
            page = 1

        try:
            # 1. Construction de la requête
            query = select(Objet).filter_by(etablissement_id=self.etablissement_id)
            query = query.outerjoin(Categorie).outerjoin(Armoire)

            # 2. Filtres
            if filters.get('q'):
                term = f"%{filters['q']}%"
                query = query.filter(or_(
                    Objet.nom.ilike(term), 
                    Categorie.nom.ilike(term), 
                    Armoire.nom.ilike(term)
                ))
            
            if filters.get('armoire_id'):
                query = query.filter(Objet.armoire_id == filters['armoire_id'])
            if filters.get('categorie_id'):
                query = query.filter(Objet.categorie_id == filters['categorie_id'])

            if filters.get('etat'):
                today = datetime.now().date()
                if filters['etat'] == 'perime':
                    query = query.filter(Objet.date_peremption < today)
                elif filters['etat'] == 'bientot':
                    query = query.filter(
                        Objet.date_peremption >= today, 
                        Objet.date_peremption <= today + timedelta(days=30)
                    )
                elif filters['etat'] == 'stock':
                    # CORRECTION : On inclut le seuil critique ET la marge de sécurité (+2)
                    # Cela permet d'afficher les items Oranges ET Rouges quand on filtre
                    query = query.filter(Objet.quantite_physique <= Objet.seuil + 2)

            # 3. Tri
            ALLOWED_SORT = {
                'nom': Objet.nom, 'quantite': Objet.quantite_physique,
                'seuil': Objet.seuil, 'date_peremption': Objet.date_peremption,
                'categorie': Categorie.nom, 'armoire': Armoire.nom
            }
            sort_expr = ALLOWED_SORT.get(sort_by, Objet.nom)
            query = query.order_by(sort_expr.desc() if direction == 'desc' else sort_expr.asc())

            # 4. Pagination
            pagination = db.paginate(query, page=page, per_page=ITEMS_PER_PAGE, error_out=False)
            
            # 5. Sérialisation (Flat DTOs)
            serialized_items = [{
                'id': obj.id,
                'nom': obj.nom,
                'quantite_physique': obj.quantite_physique,
                'seuil': obj.seuil,
                'date_peremption': obj.date_peremption,
                'image_url': obj.image_url,
                'fds_url': obj.fds_url, # Ajouté aussi au cas où
                
                # Noms pour l'affichage
                'armoire_nom': obj.armoire.nom if obj.armoire else None,
                'categorie_nom': obj.categorie.nom if obj.categorie else None,
                
                # IDs pour l'édition (C'EST CE QUI MANQUAIT)
                'armoire_id': obj.armoire_id,
                'categorie_id': obj.categorie_id,
                
                'quantite_disponible': obj.quantite_physique 
            } for obj in pagination.items]

            # 6. Contexte
            armoire_nom = None
            categorie_nom = None
            
            if filters.get('armoire_id'):
                a = db.session.get(Armoire, filters['armoire_id'])
                if a: armoire_nom = a.nom
            
            if filters.get('categorie_id'):
                c = db.session.get(Categorie, filters['categorie_id'])
                if c: categorie_nom = c.nom

            return InventoryDTO(
                items=serialized_items,
                total_pages=pagination.pages,
                current_page=page,
                context=InventoryContext(armoire_nom=armoire_nom, categorie_nom=categorie_nom)
            )

        except SQLAlchemyError as e:
            logger.error(f"Inventory error: {e}")
            raise InventoryServiceError("Impossible de charger l'inventaire.")