#!/usr/bin/env python3
"""
Script pour générer l'arborescence d'un projet Flask
Usage: python tree.py [chemin] [options]
"""

import os
import sys
from pathlib import Path

# Dossiers et fichiers à ignorer (typiques Flask/Python)
IGNORE_DIRS = {
    '__pycache__', '.git', '.venv', 'venv', 'env',
    'node_modules', '.pytest_cache', '.mypy_cache',
    'instance', 'build', 'dist', '*.egg-info'
}

IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', '.env', '.env.local',
    '*.pyc', '*.pyo', '*.log', '.gitignore'
}

def should_ignore(name, is_dir=False):
    """Vérifie si un fichier/dossier doit être ignoré."""
    if is_dir:
        return name in IGNORE_DIRS
    
    # Fichiers exacts
    if name in IGNORE_FILES:
        return True
    
    # Patterns (*.pyc, etc.)
    for pattern in IGNORE_FILES:
        if '*' in pattern:
            ext = pattern.replace('*', '')
            if name.endswith(ext):
                return True
    return False

def get_file_info(filepath):
    """Récupère des infos sur le fichier (taille, type)."""
    try:
        size = os.path.getsize(filepath)
        ext = os.path.splitext(filepath)[1]
        
        # Icônes selon type
        icons = {
            '.py': '🐍', '.html': '🌐', '.css': '🎨', 
            '.js': '⚡', '.json': '📋', '.md': '📝',
            '.sql': '🗄️', '.txt': '📄', '.pdf': '📕',
            '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️'
        }
        icon = icons.get(ext, '📄')
        
        # Conversion taille
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024**2:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/(1024**2):.1f}MB"
        
        return f"{icon} ({size_str})"
    except:
        return ""

def print_tree(directory, prefix="", show_size=True, max_depth=None, current_depth=0):
    """
    Affiche l'arborescence récursive.
    
    Args:
        directory: Chemin du dossier à scanner
        prefix: Préfixe pour l'indentation
        show_size: Afficher la taille des fichiers
        max_depth: Profondeur maximale (None = illimité)
        current_depth: Profondeur actuelle (usage interne)
    """
    if max_depth is not None and current_depth >= max_depth:
        return
    
    try:
        entries = sorted(os.listdir(directory))
    except PermissionError:
        print(f"{prefix}[Permission refusée]")
        return
    
    # Sépare dossiers et fichiers
    dirs = [e for e in entries if os.path.isdir(os.path.join(directory, e)) and not should_ignore(e, True)]
    files = [e for e in entries if os.path.isfile(os.path.join(directory, e)) and not should_ignore(e, False)]
    
    # Affiche les dossiers d'abord
    for i, d in enumerate(dirs):
        is_last_dir = (i == len(dirs) - 1) and len(files) == 0
        connector = "└── " if is_last_dir else "├── "
        print(f"{prefix}{connector}📁 {d}/")
        
        extension = "    " if is_last_dir else "│   "
        subdir_path = os.path.join(directory, d)
        print_tree(subdir_path, prefix + extension, show_size, max_depth, current_depth + 1)
    
    # Affiche les fichiers ensuite
    for i, f in enumerate(files):
        is_last = i == len(files) - 1
        connector = "└── " if is_last else "├── "
        
        filepath = os.path.join(directory, f)
        file_info = get_file_info(filepath) if show_size else ""
        print(f"{prefix}{connector}{f} {file_info}")

def count_stats(directory):
    """Compte le nombre de fichiers et dossiers."""
    total_files = 0
    total_dirs = 0
    total_size = 0
    
    for root, dirs, files in os.walk(directory):
        # Filtre les dossiers ignorés
        dirs[:] = [d for d in dirs if not should_ignore(d, True)]
        
        total_dirs += len(dirs)
        
        for f in files:
            if not should_ignore(f, False):
                total_files += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except:
                    pass
    
    return total_files, total_dirs, total_size

def save_to_file(directory, output_file="arborescence.txt", show_size=True, max_depth=None):
    """Sauvegarde l'arborescence dans un fichier."""
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        print(f"📂 Arborescence de : {os.path.abspath(directory)}")
        print("=" * 70)
        print()
        print_tree(directory, show_size=show_size, max_depth=max_depth)
        print()
        
        # Stats
        files, dirs, size = count_stats(directory)
        size_mb = size / (1024**2)
        print("=" * 70)
        print(f"📊 Statistiques :")
        print(f"   • Fichiers : {files}")
        print(f"   • Dossiers : {dirs}")
        print(f"   • Taille totale : {size_mb:.2f} MB")
    
    content = f.getvalue()
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(content)
    print(f"\n✅ Arborescence sauvegardée dans : {output_file}")

def main():
    """Point d'entrée principal."""
    # Arguments
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    
    # Options
    show_size = "--no-size" not in sys.argv
    save = "--save" in sys.argv
    max_depth = None
    
    # Profondeur max
    for arg in sys.argv:
        if arg.startswith("--depth="):
            try:
                max_depth = int(arg.split("=")[1])
            except:
                pass
    
    # Vérification
    if not os.path.exists(directory):
        print(f"❌ Erreur : Le chemin '{directory}' n'existe pas.")
        sys.exit(1)
    
    if not os.path.isdir(directory):
        print(f"❌ Erreur : '{directory}' n'est pas un dossier.")
        sys.exit(1)
    
    print(f"📂 Arborescence de : {os.path.abspath(directory)}")
    print("=" * 70)
    print()
    
    if save:
        save_to_file(directory, show_size=show_size, max_depth=max_depth)
    else:
        print_tree(directory, show_size=show_size, max_depth=max_depth)
        print()
        
        # Stats finales
        files, dirs, size = count_stats(directory)
        size_mb = size / (1024**2)
        print("=" * 70)
        print(f"📊 Statistiques :")
        print(f"   • Fichiers : {files}")
        print(f"   • Dossiers : {dirs}")
        print(f"   • Taille totale : {size_mb:.2f} MB")
        print()
        print("💡 Usage :")
        print("   python tree.py [chemin] [options]")
        print("   Options :")
        print("     --save         : Sauvegarde dans arborescence.txt")
        print("     --no-size      : Masque les tailles de fichiers")
        print("     --depth=N      : Limite la profondeur à N niveaux")
        print()
        print("   Exemple : python tree.py . --save --depth=3")

if __name__ == "__main__":
    main()