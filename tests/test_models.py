from extensions import db
from app.models.playlist import Playlist
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob


def test_playlist_creation(app):
    with app.app_context():
        pl = Playlist(
            title="Advanced Algorithms",
            source_type="demo",
            source_id="ALG_101",
            item_count=10,
        )
        db.session.add(pl)
        db.session.commit()

        retrieved = Playlist.query.filter_by(source_id="ALG_101").first()
        assert retrieved is not None
        assert retrieved.title == "Advanced Algorithms"
        assert retrieved.to_dict()["item_count"] == 10


def test_media_item_formatted_duration(app):
    with app.app_context():
        item = MediaItem(
            source_id="vid_123",
            title="Tree Traversals",
            duration_seconds=754,  # 12 mins 34 secs
        )
        assert item.formatted_duration == "12:34"

        item2 = MediaItem(
            source_id="vid_456",
            title="Comprehensive Lecture",
            duration_seconds=3665,  # 1 hr 1 min 5 secs
        )
        assert item2.formatted_duration == "1:01:05"


def test_download_job_transitions(app):
    with app.app_context():
        item = MediaItem(source_id="test_vid", title="Test Video")
        db.session.add(item)
        db.session.commit()

        job = DownloadJob(media_item_id=item.id, status=DownloadJob.STATUS_QUEUED)
        db.session.add(job)
        db.session.commit()

        # Valid transition: queued -> downloading
        assert job.can_transition_to(DownloadJob.STATUS_DOWNLOADING) is True
        assert job.transition_to(DownloadJob.STATUS_DOWNLOADING) is True
        assert job.status == DownloadJob.STATUS_DOWNLOADING
        assert job.started_at is not None

        # Invalid transition: downloading -> queued directly
        assert job.can_transition_to(DownloadJob.STATUS_QUEUED) is False
        assert job.transition_to(DownloadJob.STATUS_QUEUED) is False
        assert job.status == DownloadJob.STATUS_DOWNLOADING

        # Valid transition: downloading -> paused
        assert job.transition_to(DownloadJob.STATUS_PAUSED) is True
        assert job.status == DownloadJob.STATUS_PAUSED

        # Valid transition: paused -> queued
        assert job.transition_to(DownloadJob.STATUS_QUEUED) is True
        assert job.status == DownloadJob.STATUS_QUEUED


def test_job_retryable_logic(app):
    with app.app_context():
        item = MediaItem(source_id="retry_test", title="Retry Item")
        db.session.add(item)
        db.session.commit()

        job = DownloadJob(
            media_item_id=item.id,
            status=DownloadJob.STATUS_FAILED,
            retry_count=1,
            max_retries=3,
        )
        assert job.is_retryable is True

        job.retry_count = 3
        assert job.is_retryable is False
