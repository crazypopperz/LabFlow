# -*- coding: utf-8 -*-
"""
Packs de matériel prédéfinis pour l'onboarding Scientral.
4 packs disponibles :
- Pack SVT Collège  (6e–3e)
- Pack SVT Lycée    (2nde–Terminale)
- Pack Physique-Chimie Collège (6e–3e)
- Pack Physique-Chimie Lycée   (2nde–Terminale)

Quantités = 1 par défaut (le gestionnaire met à jour selon ses stocks).
CMR identifiés selon les listes INRS / règlement CLP.
FDS : liens directs fiches toxicologiques INRS quand disponibles.
Aligné sur les programmes EN en vigueur (réforme 2019-2023).
"""

PACKS_ONBOARDING = [

    # ================================================================
    # PACK 1 — SVT COLLÈGE (6e–3e)
    # Focus : cellule, microscopie, vivant, classification,
    #         dissection, géologie, écologie, génétique intro
    # ================================================================
    {
        "id": "pack_svt_college",
        "nom": "Pack SVT Collège",
        "description": (
            "Matériel essentiel pour un laboratoire de SVT niveau collège (6e–3e). "
            "Microscopie, dissection, géologie, écologie et étude du vivant, "
            "aligné sur les programmes officiels."
        ),
        "niveau": "Collège",
        "discipline": "SVT",
        "icon": "bi-tree",
        "color": "#10b981",
        "armoires": [
            {"nom": "SVT-C Armoire 01", "description": "Microscopie et optique"},
            {"nom": "SVT-C Armoire 02", "description": "Dissection et anatomie"},
            {"nom": "SVT-C Armoire 03", "description": "Géologie — roches et minéraux"},
            {"nom": "SVT-C Armoire 04", "description": "Colorants et réactifs biologiques"},
            {"nom": "SVT-C Armoire 05", "description": "Écologie et terrain"},
            {"nom": "SVT-C Armoire 06", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Microscopie",
            "Verrerie et consommables",
            "Dissection",
            "Géologie",
            "Colorants biologiques",
            "Réactifs biologiques",
            "Écologie",
            "EPI",
        ],
        "objets": [
            # ── MICROSCOPIE — SVT-C Armoire 01 ──────────────────────────────
            {"nom": "Microscope optique binoculaire élève", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Loupe binoculaire stéréoscopique", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames porte-objet (boîte 50)", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lamelles couvre-objet 20×20 mm (boîte 100)", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Préparations microscopiques permanentes — cellule végétale", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Préparations microscopiques permanentes — cellule animale", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Préparations microscopiques permanentes — mitose", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Préparations microscopiques permanentes — coupe de feuille", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Huile à immersion pour objectif ×100", "type_objet": "produit", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Papier Joseph (nettoyage optique)", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "carnet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cellule de Malassez (numération)", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pipettes Pasteur en verre (sachet 100)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE ET CONSOMMABLES — SVT-C Armoire 01 ─────────────────
            {"nom": "Béchers 100 mL", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Béchers 250 mL", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tubes à essais en verre (sachet 50)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Portoir à tubes à essais", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boîtes de Pétri verre (lot 10)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Compte-gouttes plastique (sachet 100)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pinces en bois pour tubes", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Papier absorbant essuie-tout labo", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "rouleau", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── DISSECTION — SVT-C Armoire 02 ───────────────────────────────
            {"nom": "Scalpel manche métal + lames (lot 10 lames)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ciseaux de dissection droits", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ciseaux de dissection courbes", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pinces à dissection fine (brucelles)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Épingles de dissection (boîte 100)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuvettes de dissection fond cire (25×15 cm)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sondes canules (lot 5)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Solution de Ringer physiologique", "type_objet": "produit", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Formol 4% (fixateur) — usage labo", "type_objet": "produit", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_67-3/FT67.pdf"},
            {"nom": "Modèle anatomique — cœur humain", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle anatomique — œil humain", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Squelette humain articulé grandeur nature", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Collection insectes épinglés (boîte entomologique)", "type_objet": "materiel", "categorie": "Dissection", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── GÉOLOGIE — SVT-C Armoire 03 ─────────────────────────────────
            {"nom": "Collection roches magmatiques (lot 10)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Collection roches sédimentaires (lot 10)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Collection roches métamorphiques (lot 10)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Collection minéraux (lot 20)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames minces de roches — set microscopie polarisante", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fossiles — lot pédagogique (10 spécimens)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide chlorhydrique 10% (test calcaire)", "type_objet": "produit", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_52-5/FT52.pdf"},
            {"nom": "Planche de dureté Mohs (set 10 minéraux référence)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boussole géologique", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Loupe de géologue ×10", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── COLORANTS BIOLOGIQUES — SVT-C Armoire 04 ────────────────────
            {"nom": "Bleu de méthylène solution 0,1%", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lugol (solution iodo-iodurée) — test amidon", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éosine solution aqueuse diluée", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Carmin aluminé (colorant noyaux)", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Vert de méthyle acétique — coloration ADN", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Rouge neutre solution diluée", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS BIOLOGIQUES — SVT-C Armoire 04 ─────────────────────
            {"nom": "Réactif de Fehling A + B — test glucose", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réactif de Bradford — dosage protéines", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bandelettes test glucose urinaire", "type_objet": "materiel", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau distillée (bidon 5 L)", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "bidon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Solution tampon pH 7 (phosphate)", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Levures de boulanger sèches", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau de chaux (hydroxyde de calcium dilué)", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉCOLOGIE ET TERRAIN — SVT-C Armoire 05 ──────────────────────
            {"nom": "Filets à papillons (épuisettes entomologiques)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filets troubleaux (pêche invertébrés aquatiques)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bacs de terrain transparents (30×20 cm)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pièges à fosse (pitfall traps, lot 10)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "PHmètre portable étanche terrain", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde thermomètre numérique terrain", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Luxmètre numérique", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Hygromètre numérique", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Règles et rubans gradués (10 m)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Clés de détermination flore locale", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Clés de détermination faune (insectes, oiseaux…)", "type_objet": "materiel", "categorie": "Écologie", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — SVT-C Armoire 06 ───────────────────────────────────────
            {"nom": "Lunettes de protection incolores (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève (taille M/L)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille L (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Container à déchets piquants-coupants (OPCT)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence portable (flacon 250 mL)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sac poubelle jaune DASRI (déchets biologiques)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 5, "unite": "rouleau", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 2 — SVT LYCÉE (2nde–Terminale)
    # Focus : génétique moléculaire, immunologie, neurosciences,
    #         évolution, écologie approfondie, biologie cellulaire
    # ================================================================
    {
        "id": "pack_svt_lycee",
        "nom": "Pack SVT Lycée",
        "description": (
            "Matériel pour un laboratoire de SVT niveau lycée (2nde–Terminale). "
            "Génétique et électrophorèse, immunologie, neurosciences, évolution "
            "et modélisation, aligné sur les programmes post-bac."
        ),
        "niveau": "Lycée",
        "discipline": "SVT",
        "icon": "bi-activity",
        "color": "#6366f1",
        "armoires": [
            {"nom": "SVT-L Armoire 01", "description": "Biologie moléculaire et génétique"},
            {"nom": "SVT-L Armoire 02", "description": "Immunologie et microbiologie"},
            {"nom": "SVT-L Armoire 03", "description": "Neurosciences et physiologie"},
            {"nom": "SVT-L Armoire 04", "description": "Microscopie avancée"},
            {"nom": "SVT-L Armoire 05", "description": "Géologie et tectonique"},
            {"nom": "SVT-L Armoire 06", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Électrophorèse",
            "Biologie moléculaire",
            "Immunologie",
            "Microbiologie",
            "Neurosciences",
            "Microscopie avancée",
            "Géologie lycée",
            "Réactifs avancés",
            "EPI",
        ],
        "objets": [
            # ── ÉLECTROPHORÈSE — SVT-L Armoire 01 ───────────────────────────
            {"nom": "Cuve à électrophorèse horizontal (gel agarose)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Alimentation électrophorèse 300 V / 400 mA", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Agarose poudre (flacon 25 g)", "type_objet": "produit", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tampon TAE 50× concentré (électrophorèse)", "type_objet": "produit", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Marqueur de taille ADN (100 pb ladder)", "type_objet": "produit", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bromure d'éthidium — colorant ADN (ATTENTION CMR)", "type_objet": "produit", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_246-1/FT246.pdf"},
            {"nom": "SYBR Safe (alternative non-CMR au BET)", "type_objet": "produit", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Micropipettes 10 µL / 100 µL / 1000 µL (jeu 3)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cônes pour micropipettes 10 µL (sachet 200)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cônes pour micropipettes 200 µL (sachet 200)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cônes pour micropipettes 1000 µL (sachet 200)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tubes Eppendorf 1,5 mL (sachet 500)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bloc chauffant (thermoblock) 0-100°C", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Transilluminateur UV (visualisation gels)", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit ADN simulation crime — électrophorèse pédagogique", "type_objet": "materiel", "categorie": "Électrophorèse", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── BIOLOGIE MOLÉCULAIRE — SVT-L Armoire 01 ─────────────────────
            {"nom": "Centrifugeuse de paillasse (6 000 rpm)", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Vortex agitateur", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit extraction ADN végétal (protocole sel / alcool)", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éthanol 95° (précipitation ADN)", "type_objet": "produit", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Détergent SDS 10% (lyse cellulaire)", "type_objet": "produit", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle double hélice ADN (didactique)", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── IMMUNOLOGIE — SVT-L Armoire 02 ──────────────────────────────
            {"nom": "Kit ELISA pédagogique (simulation test VIH)", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Plaques ELISA 96 puits", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit groupes sanguins ABO (antigènes simulés)", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lecteur ELISA (spectrophotomètre 405 nm)", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Posters paroi des anticorps / réponse immunitaire", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MICROBIOLOGIE — SVT-L Armoire 02 ────────────────────────────
            {"nom": "Étuve bactériologique 37°C", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bec Bunsen (ou brûleur à alcool)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boîtes de Pétri stériles (lot 20)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gélose nutritive prête à l'emploi (boîtes)", "type_objet": "produit", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot 10", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Anses de platine (lot 100 unités)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Alcool 70° (désinfection plans de travail)", "type_objet": "produit", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau de Javel 2,6% (désinfection déchets bio)", "type_objet": "produit", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Disques d'antibiotiques (antibiogramme pédagogique)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── NEUROSCIENCES — SVT-L Armoire 03 ────────────────────────────
            {"nom": "Modèle cerveau humain 9 pièces démontable", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Neurone géant modèle didactique", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électroencéphalographe pédagogique (ExAO EEG)", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électromyographe pédagogique (ExAO EMG)", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Oxymètre de pouls digital (SpO2)", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Spiromètre numérique (capacité respiratoire)", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ergomètre (vélo ou step pédagogique)", "type_objet": "materiel", "categorie": "Neurosciences", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MICROSCOPIE AVANCÉE — SVT-L Armoire 04 ──────────────────────
            {"nom": "Microscope polarisant (lames minces pétrographie)", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Caméra USB adaptateur microscope", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames permanentes — mitose et méiose (set 6)", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames permanentes — histologie tissus animaux (set 10)", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réactif de Feulgen (coloration ADN spécifique)", "type_objet": "produit", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "HCl 1N (hydrolyse acide — protocole Feulgen)", "type_objet": "produit", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_52-5/FT52.pdf"},

            # ── GÉOLOGIE LYCÉE — SVT-L Armoire 05 ───────────────────────────
            {"nom": "Lames minces de roches magmatiques — Alpes et volcans", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames minces de roches métamorphiques", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Maquette tectonique des plaques (fond d'océan)", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sismographe pédagogique numérique", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Carottes sédimentaires simulées (tubes PVC)", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — SVT-L Armoire 06 ───────────────────────────────────────
            {"nom": "Lunettes de protection chimique (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève lycée", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Masque FFP2 (travail avec CMR ou aérosols)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 10, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Container à déchets piquants-coupants (OPCT)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sac poubelle jaune DASRI (déchets biologiques)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 5, "unite": "rouleau", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence portable (flacon 250 mL)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 3 — PHYSIQUE-CHIMIE COLLÈGE (6e–3e)
    # Focus : états de la matière, mélanges/solutions,
    #         électricité simple, optique géométrique, mécanique intro
    # ================================================================
    {
        "id": "pack_pc_college",
        "nom": "Pack Physique-Chimie Collège",
        "description": (
            "Matériel pour un laboratoire de Physique-Chimie niveau collège (6e–3e). "
            "Électricité, optique, mécanique, états de la matière et réactions chimiques "
            "de base, aligné sur les programmes officiels."
        ),
        "niveau": "Collège",
        "discipline": "Physique-Chimie",
        "icon": "bi-lightning",
        "color": "#f59e0b",
        "armoires": [
            {"nom": "PC-C Armoire 01", "description": "Électricité et magnétisme"},
            {"nom": "PC-C Armoire 02", "description": "Optique et mécanique"},
            {"nom": "PC-C Armoire 03", "description": "Chimie — produits et verrerie"},
            {"nom": "PC-C Armoire 04", "description": "Mesure et instrumentation"},
            {"nom": "PC-C Armoire 05", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Électricité",
            "Magnétisme",
            "Optique",
            "Mécanique",
            "Verrerie chimie",
            "Produits chimiques collège",
            "Mesure",
            "EPI",
        ],
        "objets": [
            # ── ÉLECTRICITÉ — PC-C Armoire 01 ────────────────────────────────
            {"nom": "Générateur de tension continue 0-12V DC", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Piles 1,5V R20 (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Porte-piles 2×1,5V avec fils", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ampoules 1,5V / 0,3A pour circuits (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "LED rouge + verte + bleue (lot 30)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Résistances assorties 100Ω-10kΩ (lot 50)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Conducteurs souples avec fiches banane (lot 20)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Interrupteurs à bascule (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Moteur électrique DC pédagogique", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Rhéostat coulissant 10Ω / 3A", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Plaquette de montage (breadboard)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MAGNÉTISME — PC-C Armoire 01 ────────────────────────────────
            {"nom": "Aimants barreaux (paire NS)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "paire", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Aimants en U (fer à cheval)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boussoles de paillasse (lot 10)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Limaille de fer (tube 100 g — visualisation lignes de champ)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "tube", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électroaimant bobine de Helmholtz", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── OPTIQUE — PC-C Armoire 02 ────────────────────────────────────
            {"nom": "Banc optique gradué 1 m avec cavaliers", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lentilles convergentes (f=+10, +20, +50 cm) lot", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lentilles divergentes (f=−10, −20 cm) lot", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Miroirs plans (lot 5)", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Prisme optique en verre crown", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Source lumineuse pour banc optique (ampoule halogène)", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Écran blanc pour banc optique", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Diaphragme fente réglable", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réseau de diffraction 100 traits/mm", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filtre colorés (rouge, vert, bleu, jaune) lot", "type_objet": "materiel", "categorie": "Optique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MÉCANIQUE — PC-C Armoire 02 ─────────────────────────────────
            {"nom": "Dynamomètres 1N / 5N / 10N (jeu 3)", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Masses marquées 50 g / 100 g / 200 g (lot)", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Poulie simple fixe + mobile", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Plan incliné réglable en angle", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Règle graduée 30 cm + 1 m (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE CHIMIE — PC-C Armoire 03 ───────────────────────────
            {"nom": "Béchers 100 mL (lot 10)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Béchers 250 mL (lot 10)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Erlenmeyers 100 mL / 250 mL (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éprouvettes graduées 25 mL / 100 mL / 250 mL", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fioles jaugées 100 mL / 250 mL (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Entonnoirs en verre (lot 5)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Baguettes en verre (lot 10)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tubes à essais en verre (lot 50)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filtres en papier (lot 100)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tiges, noix, pinces — set de fixation paillasse", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trépied + toile métallique céramique", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Brûleur à alcool + alcool à brûler (flacon 500 mL)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── PRODUITS CHIMIQUES COLLÈGE — PC-C Armoire 03 ────────────────
            {"nom": "Eau distillée (bidon 5 L)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "bidon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sel de cuisine NaCl (500 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sucre saccharose (500 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bicarbonate de sodium NaHCO3 (500 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Vinaigre blanc 8° (1 L)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau oxygénée 3% (110 vol., 1 L)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide chlorhydrique dilué 1 mol/L", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_52-5/FT52.pdf"},
            {"nom": "Soude NaOH 1 mol/L", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_55-5/FT55.pdf"},
            {"nom": "Sulfate de cuivre CuSO4 (100 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bleu de bromothymol (BBT) 0,04% — indicateur pH", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bandelettes pH universel", "type_objet": "materiel", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MESURE — PC-C Armoire 04 ─────────────────────────────────────
            {"nom": "Multimètre numérique pédagogique", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Voltmètre/ampèremètre analogique de tableau", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Balance de précision 0,1 g / 500 g", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chronomètre numérique", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre numérique 0-200°C", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pied à coulisse 150 mm numérique", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éprouvette graduée 100 mL (lot 5) — mesure volume", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — PC-C Armoire 05 ────────────────────────────────────────
            {"nom": "Lunettes de protection chimique (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence portable (flacon 250 mL)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pictogrammes de danger SGH (jeu complet plastifié)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Extincteur CO2 2 kg", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 4 — PHYSIQUE-CHIMIE LYCÉE (2nde–Terminale)
    # Focus : chimie organique, thermodynamique, mécanique avancée,
    #         ondes, électrochimie, spectroscopie, ExAO
    # ================================================================
    {
        "id": "pack_pc_lycee",
        "nom": "Pack Physique-Chimie Lycée",
        "description": (
            "Matériel complet pour un laboratoire de Physique-Chimie niveau lycée (2nde–Terminale). "
            "Chimie organique et synthèse, électrochimie, mécanique, ondes et spectroscopie, "
            "aligné sur les programmes post-réforme 2019."
        ),
        "niveau": "Lycée",
        "discipline": "Physique-Chimie",
        "icon": "bi-flask",
        "color": "#ef4444",
        "armoires": [
            {"nom": "PC-L Armoire 01", "description": "Chimie organique et synthèse"},
            {"nom": "PC-L Armoire 02", "description": "Électrochimie et électricité avancée"},
            {"nom": "PC-L Armoire 03", "description": "Mécanique et thermodynamique"},
            {"nom": "PC-L Armoire 04", "description": "Ondes, spectroscopie et optique avancée"},
            {"nom": "PC-L Armoire 05", "description": "Produits chimiques et réactifs"},
            {"nom": "PC-L Armoire 06", "description": "EPI et sécurité renforcée"},
        ],
        "categories": [
            "Chimie organique",
            "Verrerie spécialisée",
            "Électrochimie",
            "Électricité lycée",
            "Mécanique avancée",
            "Thermodynamique",
            "Ondes et spectroscopie",
            "Réactifs acides-bases",
            "Réactifs organiques",
            "Métaux et solides",
            "EPI renforcé",
        ],
        "objets": [
            # ── CHIMIE ORGANIQUE — PC-L Armoire 01 ──────────────────────────
            {"nom": "Réfrigérant à boules (condenseur vertical)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chauffe-ballon électrique 250 mL avec variateur", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Agitateur magnétique chauffant", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Barreaux magnétiques assortis (lot 10)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ampoule à décanter 250 mL (robinet téflon)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ballon fond rond 250 mL (lot 5)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Colonne de distillation Vigreux 30 cm", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre 0-300°C (distillation)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit rodage verre 14/23 (joints + adaptateurs)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chromatographie sur couche mince (CCM) — plaques silice (lot 25)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuve à CCM en verre avec couvercle", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réfractomètre portatif (indice de réfraction)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre de contrôle point de fusion (appareil Kofler)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE SPÉCIALISÉE — PC-L Armoire 01 ──────────────────────
            {"nom": "Burettes de précision 50 mL (robinet verre)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pipettes graduées 5 mL / 10 mL / 25 mL (lot 3 de chaque)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Propipette (poire aspirante sécurisée)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fioles jaugées 100 mL / 250 mL / 500 mL / 1 L (lot)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Béchers 50 / 100 / 250 / 500 / 1000 mL (lot complet)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Erlenmeyers 100 / 250 / 500 mL avec bouchon (lot)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉLECTROCHIMIE — PC-L Armoire 02 ─────────────────────────────
            {"nom": "Électrode de verre pH (combinée)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "pHmètre numérique de précision ±0,01", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Conductimètre numérique avec sonde", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Solutions tampons pH 4, 7 et 10 (flacons étalonnage)", "type_objet": "produit", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électrodes de graphite barreaux (lot 10)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électrodes de zinc / cuivre / fer (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pont électrolytique (tube en U + gel KCl)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pots à électrolyse en verre (lot 5)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉLECTRICITÉ LYCÉE — PC-L Armoire 02 ─────────────────────────
            {"nom": "Générateur de tension continue + alternatif 0-12V", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Oscilloscope numérique 2 voies (50 MHz)", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Générateur basse fréquence (GBF) 0,1 Hz – 1 MHz", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Condensateurs assortis (lot — µF, nF, pF)", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bobines inductances assortis (lot — mH, H)", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Multimètre de précision 6000 points", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fils banane-banane (lot 20 de couleurs variées)", "type_objet": "materiel", "categorie": "Électricité lycée", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MÉCANIQUE AVANCÉE — PC-L Armoire 03 ─────────────────────────
            {"nom": "Capteur de force ExAO (±50 N)", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur de mouvement ultrasonique ExAO", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chronophotographe numérique stroboscope", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pendule de Newton (5 billes acier)", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Rail à coussin d'air avec chariot (2 m)", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Balles de différentes masses (lot pour chocs)", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Interface ExAO USB (acquisitions capteurs)", "type_objet": "materiel", "categorie": "Mécanique avancée", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── THERMODYNAMIQUE — PC-L Armoire 03 ───────────────────────────
            {"nom": "Calorimètre en aluminium avec accessoires", "type_objet": "materiel", "categorie": "Thermodynamique", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Résistance chauffante pour calorimètre (50 Ω)", "type_objet": "materiel", "categorie": "Thermodynamique", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur de température ExAO (−20 à +110°C)", "type_objet": "materiel", "categorie": "Thermodynamique", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre de précision 0,1°C", "type_objet": "materiel", "categorie": "Thermodynamique", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Plaque chauffante céramique 1500 W (paillasse)", "type_objet": "materiel", "categorie": "Thermodynamique", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ONDES ET SPECTROSCOPIE — PC-L Armoire 04 ────────────────────
            {"nom": "Spectroscope à réseau de diffraction (visible)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lampes spectrales (H, He, Ne, Na) avec alimentation HT", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Spectrophotomètre UV-Visible (absorbance)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuves plastique pour spectrophotomètre (lot 100)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur ExAO ultrason (mesure vitesse son)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Laser rouge (classe 2, <1 mW) pour optique ondulatoire", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réseau de diffraction 300 / 600 / 1200 traits/mm (lot)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS ACIDES-BASES — PC-L Armoire 05 ─────────────────────
            {"nom": "Acide chlorhydrique 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_52-5/FT52.pdf"},
            {"nom": "Acide sulfurique 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_1-8/FT1.pdf"},
            {"nom": "Acide acétique 1 mol/L (vinaigre concentré, 1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Soude NaOH 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_55-5/FT55.pdf"},
            {"nom": "Ammoniaque solution 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_16-7/FT16.pdf"},
            {"nom": "Phénolphtaléine solution 0,5% dans éthanol", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_160-3/FT160.pdf"},
            {"nom": "Bleu de bromothymol (BBT) 0,04%", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Permanganate de potassium KMnO4 (100 g)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Nitrate d'argent AgNO3 solution 0,1 mol/L", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS ORGANIQUES — PC-L Armoire 05 ───────────────────────
            {"nom": "Éthanol absolu 99,5° (1 L) — synthèse organique", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cyclohexane (500 mL) — solvant organique", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide éthanoïque (acide acétique glacial, 500 mL)", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Anhydride acétique (100 mL) — synthèse aspirine", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide salicylique (50 g) — synthèse aspirine", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide benzoïque (100 g)", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acétate d'éthyle (500 mL) — solvant CCM", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Hexane (500 mL) — solvant CCM", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_1-8/FT1.pdf"},
            {"nom": "Dichlorométhane (500 mL) — solvant extraction", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_32-5/FT32.pdf"},

            # ── MÉTAUX ET SOLIDES — PC-L Armoire 05 ─────────────────────────
            {"nom": "Grenailles de zinc (200 g)", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ruban de magnésium (1 m)", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "rouleau", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Poudre de soufre sublimé (100 g)", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Iode solide (10 g) — élution CCM révélateur", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sulfate de cuivre anhydre CuSO4 (100 g)", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau distillée bidon 5 L", "type_objet": "produit", "categorie": "Métaux et solides", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "bidon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI RENFORCÉ — PC-L Armoire 06 ──────────────────────────────
            {"nom": "Lunettes de protection chimique anti-projections (élève)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc (ignifugé pour chimie organique)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile taille M résistants aux solvants (boîte 100)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants latex épais résistants acides/bases (taille M, L)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 5, "unite": "paire", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Masque demi-face avec cartouche A1 (vapeurs organiques)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Masque FFP2 (lot 20)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence fixe avec robinet (mural)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Extincteur CO2 2 kg", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bac de rétention plastique (produits CMR)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pictogrammes de danger SGH (jeu complet plastifié)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Absorbant universel (sable ou vermiculite, sac 5 kg)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "sac", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },
]
