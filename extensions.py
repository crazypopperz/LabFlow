from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# On initialise les extensions sans les lier à l'application tout de suite
# (Elles seront liées dans app.py via la fonction init_app)

# 1. Limiter (Protection contre les requêtes abusives)
limiter = Limiter(key_func=get_remote_address)

# 2. Cache (Pour accélérer certaines pages)
cache = Cache()