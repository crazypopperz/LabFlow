ITEMS_PER_PAGE = 10

# --- CONFIGURATION EMAIL (FLASK-MAIL) ---
import os

# En local, on peut laisser des valeurs par défaut, mais pour le mot de passe
# on force la récupération via os.environ pour la sécurité.
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'

# Ces deux-là doivent impérativement être définis sur Render
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)