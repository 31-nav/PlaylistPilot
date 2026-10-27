from extensions import db
from app.models.playlist import Playlist
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.playlist_service import PlaylistService


def test_seed_demo_playlist(app):
    with app.app_context():
        pl = PlaylistService.seed_demo_playlist(force=True)
        assert pl is not None
        assert pl.item_count == 105
        assert MediaItem.query.filter_by(playlist_id=pl.id).count() == 105


def test_playlist_pagination_and_search(app, sample_playlist):
    with app.app_context():
        # Test pagination: page 1 of 25
        items, total, pages = PlaylistService.get_playlist_items(
            sample_playlist.id, page=1, per_page=25
        )
        assert len(items) == 25
        assert total == 105
        assert pages == 5

        # Test search
        searched, s_total, _ = PlaylistService.get_playlist_items(
            sample_playlist.id, search="Algorithms"
        )
        assert s_total > 0
        for it in searched:
            assert "Algorithms" in it.title or "Algorithms" in it.metadata_json


def test_safe_playlist_deletion(app, sample_playlist):
    with app.app_context():
        # Create a job tied to an item
        item = MediaItem.query.filter_by(playlist_id=sample_playlist.id).first()
        job = DownloadJob(media_item_id=item.id, status=DownloadJob.STATUS_COMPLETED)
        db.session.add(job)
        db.session.commit()
        job_id = job.id

        # Delete playlist metadata safely
        deleted = PlaylistService.delete_playlist(sample_playlist.id)
        assert deleted is True

        # Verify playlist is removed
        assert db.session.get(Playlist, sample_playlist.id) is None

        # Verify item and job still exist (dissociated safely)
        preserved_job = db.session.get(DownloadJob, job_id)
        assert preserved_job is not None
        assert preserved_job.status == DownloadJob.STATUS_COMPLETED
