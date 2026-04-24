"""
fix_breadcrumbs.py
Harmonise tous les breadcrumbs du projet LabFlow vers le format :
  Tableau de Bord → Administration → Page  (pages admin)
  Tableau de Bord → Page                   (pages non-admin)
"""

import re
from pathlib import Path

# ── Adapte ce chemin à ton environnement ──────────────────────────────────────
BASE = Path("E:/Xav-Projets/labflow/views")
# ─────────────────────────────────────────────────────────────────────────────

TABLEAU_DE_BORD = "{'text': 'Tableau de Bord', 'url': url_for('inventaire.index')}"
ADMINISTRATION  = "{'text': 'Administration', 'url': url_for('admin.admin')}"

replacements = {

    # ── admin.py ──────────────────────────────────────────────────────────────

    "admin.py": [

        # L.1563 — Utilisateurs
        (
            "[{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Utilisateurs'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Utilisateurs', 'url': None}}
    ]"""
        ),

        # L.1759 — Kits
        (
            "[{'text': 'Administration', 'url': url_for('admin.admin')}, {'text': 'Kits'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Kits', 'url': None}}
    ]"""
        ),

        # L.1886 — Kit modifier (3 niveaux → 4)
        (
            """[
        {'text': 'Admin', 'url': url_for('admin.admin')},
        {'text': 'Kits', 'url': url_for('admin.gestion_kits')},
        {'text': kit.nom}
    ]""",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Kits', 'url': url_for('admin.gestion_kits')}},
        {{'text': kit.nom, 'url': None}}
    ]"""
        ),

        # L.1943 — Échéances
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Échéances'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Échéances', 'url': None}}
    ]"""
        ),

        # L.2056 — Budget
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Budget'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Budget', 'url': None}}
    ]"""
        ),

        # L.2394 — Fournisseurs
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Fournisseurs'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Fournisseurs', 'url': None}}
    ]"""
        ),

        # L.2556 — Sauvegardes
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Sauvegardes'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Sauvegardes', 'url': None}}
    ]"""
        ),

        # L.2724 — Import
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Import'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Import', 'url': None}}
    ]"""
        ),

        # L.3051 — Historique Complet
        (
            """[
        {'text': 'Admin', 'url': url_for('admin.admin')},
        {'text': 'Historique Complet'}
    ]""",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Historique Complet', 'url': None}}
    ]"""
        ),
    ],

    # ── admin_documents.py ────────────────────────────────────────────────────

    "admin_documents.py": [
        (
            "[{'text': 'Admin', 'url': url_for('admin.admin')}, {'text': 'Documents & Conformité'}]",
            f"""[
        {TABLEAU_DE_BORD},
        {ADMINISTRATION},
        {{'text': 'Documents & Conformité', 'url': None}}
    ]"""
        ),
    ],

    # ── main.py ───────────────────────────────────────────────────────────────

    "main.py": [
        (
            "{'text': 'Accueil', 'url': url_for('inventaire.index')}",
            "{'text': 'Tableau de Bord', 'url': url_for('inventaire.index')}"
        ),
    ],
}


def apply_replacements(file_path: Path, changes: list[tuple[str, str]]) -> int:
    text = file_path.read_text(encoding="utf-8")
    count = 0
    for old, new in changes:
        if old in text:
            text = text.replace(old, new)
            count += 1
        else:
            print(f"  ⚠️  Pattern non trouvé dans {file_path.name} :\n     {old[:80]}…")
    file_path.write_text(text, encoding="utf-8")
    return count


def main():
    total = 0
    for filename, changes in replacements.items():
        path = BASE / filename
        if not path.exists():
            print(f"❌ Fichier introuvable : {path}")
            continue
        n = apply_replacements(path, changes)
        print(f"✅ {filename} — {n}/{len(changes)} remplacement(s) effectué(s)")
        total += n
    print(f"\n🎉 Total : {total} remplacement(s) appliqué(s)")


if __name__ == "__main__":
    main()