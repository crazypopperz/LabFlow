# Gestion Matériel Labo Collège et Lycée (GMLCL)

**Version 1.0**

![Logo de l'application](https://raw.githubusercontent.com/crazypopperz/GestionLabo/main/static/logo.png)

## Description

GMLCL est une application web de gestion d'inventaire conçue spécifiquement pour les laboratoires de sciences. Elle permet de suivre le stock de matériel, de gérer les réservations, de suivre un budget et de recevoir des alertes automatiques.

Construite avec Flask, elle fonctionne comme un serveur local accessible sur le réseau de l'établissement, sans nécessiter de connexion internet. Sa base de données SQLite la rend entièrement autonome et facile à déployer via un simple exécutable.

### Modèle Freemium
- **Version Gratuite :** Accès à toutes les fonctionnalités, mais l'inventaire est limité à 50 objets uniques.
- **Version Pro :** Débloque un nombre illimité d'objets et la fonctionnalité de sauvegarde de la base de données.

## Technologies Utilisées

- **Backend :** Python 3, Flask, Waitress (serveur de production)
- **Base de Données :** SQLite 3
- **Frontend :** HTML5, CSS3, JavaScript
- **Packaging :** PyInstaller

## Installation (pour les développeurs)

Ce guide est destiné à la mise en place d'un environnement de développement. Pour une utilisation finale, veuillez utiliser l'exécutable fourni (`GestionLabo.exe`).

1.  **Cloner le projet :**
    ```bash
    git clone https://github.com/crazypopperz/GestionLabo.git
    cd GestionLabo
    ```

2.  **Créer et activer un environnement virtuel :**
    ```bash
    # Créer l'environnement
    python -m venv venv
    # Activer sur Windows
    venv\Scripts\activate
    # Activer sur macOS/Linux
    source venv/bin/activate
    ```

3.  **Installer les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

## Lancement de l'application

### En Mode Développement
Ce mode active le débogage et le rechargement automatique. Lancez l'application avec la commande suivante. Elle sera accessible à `http://127.0.0.1:5000`.
```bash
python run.py
```

### En Mode Production (via l'exécutable)
Double-cliquez sur le fichier `GestionLabo.exe`. Une console s'ouvrira, affichant les adresses de connexion pour l'administrateur et pour les autres utilisateurs du réseau.

## Création de l'Exécutable (Packaging)

L'application est configurée pour être compilée avec PyInstaller en utilisant un fichier de spécification (`.spec`) pour plus de fiabilité.

1.  **Installer les outils nécessaires :**
    ```bash
    pip install pyinstaller waitress
    ```

2.  **Lancer la compilation :**
    La configuration est entièrement gérée par le fichier `run.spec`. Exécutez simplement :
    ```bash
    pyinstaller run.spec
    ```

3.  L'exécutable final et ses dépendances se trouveront dans le dossier `dist/GestionLabo`.

## Structure du Projet

```
.
├── instance/
│   └── gestionlabo.db  # Base de données (créée au premier lancement)
├── static/             # Fichiers CSS, JS, images
├── templates/          # Templates HTML Jinja2
├── views/              # Blueprints Flask (logique des routes)
│   ├── admin.py
│   ├── auth.py
│   └── ...
├── app.py              # Factory de l'application Flask
├── config.py           # Configuration statique
├── db.py               # Initialisation de la base de données
├── run.py              # Lanceur pour le DÉVELOPPEMENT
├── run_production.py   # Lanceur pour la PRODUCTION (utilisé par PyInstaller)
├── run.spec            # Fichier de configuration pour PyInstaller
├── requirements.txt    # Dépendances Python
└── README.md           # Ce fichier
```

## Auteurs et Licence

- **Auteurs :** Yll Basha & Xavier De Baudry d'Asson
- **Licence :** [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)