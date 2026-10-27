from app.routes.dashboard import dashboard_bp
from app.routes.playlists import playlists_bp
from app.routes.queue import queue_bp
from app.routes.history import history_bp
from app.routes.settings import settings_bp
from app.routes.api import api_bp
from app.routes.auth import auth_bp, init_oauth

__all__ = [
    "dashboard_bp",
    "playlists_bp",
    "queue_bp",
    "history_bp",
    "settings_bp",
    "api_bp",
    "auth_bp",
    "init_oauth",
]

