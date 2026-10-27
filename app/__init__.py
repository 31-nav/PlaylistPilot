import os
import logging
from flask import Flask, render_template, jsonify, request
from config import config_by_name, BASE_DIR
from extensions import db
from app.routes import (
    dashboard_bp,
    playlists_bp,
    queue_bp,
    history_bp,
    settings_bp,
    api_bp,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("playlistpilot")


def create_app(config_name="default"):
    """Application factory for PlaylistPilot."""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if r"C:\Program Files" not in os.environ.get("PATH", ""):
        os.environ["PATH"] = r"C:\Program Files;" + os.environ.get("PATH", "")

    app = Flask(__name__)
    
    # Load configuration
    cfg_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg_class)

    # Ensure required directories exist
    instance_dir = BASE_DIR / "instance"
    instance_dir.mkdir(parents=True, exist_ok=True)
    
    download_dir = app.config.get("DOWNLOAD_DIR", BASE_DIR / "downloads")
    download_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    
    # Initialize Google OAuth
    from app.routes.auth import auth_bp, init_oauth
    init_oauth(app)

    # Register Blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # User Context Processor for Templates
    @app.context_processor
    def inject_current_user():
        from flask import session
        user_data = None
        if "user_id" in session:
            user_data = {
                "id": session.get("user_id"),
                "email": session.get("user_email"),
                "name": session.get("user_name"),
                "avatar_url": session.get("user_avatar"),
            }
        return {"current_user": user_data}

    # Register Error Handlers
    @app.errorhandler(404)
    def handle_404(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Requested resource not found", "status_code": 404}), 404
        return render_template("errors/404.html", active_page=None), 404

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Internal server error: {e}", exc_info=True)
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Internal server error occurred", "status_code": 500}), 500
        return render_template("errors/500.html", active_page=None), 500

    @app.errorhandler(503)
    def handle_530(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"success": False, "error": "Service temporarily unavailable", "status_code": 503}), 503
        return render_template("errors/503.html", active_page=None), 503

    # Post-initialization tasks
    with app.app_context():
        # Initialize database tables
        db.create_all()

        # Automatic SQLite column migration if needed
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                if "sqlite" in str(db.engine.url):
                    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(download_jobs)")).fetchall()]
                    if cols and "user_id" not in cols:
                        conn.execute(text("ALTER TABLE download_jobs ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                        conn.commit()
                    p_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(playlists)")).fetchall()]
                    if p_cols and "user_id" not in p_cols:
                        conn.execute(text("ALTER TABLE playlists ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                        conn.commit()
        except Exception as mig_err:
            logger.debug(f"SQLite migration check notice: {mig_err}")

        # Seed initial demo playlist if database is empty
        if not app.config.get("TESTING", False):
            from app.models.playlist import Playlist
            from app.services.playlist_service import PlaylistService
            from app.services.recovery_service import RecoveryService
            from app.services.worker_service import WorkerService

            try:
                # Startup Crash Recovery: Check for orphaned or interrupted jobs
                RecoveryService.recover_stale_jobs(app)

                # Start the background worker thread
                worker = WorkerService.get_instance(app)
                worker.start()
            except Exception as e:
                logger.error(f"Error during app startup initialization: {e}", exc_info=True)

    return app
