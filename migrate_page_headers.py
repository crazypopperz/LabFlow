#!/usr/bin/env python3
"""
migrate_page_headers.py
Migre les templates publics (hors admin) vers la macro page_header unifiée.

Usage : python migrate_page_headers.py [--dry-run]
"""

import re
import sys
import shutil
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
TEMPLATES_DIR = Path("templates")
BACKUP_DIR = Path("templates/_backup_migration")

# ─── Configuration des pages publiques à migrer ───────────────────────────────
# Format : template_file → (title, subtitle, icon_class, icon_bg)
# icon_bg : couleur CSS (hex ou var())
# icon_class : classe Bootstrap Icons sans le préfixe "bi "

PAGES = {
    "index.html": {
        "title": "Tableau de Bord",
        "subtitle": None,
        "icon_class": "bi-motherboard-fill",
        "icon_bg": "var(--couleur-principale)",
        "has_breadcrumb": False,  # Page racine, pas de breadcrumb
    },
    "gestion_armoires.html": {
        "title": "Gestion des Armoires",
        "subtitle": "Ajoutez, modifiez et organisez vos armoires",
        "icon_class": "bi-box2-fill",
        "icon_bg": "#198754",
        "has_breadcrumb": True,
    },
    "gestion_categories.html": {
        "title": "Gestion des Catégories",
        "subtitle": "Organisez vos catégories de matériel",
        "icon_class": "bi-inboxes-fill",
        "icon_bg": "#0d6efd",
        "has_breadcrumb": True,
    },
    "calendrier.html": {
        "title": "Calendrier de Réservation",
        "subtitle": "Consultez et gérez les réservations",
        "icon_class": "bi-calendar2-week-fill",
        "icon_bg": "#6f42c1",
        "has_breadcrumb": True,
    },
    "alertes.html": {
        "title": "Alertes & Suggestions",
        "subtitle": "Gérez les alertes de stock et les demandes",
        "icon_class": "bi-bell-fill",
        "icon_bg": "#dc3545",
        "has_breadcrumb": True,
    },
    "panier.html": {
        "title": "Panier de Réservation",
        "subtitle": "Finalisez votre réservation de matériel",
        "icon_class": "bi-cart-fill",
        "icon_bg": "#0d6efd",
        "has_breadcrumb": True,
    },
    "budget.html": {
        "title": "Suivi Budgétaire",
        "subtitle": "Consultez et gérez le budget de l'établissement",
        "icon_class": "bi-cash-stack",
        "icon_bg": "#198754",
        "has_breadcrumb": True,
    },
    "rapports.html": {
        "title": "Rapports",
        "subtitle": "Analysez les données de votre inventaire",
        "icon_class": "bi-bar-chart-fill",
        "icon_bg": "#6f42c1",
        "has_breadcrumb": True,
    },
    "dormants.html": {
        "title": "Objets Dormants",
        "subtitle": "Matériel non utilisé depuis longtemps",
        "icon_class": "bi-archive-fill",
        "icon_bg": "#6c757d",
        "has_breadcrumb": True,
    },
    "fournisseurs.html": {
        "title": "Annuaire Fournisseurs",
        "subtitle": "Consultez les fournisseurs de l'établissement",
        "icon_class": "bi-truck",
        "icon_bg": "#0ba360",
        "has_breadcrumb": True,
    },
    "vue_jour.html": {
        "title": "Vue du Jour",
        "subtitle": "Réservations et disponibilités du jour",
        "icon_class": "bi-calendar-day-fill",
        "icon_bg": "#6f42c1",
        "has_breadcrumb": True,
    },
    "profil.html": {
        "title": "Mon Profil",
        "subtitle": "Gérez vos informations personnelles",
        "icon_class": "bi-person-circle",
        "icon_bg": "var(--couleur-principale)",
        "has_breadcrumb": True,
    },
    "documentation.html": {
        "title": "Documentation",
        "subtitle": "Guide d'utilisation de Scientral",
        "icon_class": "bi-book-fill",
        "icon_bg": "#0d6efd",
        "has_breadcrumb": True,
    },
    "a_propos.html": {
        "title": "À Propos",
        "subtitle": "Informations sur Scientral",
        "icon_class": "bi-info-circle-fill",
        "icon_bg": "var(--couleur-principale)",
        "has_breadcrumb": True,
    },
    "securite/index.html": {
        "title": "Sécurité & Maintenance",
        "subtitle": "Suivi de conformité des équipements",
        "icon_class": "bi-shield-check",
        "icon_bg": "#20c997",
        "has_breadcrumb": True,
    },
    "securite/details.html": {
        "title": "Détail Équipement",
        "subtitle": None,
        "icon_class": "bi-shield-fill",
        "icon_bg": "#20c997",
        "has_breadcrumb": True,
    },
}

# ─── Patterns à supprimer dans le block content ───────────────────────────────

# Blocs h1/h2 avec icône — pattern le plus courant dans les pages publiques
# On cherche le bloc d-flex avec h2/h1 mb-4 pb-3 border-bottom
HEADER_BLOCK_PATTERNS = [
    # Pattern 1 : d-flex justify-content-between ... border-bottom + h2
    re.compile(
        r"\n?[ \t]*{%[- ]* include '_breadcrumb\.html' [-%]*%}\n?"
        r".*?"                           # contenu variable
        r"(?=\n[ \t]*{%-?\s*(?:if|for|set|with|block|endif|endfor|endblock)|"
        r"\n[ \t]*<(?:div|section|main|ul|table|form))",
        re.DOTALL
    ),
]

# ─── Générateur de bloc macro ─────────────────────────────────────────────────

def build_macro_call(cfg, has_actions=False):
    """Génère l'appel à la macro page_header."""
    icon_part = f'\n         icon_class = "{cfg["icon_class"]}",' if cfg.get("icon_class") else ""
    icon_bg_part = f'\n         icon_bg    = "{cfg["icon_bg"]}",' if cfg.get("icon_bg") else ""
    subtitle_part = f'\n         subtitle   = "{cfg["subtitle"]}",' if cfg.get("subtitle") else ""
    bc_part = '\n         breadcrumbs= breadcrumbs,' if cfg.get("has_breadcrumb") else ""

    if has_actions:
        return (
            f'{{% from "_page_header.html" import page_header %}}\n'
            f'{{% call page_header(\n'
            f'     title      = "{cfg["title"]}",{subtitle_part}{icon_part}{icon_bg_part}{bc_part}\n'
            f') %}}\n'
            f'    {{% ACTIONS_PLACEHOLDER %}}\n'
            f'{{% endcall %}}'
        )
    else:
        return (
            f'{{% from "_page_header.html" import page_header %}}\n'
            f'{{{{ page_header(\n'
            f'     title      = "{cfg["title"]}",{subtitle_part}{icon_part}{icon_bg_part}{bc_part}\n'
            f') }}}}'
        )


# ─── Détection du bloc à remplacer ───────────────────────────────────────────

def find_header_block(content):
    """
    Trouve le bloc à remplacer dans le contenu du template.
    Retourne (start, end) ou None.
    """
    # Cherche {% include '_breadcrumb.html' %}
    bc_match = re.search(r'[ \t]*\{%-?\s*include [\'"]_breadcrumb\.html[\'"]\s*-?%\}', content)
    if not bc_match:
        return None

    start = bc_match.start()

    # Depuis le breadcrumb, cherche le premier bloc d-flex avec h1/h2 et border-bottom
    # On cherche la fin du bloc d-flex (fermeture de </div> correspondante)
    after_bc = content[bc_match.end():]

    # Pattern : bloc d-flex...border-bottom contenant h1 ou h2
    dflex_match = re.search(
        r'\n[ \t]*<div[^>]*class="[^"]*d-flex[^"]*justify-content-between[^"]*"[^>]*>',
        after_bc
    )

    if dflex_match:
        # Trouver la fermeture du div correspondant
        block_start = bc_match.end() + dflex_match.start()
        block_content = content[block_start:]

        depth = 0
        end_pos = 0
        for i, char in enumerate(block_content):
            if block_content[i:i+4] == '<div':
                depth += 1
            elif block_content[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end_pos = i + 6
                    break

        return (start, block_start + end_pos)

    # Fallback : juste le breadcrumb + la ligne suivante h1/h2
    h_match = re.search(r'\n[ \t]*<h[12][^>]*>.*?</h[12]>', after_bc, re.DOTALL)
    if h_match:
        return (start, bc_match.end() + h_match.end())

    # Dernier recours : juste le breadcrumb include
    return (start, bc_match.end())


# ─── Migration d'un fichier ───────────────────────────────────────────────────

def migrate_file(template_name, cfg):
    path = TEMPLATES_DIR / template_name

    if not path.exists():
        print(f"  ⚠  {template_name} — fichier introuvable, ignoré")
        return False

    content = path.read_text(encoding="utf-8")

    # Cas spécial : index.html (pas de breadcrumb include)
    if not cfg["has_breadcrumb"]:
        # Cherche le bloc h1 avec d-flex et border-bottom
        match = re.search(
            r'[ \t]*<div[^>]*class="[^"]*d-flex[^"]*justify-content-between[^"]*border-bottom[^"]*"[^>]*>.*?</div>\s*',
            content, re.DOTALL
        )
        if not match:
            # Essai simplifié : h1 avec d-flex
            match = re.search(
                r'[ \t]*<div[^>]*class="[^"]*d-flex[^"]*mb-[45][^"]*border-bottom[^"]*"[^>]*>.*?</div>\s*',
                content, re.DOTALL
            )

        macro_call = build_macro_call(cfg, has_actions=False)

        if match:
            new_content = content[:match.start()] + macro_call + "\n" + content[match.end():]
        else:
            print(f"  ⚠  {template_name} — bloc titre non trouvé, insertion manuelle requise")
            return False
    else:
        result = find_header_block(content)
        if not result:
            print(f"  ⚠  {template_name} — breadcrumb non trouvé, ignoré")
            return False

        start, end = result

        # Détecte si le bloc contenait un CTA (bouton d'action)
        removed_block = content[start:end]
        has_actions = bool(re.search(r'<button|<a[^>]+btn', removed_block))

        macro_call = build_macro_call(cfg, has_actions=has_actions)
        new_content = content[:start] + macro_call + "\n" + content[end:]

    if DRY_RUN:
        print(f"  [DRY-RUN] {template_name} — OK (has_actions={has_actions if cfg['has_breadcrumb'] else False})")
        return True

    # Backup
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / template_name.replace("/", "_")
    shutil.copy2(path, backup_path)

    path.write_text(new_content, encoding="utf-8")
    print(f"  ✓  {template_name} — migré (backup: {backup_path.name})")
    return True


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Migration Page Headers — {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"{'='*60}\n")

    ok = 0
    ko = 0

    for template_name, cfg in PAGES.items():
        result = migrate_file(template_name, cfg)
        if result:
            ok += 1
        else:
            ko += 1

    print(f"\n{'='*60}")
    print(f"  Résultat : {ok} migrés, {ko} à vérifier manuellement")
    print(f"{'='*60}")

    if not DRY_RUN:
        print(f"\n  Backups dans : {BACKUP_DIR}/")
        print(f"\n  RAPPEL — Étapes restantes :")
        print(f"  1. Vérifier les ACTIONS_PLACEHOLDER dans les templates migrés")
        print(f"  2. Ajouter le CSS _page_header.css dans components.css")
        print(f"  3. Supprimer l'ancien .page-hero de components.css")
        print(f"  4. Tester visuellement page par page\n")


if __name__ == "__main__":
    main()
