# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
cache = Cache()

# Configuration du Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"], # Limites globales larges
    storage_uri="memory://", # Stockage en mémoire (suffisant pour une instance unique)
    strategy="fixed-window"
)