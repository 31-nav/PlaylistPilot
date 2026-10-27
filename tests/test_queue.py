from extensions import db
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.queue_service import QueueService


def test_enqueue_duplicate_prevention(app, sample_playlist):
    with app.app_context():
        items = MediaItem.query.filter_by(playlist_id=sample_playlist.id).limit(5).all()
        ids = [it.id for it in items]

        # First enqueue
        res1 = QueueService.enqueue_items(ids)
        assert res1["added_count"] == 5
        assert res1["skipped_count"] == 0

        # Attempt to re-enqueue identical items while pending
        res2 = QueueService.enqueue_items(ids)
        assert res2["added_count"] == 0
        assert res2["skipped_count"] == 5


def test_urgent_priority_ordering(app, sample_playlist):
    with app.app_context():
        items = MediaItem.query.filter_by(playlist_id=sample_playlist.id).limit(3).all()
        ids = [it.id for it in items]

        res = QueueService.enqueue_items(ids)
        job_ids = res["job_ids"]

        # Initially, jobs are ordered FIFO
        waiting = QueueService.get_waiting_queue()
        assert waiting[0].id == job_ids[0]

        # Prioritize the 3rd job
        target_job_id = job_ids[2]
        pri_res = QueueService.prioritize_job(target_job_id)
        assert pri_res["success"] is True

        # Now target_job_id should be first in waiting queue!
        updated_waiting = QueueService.get_waiting_queue()
        assert updated_waiting[0].id == target_job_id
        assert updated_waiting[0].priority > updated_waiting[1].priority


def test_cancel_and_retry(app, sample_playlist):
    with app.app_context():
        item = MediaItem.query.first()
        res = QueueService.enqueue_items([item.id])
        job_id = res["job_ids"][0]

        # Cancel queued job
        cancel_res = QueueService.cancel_job(job_id)
        assert cancel_res["success"] is True
        assert cancel_res["status"] == "cancelled"

        job = db.session.get(DownloadJob, job_id)
        assert job.status == DownloadJob.STATUS_CANCELLED

        # Re-queue / Retry
        retry_res = QueueService.retry_job(job_id)
        assert retry_res["success"] is True
        assert db.session.get(DownloadJob, job_id).status == DownloadJob.STATUS_QUEUED
