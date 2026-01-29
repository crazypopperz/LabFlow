# extensions.py
from flask_caching import Cache
from flask_limiter import Limiter
from flask_mail import Mail
from flask_limiter.util import get_remote_address

# Note : db est importé depuis db.py, on ne le redéfinit pas ici pour éviter les conflits.

cache = Cache()

# Initialisation de l'email (C'est ce dont on a besoin pour le mot de passe oublié)
mail = Mail()

# Configuration du Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"], 
    storage_uri="memory://", 
    strategy="fixed-window"
)