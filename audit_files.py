import os

# Liste des fichiers connus et valides (chemins relatifs)
WHITELIST = {
    # Racine
    "app.py", "db.py", "extensions.py", "utils.py", "config.py", "reset_db.py", ".env", "requirements.txt", "audit_files.py",
    
    # Views
    "views/__init__.py", "views/auth.py", "views/main.py", "views/inventaire.py", "views/admin.py", "views/api.py",
    
    # Services
    "services/__init__.py", "services/stock_service.py", "services/kit_service.py", "services/panier_service.py", "services/inventory_service.py",
    
    # Static JS
    "static/js/script.js",
    "static/js/modules/booking-modal.js", "static/js/modules/calendar-monthly.js", "static/js/modules/calendar-daily.js",
    "static/js/modules/cart-summary.js", "static/js/modules/cart-utils.js", "static/js/modules/toast.js", "static/js/modules/tour.js",
    
    # Static CSS
    "static/css/style.css",
    
    # Templates Base
    "templates/base.html", "templates/header.html", "templates/footer.html", "templates/sub_header.html",
    "templates/_breadcrumb.html", "templates/_pagination.html", "templates/_modals.html", "templates/_inventaire_content.html",
    
    # Templates Pages
    "templates/index.html", "templates/login.html", "templates/register.html", "templates/setup.html", "templates/profil.html",
    "templates/inventaire.html", "templates/objet_details.html", "templates/armoire.html", "templates/categorie.html", "templates/fournisseurs.html",
    "templates/calendrier.html", "templates/vue_jour.html", "templates/panier.html", "templates/alertes.html", "templates/budget.html",
    "templates/a_propos.html", "templates/legal.html", "templates/documentation.html",
    
    # Templates Admin
    "templates/admin.html", "templates/admin_utilisateurs.html", "templates/admin_kits.html", "templates/admin_kit_modifier.html",
    "templates/admin_echeances.html", "templates/admin_import.html", "templates/admin_backup.html", "templates/rapports.html",
    
    # Templates Erreurs
    "templates/errors/404.html", "templates/errors/500.html", "templates/errors/429.html",
    
    # Modales séparées (si tu as choisi l'option fichiers séparés)
    "templates/_modale_fournisseur_add.html", "templates/_modale_fournisseur_edit.html",
    "templates/_modale_budget_config.html", "templates/_modale_depense_add.html", "templates/_modale_depense_edit.html",
    "templates/_modale_danger.html", "templates/_modale_suggestion.html"
}

# Dossiers à ignorer complètement
IGNORE_DIRS = {".git", "__pycache__", "venv", "env", "instance", "logs", "static/uploads", "static/icons", "static/images", ".idea", ".vscode"}

def audit():
    print("🔍 AUDIT DES FICHIERS EN COURS...\n")
    root_dir = os.getcwd()
    ghost_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filtrer les dossiers ignorés
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            
            # Ignorer les fichiers compilés Python
            if filename.endswith(".pyc"): continue
            
            if rel_path not in WHITELIST:
                ghost_files.append(rel_path)

    if ghost_files:
        print(f"⚠️  {len(ghost_files)} FICHIERS SUSPECTS DÉTECTÉS :\n")
        for f in sorted(ghost_files):
            print(f"  [?] {f}")
        print("\n👉 Vérifie cette liste. Si un fichier est important, ajoute-le à la WHITELIST.")
        print("👉 Sinon, déplace-les dans un dossier '_TRASH' pour tester.")
    else:
        print("✅ Aucun fichier suspect trouvé. Ton projet est propre !")

if __name__ == "__main__":
    audit()