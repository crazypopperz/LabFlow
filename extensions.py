# Fichier : extensions.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import os

# Rate Limiter
# On initialise sans 'app', on le fera dans app.py avec init_app
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    default_limits=["2000 per day", "500 per hour"]
)

# Cache
# CORRECTION : On ne met pas la config ici, on initialise juste l'objet
cache = Cache()