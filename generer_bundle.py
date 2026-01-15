import os

# Configuration
OUTPUT_FILE = "code_bundle_complet.txt"
EXTENSIONS_A_INCLURE = {'.py', '.html', '.css', '.js', '.txt', '.md'}
DOSSIERS_A_IGNORER = {'venv', '__pycache__', '.git', '.idea', 'instance', 'uploads', 'images', 'icons'}
FICHIERS_A_IGNORER = {'generer_bundle.py', 'reset_db.py', 'package-lock.json'}

def est_fichier_pertinent(filename):
    return any(filename.endswith(ext) for ext in EXTENSIONS_A_INCLURE) and filename not in FICHIERS_A_IGNORER

def generer_bundle():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write("=== CONTEXTE COMPLET DU PROJET LABFLOW ===\n\n")
        
        for root, dirs, files in os.walk("."):
            # Filtrer les dossiers ignorés
            dirs[:] = [d for d in dirs if d not in DOSSIERS_A_IGNORER]
            
            for file in files:
                if est_fichier_pertinent(file):
                    path = os.path.join(root, file)
                    # Chemin relatif propre
                    rel_path = os.path.relpath(path, ".")
                    
                    try:
                        with open(path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                        # Formatage clair pour l'IA
                        outfile.write(f"\n{'='*50}\n")
                        outfile.write(f"FICHIER : {rel_path}\n")
                        outfile.write(f"{'='*50}\n")
                        outfile.write(content + "\n")
                        print(f"Ajouté : {rel_path}")
                        
                    except Exception as e:
                        print(f"Erreur lecture {rel_path}: {e}")

    print(f"\n✅ Terminé ! Tout le code est dans : {OUTPUT_FILE}")

if __name__ == "__main__":
    generer_bundle()