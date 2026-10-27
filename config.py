import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-playlistpilot-2026")
    
    # Database (Supabase PostgreSQL / SQLite fallback)
    raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'playlistpilot.db').as_posix()}")
    if raw_db_url.startswith("sqlite:///instance/"):
        rel_path = raw_db_url[len("sqlite:///instance/"):]
        raw_db_url = f"sqlite:///{(BASE_DIR / 'instance' / rel_path).as_posix()}"
    elif raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    } if not raw_db_url.startswith("sqlite") else {}

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Download & Storage
    DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIRECTORY", "downloads")
    MIN_FREE_SPACE_MB = int(os.getenv("MIN_FREE_SPACE_MB", "200"))

    # Queue & Worker Settings
    AUTO_RETRY = os.getenv("AUTO_RETRY", "true").lower() in ("true", "1", "yes")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    QUEUE_POLL_INTERVAL = float(os.getenv("QUEUE_POLL_INTERVAL", "2.0"))
    DEFAULT_QUALITY = os.getenv("DEFAULT_QUALITY", "best")

    # Integrations
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")

    # App Environment
    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    TEST_DB_PATH = BASE_DIR / "instance" / "test_playlistpilot.db"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_PATH.as_posix()}"
    DOWNLOAD_DIR = BASE_DIR / "tests" / "test_downloads"
    QUEUE_POLL_INTERVAL = 0.1
    SIMULATION_SPEED = 20.0  # Ultra-fast simulation for automated tests


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
