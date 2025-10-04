import os

# --- Configuration ---
START_PATH = '.'
OUTPUT_FILE = 'code_bundle_complet.txt'

# Extensions de fichiers à inclure
INCLUDE_EXTENSIONS = [
    '.py', '.js', '.css', '.html', '.txt', '.md', '.sql'
]

# Éléments à ignorer
IGNORE_DIRS = [
    '__pycache__', '.git', '.vscode', 'venv', '.venv', 
    'node_modules', 'dist', 'build'
]
IGNORE_FILES = [
    'export_full_code.py', 'show_full_tree.py', 'code_bundle_complet.txt', 
    'arborescence_complete.txt', '.gitignore'
]
# --- Fin de la configuration ---

def generate_bundle(startpath, output_file):
    """Parcourt le projet et concatène le contenu des fichiers texte dans un seul fichier."""
    print(f"Création du bundle de code complet dans '{output_file}'...")
    
    try:
        with open(output_file, 'w', encoding='utf-8', errors='ignore') as bundle:
            for root, dirs, files in os.walk(startpath, topdown=True):
                dirs[:] = sorted([d for d in dirs if d not in IGNORE_DIRS])
                
                files_to_process = sorted([
                    f for f in files 
                    if f not in IGNORE_FILES and any(f.endswith(ext) for ext in INCLUDE_EXTENSIONS)
                ])

                if not files_to_process:
                    continue

                for f in files_to_process:
                    file_path = os.path.join(root, f)
                    relative_path = os.path.relpath(file_path, startpath).replace(os.sep, '/')
                    
                    bundle.write(f"\n--- START OF FILE {relative_path} ---\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as source_file:
                            bundle.write(source_file.read())
                    except Exception as e:
                        bundle.write(f"!!! ERREUR DE LECTURE: {e} !!!\n")
                    
                    bundle.write(f"\n--- END OF FILE {relative_path} ---\n")

        print(f"Bundle '{output_file}' créé avec succès.")
        print("Tu peux maintenant copier-coller le contenu de ce fichier.")

    except Exception as e:
        print(f"Une erreur est survenue lors de la création du bundle : {e}")

if __name__ == '__main__':
    generate_bundle(START_PATH, OUTPUT_FILE)