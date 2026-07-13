"""
Extensions Flask partagées entre app.py (qui les initialise avec `init_app`) et
les Blueprints de routes/ (qui les utilisent, ex: `@limiter.limit(...)`).
Séparé de app.py pour éviter un import circulaire avec routes/.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
