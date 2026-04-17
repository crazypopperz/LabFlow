# -*- coding: utf-8 -*-
"""
Packs de matériel prédéfinis pour l'onboarding Scientral.
4 packs disponibles :
- Pack SVT Collège  (6e–3e)
- Pack SVT Lycée    (2nde–Terminale)
- Pack Physique-Chimie Collège (6e–3e)
- Pack Physique-Chimie Lycée   (2nde–Terminale)

Quantités = 1 par défaut (le gestionnaire met à jour selon ses stocks).
CMR identifiés selon les listes INRS / règlement CLP / Directives ONS.
FDS : liens directs fiches toxicologiques INRS quand disponibles.
Aligné sur les programmes EN en vigueur (réforme 2016-2020 Collège, 2019 Lycée).
"""

PACKS_ONBOARDING = [

    # ================================================================
    # PACK 1 — SVT COLLÈGE (6e–3e)
    # Focus : cellule, microscopie, vivant, classification,
    #         géologie (volcans/séismes), écologie, génétique intro
    # ================================================================
    {
        "id": "pack_svt_college",
        "nom": "Pack SVT Collège",
        "description": (
            "Matériel essentiel pour un laboratoire de SVT niveau collège (6e–3e). "
            "Microscopie, géologie (volcans/séismes), écologie, ExAO de base et étude du vivant, "
            "strictement aligné sur les programmes officiels et les normes de sécurité."
        ),
        "niveau": "Collège",
        "discipline": "SVT",
        "icon": "bi-tree",
        "color": "#10b981",
        "armoires": [
            {"nom": "SVT-C Armoire 01", "description": "Microscopie et optique"},
            {"nom": "SVT-C Armoire 02", "description": "Anatomie et génétique"},
            {"nom": "SVT-C Armoire 03", "description": "Géologie — roches et maquettes"},
            {"nom": "SVT-C Armoire 04", "description": "Colorants et réactifs biologiques"},
            {"nom": "SVT-C Armoire 05", "description": "Écologie, terrain et ExAO"},
            {"nom": "SVT-C Armoire 06", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Microscopie",
            "Verrerie et consommables",
            "Anatomie et Génétique",
            "Géologie",
            "Colorants biologiques",
            "Réactifs biologiques",
            "Écologie et ExAO",
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
            {"nom": "Papier Joseph (nettoyage optique)", "type_objet": "materiel", "categorie": "Microscopie", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "carnet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pipettes Pasteur en plastique (sachet 100)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE ET CONSOMMABLES — SVT-C Armoire 01 ─────────────────
            {"nom": "Béchers 100 mL", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Béchers 250 mL", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tubes à essais en verre (sachet 50)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Portoir à tubes à essais", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boîtes de Pétri plastique stériles (lot 20)", "type_objet": "materiel", "categorie": "Verrerie et consommables", "armoire": "SVT-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ANATOMIE ET GÉNÉTIQUE — SVT-C Armoire 02 ────────────────────
            {"nom": "Scalpel manche métal + lames (lot 10 lames)", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ciseaux de dissection fins", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pinces à dissection fine (brucelles)", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuvettes de dissection fond cire (25×15 cm)", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle anatomique — cœur humain démontable", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle anatomique — appareil respiratoire", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Squelette humain articulé grandeur nature", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle moléculaire ADN simplifié (collège)", "type_objet": "materiel", "categorie": "Anatomie et Génétique", "armoire": "SVT-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── GÉOLOGIE — SVT-C Armoire 03 ─────────────────────────────────
            {"nom": "Collection roches magmatiques (lot 10)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Collection roches sédimentaires (lot 10)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fossiles — lot pédagogique (10 spécimens)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide chlorhydrique 10% (test calcaire)", "type_objet": "produit", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_13/FT13.pdf"},
            {"nom": "Maquette de volcan (éruption effusive/explosive)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Maquette sismologique (propagation ondes)", "type_objet": "materiel", "categorie": "Géologie", "armoire": "SVT-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── COLORANTS BIOLOGIQUES — SVT-C Armoire 04 ────────────────────
            {"nom": "Bleu de méthylène solution 0,1%", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lugol (solution iodo-iodurée) — test amidon", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éosine solution aqueuse diluée", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Rouge neutre solution diluée", "type_objet": "produit", "categorie": "Colorants biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS BIOLOGIQUES — SVT-C Armoire 04 ─────────────────────
            {"nom": "Réactif de Fehling A + B — test glucose", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bandelettes test glucose urinaire", "type_objet": "materiel", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau distillée (bidon 5 L)", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "bidon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Levures de boulanger sèches", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Eau de chaux (hydroxyde de calcium dilué)", "type_objet": "produit", "categorie": "Réactifs biologiques", "armoire": "SVT-C Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉCOLOGIE ET ExAO — SVT-C Armoire 05 ─────────────────────────
            {"nom": "Appareil de Berlèse (extraction faune du sol)", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Console ExAO portable (acquisition données)", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde ExAO Oxymètre (O2 dissous/air)", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde ExAO Température", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filets troubleaux (pêche invertébrés aquatiques)", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Clés de détermination flore/faune locale", "type_objet": "materiel", "categorie": "Écologie et ExAO", "armoire": "SVT-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — SVT-C Armoire 06 ───────────────────────────────────────
            {"nom": "Lunettes de protection incolores (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève (taille M/L)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Container à déchets piquants-coupants (OPCT)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence portable (flacon 250 mL)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-C Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 2 — SVT LYCÉE (2nde–Terminale)
    # Focus : génétique moléculaire (PCR), immunologie, neurosciences,
    #         métabolisme (ExAO), évolution, biologie cellulaire
    # ================================================================
    {
        "id": "pack_svt_lycee",
        "nom": "Pack SVT Lycée",
        "description": (
            "Matériel pour un laboratoire de SVT niveau lycée (2nde–Terminale). "
            "Génétique (PCR, électrophorèse), immunologie, métabolisme (ExAO complet), "
            "aligné sur les programmes post-bac et sans CMR."
        ),
        "niveau": "Lycée",
        "discipline": "SVT",
        "icon": "bi-activity",
        "color": "#6366f1",
        "armoires": [
            {"nom": "SVT-L Armoire 01", "description": "Biologie moléculaire et génétique"},
            {"nom": "SVT-L Armoire 02", "description": "Immunologie et microbiologie"},
            {"nom": "SVT-L Armoire 03", "description": "Physiologie et ExAO Métabolisme"},
            {"nom": "SVT-L Armoire 04", "description": "Microscopie avancée"},
            {"nom": "SVT-L Armoire 05", "description": "Géologie et tectonique"},
            {"nom": "SVT-L Armoire 06", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Génétique et PCR",
            "Biologie moléculaire",
            "Immunologie",
            "Microbiologie",
            "Physiologie et ExAO",
            "Microscopie avancée",
            "Géologie lycée",
            "EPI",
        ],
        "objets": [
            # ── GÉNÉTIQUE ET PCR — SVT-L Armoire 01 ─────────────────────────
            {"nom": "Thermocycleur pédagogique (PCR)", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuve à électrophorèse horizontal (gel agarose)", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Alimentation électrophorèse 300 V / 400 mA", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Agarose poudre (flacon 25 g)", "type_objet": "produit", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tampon TAE 50× concentré (électrophorèse)", "type_objet": "produit", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "SYBR Safe ou Fast Blast DNA (colorant ADN non-CMR)", "type_objet": "produit", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Micropipettes 10 µL / 100 µL / 1000 µL (jeu 3)", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cônes pour micropipettes (assortiment)", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Transilluminateur UV ou LED bleue (visualisation gels)", "type_objet": "materiel", "categorie": "Génétique et PCR", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── BIOLOGIE MOLÉCULAIRE — SVT-L Armoire 01 ─────────────────────
            {"nom": "Centrifugeuse de paillasse (6 000 rpm)", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Vortex agitateur", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit extraction ADN végétal (protocole sel / alcool)", "type_objet": "materiel", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éthanol 95° (précipitation ADN)", "type_objet": "produit", "categorie": "Biologie moléculaire", "armoire": "SVT-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── IMMUNOLOGIE — SVT-L Armoire 02 ──────────────────────────────
            {"nom": "Kit ELISA pédagogique (simulation test VIH)", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Plaques ELISA 96 puits", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit groupes sanguins ABO (antigènes simulés)", "type_objet": "materiel", "categorie": "Immunologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MICROBIOLOGIE — SVT-L Armoire 02 ────────────────────────────
            {"nom": "Étuve bactériologique 37°C", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bec Bunsen (ou brûleur à alcool)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boîtes de Pétri stériles (lot 20)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit transformation bactérienne (plasmide pGLO / E. coli K12)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Disques d'antibiotiques (antibiogramme pédagogique)", "type_objet": "materiel", "categorie": "Microbiologie", "armoire": "SVT-L Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── PHYSIOLOGIE ET ExAO — SVT-L Armoire 03 ──────────────────────
            {"nom": "Bioréacteur ExAO complet (enceinte + agitation)", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde ExAO O2 (dioxygène)", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde ExAO CO2 (dioxyde de carbone)", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonde ExAO Éthanol (fermentation)", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électromyographe pédagogique (ExAO EMG - réflexe myotatique)", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Modèle cerveau humain démontable", "type_objet": "materiel", "categorie": "Physiologie et ExAO", "armoire": "SVT-L Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MICROSCOPIE AVANCÉE — SVT-L Armoire 04 ──────────────────────
            {"nom": "Microscope polarisant (lames minces pétrographie)", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Micromètre oculaire et lame micrométrique", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Caméra USB adaptateur microscope", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames permanentes — mitose et méiose (set 6)", "type_objet": "materiel", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Orcéine acétique (coloration chromosomes/mitose)", "type_objet": "produit", "categorie": "Microscopie avancée", "armoire": "SVT-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── GÉOLOGIE LYCÉE — SVT-L Armoire 05 ───────────────────────────
            {"nom": "Lames minces de roches magmatiques — Alpes et volcans", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lames minces de roches métamorphiques", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "set", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Maquette tectonique des plaques (fond d'océan)", "type_objet": "materiel", "categorie": "Géologie lycée", "armoire": "SVT-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — SVT-L Armoire 06 ───────────────────────────────────────
            {"nom": "Lunettes de protection chimique (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève lycée", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Container à déchets piquants-coupants (OPCT)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sac poubelle jaune DASRI (déchets biologiques)", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 5, "unite": "rouleau", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "SVT-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 3 — PHYSIQUE-CHIMIE COLLÈGE (6e–3e)
    # Focus : états de la matière, mélanges/solutions,
    #         électricité simple, optique, mécanique, son
    # ================================================================
    {
        "id": "pack_pc_college",
        "nom": "Pack Physique-Chimie Collège",
        "description": (
            "Matériel pour un laboratoire de Physique-Chimie niveau collège (6e–3e). "
            "Électricité, optique, mécanique, son, états de la matière et réactions chimiques "
            "de base (concentrations adaptées à la sécurité collège)."
        ),
        "niveau": "Collège",
        "discipline": "Physique-Chimie",
        "icon": "bi-lightning",
        "color": "#f59e0b",
        "armoires": [
            {"nom": "PC-C Armoire 01", "description": "Électricité et magnétisme"},
            {"nom": "PC-C Armoire 02", "description": "Optique, mécanique et son"},
            {"nom": "PC-C Armoire 03", "description": "Chimie — produits et verrerie"},
            {"nom": "PC-C Armoire 04", "description": "Mesure et instrumentation"},
            {"nom": "PC-C Armoire 05", "description": "EPI et sécurité"},
        ],
        "categories": [
            "Électricité",
            "Magnétisme",
            "Optique et Son",
            "Mécanique",
            "Verrerie chimie",
            "Produits chimiques collège",
            "Mesure",
            "EPI",
        ],
        "objets": [
            # ── ÉLECTRICITÉ — PC-C Armoire 01 ────────────────────────────────
            {"nom": "Générateur de tension continue protégé 6V/12V", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Piles 1,5V R20 (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ampoules 6V / 0,1A pour circuits (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "LED rouge + verte + bleue (lot 30)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Résistances assorties (lot 50)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Conducteurs souples avec fiches banane (lot 20)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Interrupteurs à bascule (lot 10)", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Moteur électrique DC pédagogique", "type_objet": "materiel", "categorie": "Électricité", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MAGNÉTISME — PC-C Armoire 01 ────────────────────────────────
            {"nom": "Aimants barreaux (paire NS)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "paire", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Aimants en U (fer à cheval)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boussoles de paillasse (lot 10)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Limaille de fer (tube 100 g — visualisation lignes de champ)", "type_objet": "materiel", "categorie": "Magnétisme", "armoire": "PC-C Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "tube", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── OPTIQUE ET SON — PC-C Armoire 02 ─────────────────────────────
            {"nom": "Banc optique gradué 1 m avec cavaliers", "type_objet": "materiel", "categorie": "Optique et Son", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lentilles convergentes et divergentes (lot)", "type_objet": "materiel", "categorie": "Optique et Son", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Source lumineuse pour banc optique", "type_objet": "materiel", "categorie": "Optique et Son", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filtres colorés et réseaux de diffraction (lot)", "type_objet": "materiel", "categorie": "Optique et Son", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sonomètre numérique (étude du son)", "type_objet": "materiel", "categorie": "Optique et Son", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MÉCANIQUE — PC-C Armoire 02 ─────────────────────────────────
            {"nom": "Dynamomètres 1N / 5N / 10N (jeu 3)", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Masses marquées 50 g / 100 g / 200 g (lot)", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éprouvette graduée 100 mL (lot 5) — mesure volume/masse volumique", "type_objet": "materiel", "categorie": "Mécanique", "armoire": "PC-C Armoire 02", "quantite_physique": 1, "seuil": 1, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE CHIMIE — PC-C Armoire 03 ───────────────────────────
            {"nom": "Béchers 100 mL / 250 mL (lot 10 de chaque)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Erlenmeyers 100 mL / 250 mL (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Éprouvettes graduées 25 mL / 100 mL", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Tubes à essais en verre (lot 50)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Filtres en papier (lot 100) + Entonnoirs", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Boîte de modèles moléculaires élève (orga/minéral)", "type_objet": "materiel", "categorie": "Verrerie chimie", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 5, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── PRODUITS CHIMIQUES COLLÈGE — PC-C Armoire 03 ────────────────
            {"nom": "Eau distillée (bidon 5 L)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "bidon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Sel de cuisine NaCl (500 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bicarbonate de sodium NaHCO3 (500 g)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "sachet", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Vinaigre blanc 8° (1 L)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide chlorhydrique dilué 0,1 mol/L (sécurité collège)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_13/FT13.pdf"},
            {"nom": "Soude NaOH 0,1 mol/L (sécurité collège)", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_20/FT20.pdf"},
            {"nom": "Sulfate de cuivre anhydre CuSO4 (100 g) - test de l'eau", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bleu de bromothymol (BBT) 0,04% — indicateur pH", "type_objet": "produit", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Papier pH universel (rouleau)", "type_objet": "materiel", "categorie": "Produits chimiques collège", "armoire": "PC-C Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MESURE — PC-C Armoire 04 ─────────────────────────────────────
            {"nom": "Multimètre numérique pédagogique", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Balance de précision 0,1 g / 500 g", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre numérique 0-100°C", "type_objet": "materiel", "categorie": "Mesure", "armoire": "PC-C Armoire 04", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI — PC-C Armoire 05 ────────────────────────────────────────
            {"nom": "Lunettes de protection chimique (élève)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc élève", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile jetables taille M (boîte 100)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence portable (flacon 250 mL)", "type_objet": "materiel", "categorie": "EPI", "armoire": "PC-C Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },

    # ================================================================
    # PACK 4 — PHYSIQUE-CHIMIE LYCÉE (2nde–Terminale)
    # Focus : chimie organique, thermodynamique, mécanique avancée,
    #         ondes, électrochimie, programmation (Arduino/Python)
    # ================================================================
    {
        "id": "pack_pc_lycee",
        "nom": "Pack Physique-Chimie Lycée",
        "description": (
            "Matériel complet pour un laboratoire de Physique-Chimie niveau lycée (2nde–Terminale). "
            "Chimie organique, titrages, mécanique, ondes, programmation microcontrôleurs, "
            "aligné sur les programmes post-réforme 2019 (sans CMR interdits)."
        ),
        "niveau": "Lycée",
        "discipline": "Physique-Chimie",
        "icon": "bi-flask",
        "color": "#ef4444",
        "armoires": [
            {"nom": "PC-L Armoire 01", "description": "Chimie organique et synthèse"},
            {"nom": "PC-L Armoire 02", "description": "Électrochimie et électricité avancée"},
            {"nom": "PC-L Armoire 03", "description": "Mécanique, Thermo et Programmation"},
            {"nom": "PC-L Armoire 04", "description": "Ondes, spectroscopie et optique avancée"},
            {"nom": "PC-L Armoire 05", "description": "Produits chimiques et réactifs"},
            {"nom": "PC-L Armoire 06", "description": "EPI et sécurité renforcée"},
        ],
        "categories": [
            "Chimie organique",
            "Verrerie spécialisée",
            "Électrochimie",
            "Électricité et Programmation",
            "Mécanique et Thermo",
            "Ondes et spectroscopie",
            "Réactifs acides-bases",
            "Réactifs organiques",
            "EPI renforcé",
        ],
        "objets": [
            # ── CHIMIE ORGANIQUE — PC-L Armoire 01 ──────────────────────────
            {"nom": "Réfrigérant à boules (condenseur vertical)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chauffe-ballon électrique 250 mL avec variateur", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Agitateur magnétique chauffant", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ampoule à décanter 250 mL (robinet téflon)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Ballon fond rond 250 mL (lot 5)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Chromatographie sur couche mince (CCM) — plaques silice (lot 25)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cuve à CCM en verre avec couvercle", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Thermomètre de contrôle point de fusion (appareil Kofler)", "type_objet": "materiel", "categorie": "Chimie organique", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── VERRERIE SPÉCIALISÉE — PC-L Armoire 01 ──────────────────────
            {"nom": "Burettes de précision 25 mL (robinet téflon)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Pipettes jaugées 10 mL / 20 mL (lot 3 de chaque)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Propipette (poire aspirante sécurisée)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Fioles jaugées 100 mL / 250 mL (lot)", "type_objet": "materiel", "categorie": "Verrerie spécialisée", "armoire": "PC-L Armoire 01", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉLECTROCHIMIE — PC-L Armoire 02 ─────────────────────────────
            {"nom": "pHmètre numérique de précision avec électrode", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Conductimètre numérique avec sonde", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Solutions tampons pH 4, 7 et 10 (flacons étalonnage)", "type_objet": "produit", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "jeu", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Électrodes de zinc / cuivre / fer (lot 5 de chaque)", "type_objet": "materiel", "categorie": "Électrochimie", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ÉLECTRICITÉ ET PROGRAMMATION — PC-L Armoire 02 ──────────────
            {"nom": "Générateur de tension continue + alternatif 0-12V", "type_objet": "materiel", "categorie": "Électricité et Programmation", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Oscilloscope numérique 2 voies (50 MHz)", "type_objet": "materiel", "categorie": "Électricité et Programmation", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Générateur basse fréquence (GBF)", "type_objet": "materiel", "categorie": "Électricité et Programmation", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Kit microcontrôleur type Arduino (avec capteurs)", "type_objet": "materiel", "categorie": "Électricité et Programmation", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 2, "unite": "kit", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Multimètre de précision 6000 points", "type_objet": "materiel", "categorie": "Électricité et Programmation", "armoire": "PC-L Armoire 02", "quantite_physique": 1, "seuil": 5, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── MÉCANIQUE ET THERMO — PC-L Armoire 03 ───────────────────────
            {"nom": "Interface ExAO USB (acquisitions capteurs)", "type_objet": "materiel", "categorie": "Mécanique et Thermo", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur de force ExAO (±50 N)", "type_objet": "materiel", "categorie": "Mécanique et Thermo", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur de mouvement ultrasonique ExAO", "type_objet": "materiel", "categorie": "Mécanique et Thermo", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Calorimètre en aluminium avec accessoires", "type_objet": "materiel", "categorie": "Mécanique et Thermo", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Capteur de température ExAO (−20 à +110°C)", "type_objet": "materiel", "categorie": "Mécanique et Thermo", "armoire": "PC-L Armoire 03", "quantite_physique": 1, "seuil": 3, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── ONDES ET SPECTROSCOPIE — PC-L Armoire 04 ────────────────────
            {"nom": "Spectrophotomètre UV-Visible (absorbance)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Spectroscope à réseau de diffraction (visible)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Polarimètre de Laurent (étude de la chiralité)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Laser rouge (classe 2, <1 mW) pour optique ondulatoire", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Réseau de diffraction 300 / 600 / 1200 traits/mm (lot)", "type_objet": "materiel", "categorie": "Ondes et spectroscopie", "armoire": "PC-L Armoire 04", "quantite_physique": 1, "seuil": 2, "unite": "lot", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS ACIDES-BASES — PC-L Armoire 05 ─────────────────────
            {"nom": "Acide chlorhydrique 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_13/FT13.pdf"},
            {"nom": "Acide sulfurique solution aqueuse 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_30/FT30.pdf"},
            {"nom": "Soude NaOH 1 mol/L (1 L)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_20/FT20.pdf"},
            {"nom": "Phénolphtaléine solution 0,5% dans éthanol (ATTENTION CMR)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": True, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_160/FT160.pdf"},
            {"nom": "Bleu de bromothymol (BBT) 0,04%", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Permanganate de potassium KMnO4 (100 g)", "type_objet": "produit", "categorie": "Réactifs acides-bases", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── RÉACTIFS ORGANIQUES — PC-L Armoire 05 ───────────────────────
            {"nom": "Éthanol absolu 99,5° (1 L) — synthèse organique", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 2, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Cyclohexane (500 mL) — solvant organique", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_17/FT17.pdf"},
            {"nom": "Heptane (500 mL) — solvant extraction/CCM", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_65/FT65.pdf"},
            {"nom": "Acétate d'éthyle (500 mL) — solvant extraction/CCM", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": "https://www.inrs.fr/dms/ficheTox/FicheFicheTox/FICHETOX_18/FT18.pdf"},
            {"nom": "Acide éthanoïque (acide acétique glacial, 500 mL)", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Anhydride acétique (100 mL) — synthèse aspirine", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Acide salicylique (50 g) — synthèse aspirine", "type_objet": "produit", "categorie": "Réactifs organiques", "armoire": "PC-L Armoire 05", "quantite_physique": 1, "seuil": 1, "unite": "flacon", "is_cmr": False, "image_url": None, "fds_url": None},

            # ── EPI RENFORCÉ — PC-L Armoire 06 ──────────────────────────────
            {"nom": "Lunettes de protection chimique anti-projections (élève)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 30, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lunettes de protection anti-UV (pour CCM)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Blouses coton blanc (ignifugé pour chimie organique)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 15, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Gants nitrile taille M résistants aux solvants (boîte 100)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "boîte", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Lave-yeux d'urgence fixe avec robinet (mural)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Trousse premiers secours réglementaire", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Bac de rétention plastique (produits dangereux)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 2, "unite": "unité", "is_cmr": False, "image_url": None, "fds_url": None},
            {"nom": "Absorbant universel (sable ou vermiculite, sac 5 kg)", "type_objet": "materiel", "categorie": "EPI renforcé", "armoire": "PC-L Armoire 06", "quantite_physique": 1, "seuil": 1, "unite": "sac", "is_cmr": False, "image_url": None, "fds_url": None},
        ],
    },
]