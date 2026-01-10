import os

# Liste des dossiers à ignorer pour ne pas polluer le prompt
IGNORE_DIRS = {
    '.git', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'instance', 'migrations', 'static/uploads'
}

# Liste des fichiers à ignorer
IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', 'generate_structure.py', 
    'update_db.py', 'reset_db.py', 'audit_files.py', 'simulate_dormant.py'
}

def generate_tree(startpath):
    tree_str = "### 📂 STRUCTURE RÉELLE DU PROJET\n/\n"
    
    for root, dirs, files in os.walk(startpath):
        # Filtrage des dossiers in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * (level)
        
        # On n'affiche pas la racine '.'
        if root != startpath:
            folder_name = os.path.basename(root)
            tree_str += f"{indent}├── 📂 {folder_name}/\n"
            sub_indent = '│   ' * (level + 1)
        else:
            sub_indent = '│   '

        for f in sorted(files):
            if f not in IGNORE_FILES and not f.endswith('.pyc'):
                tree_str += f"{sub_indent}├── {f}\n"
                
    return tree_str

if __name__ == "__main__":
    try:
        # Génère l'arborescence depuis le dossier courant
        structure = generate_tree(os.getcwd())
        
        # Affiche dans la console
        print(structure)
        
        # Sauvegarde dans un fichier texte pour copier-coller facile
        with open("structure_projet.txt", "w", encoding="utf-8") as f:
            f.write(structure)
            
        print("\n✅ L'arborescence a été générée dans 'structure_projet.txt' !")
        print("👉 Ouvre ce fichier et copie tout son contenu pour le donner à l'IA.")
        
    except Exception as e:
        print(f"Erreur : {e}")