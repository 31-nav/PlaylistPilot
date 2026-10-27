import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from extensions import db
from app.models.playlist import Playlist
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.playlist_service import PlaylistService
from app.services.worker_service import WorkerService


class SamplePlaylistRef:
    def __init__(self, id, title):
        self.id = id
        self.title = title


@pytest.fixture(scope="session")
def app():
    """Create Flask application in testing configuration."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    # Clean up test database file if exists
    test_db = Path(app.config["TEST_DB_PATH"])
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Ensure database is clean and worker is stopped before each test."""
    # Ensure worker stopped
    worker = WorkerService.get_instance(app)
    worker.stop(timeout=1.0)
    worker.simulated_network_offline = False
    worker.simulate_next_job_failure = False
    worker.simulate_failure_job_id = None

    with app.app_context():
        DownloadJob.query.delete()
        MediaItem.query.delete()
        Playlist.query.delete()
        db.session.commit()
    yield
    # Stop worker again after test
    worker.stop(timeout=1.0)


@pytest.fixture
def sample_playlist(app):
    """Seed and return a detached-safe reference to the demo playlist."""
    with app.app_context():
        pl = PlaylistService.seed_demo_playlist(force=True)
        return SamplePlaylistRef(pl.id, pl.title)
