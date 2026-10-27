from pathlib import Path
from extensions import db
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.recovery_service import RecoveryService


def test_recovery_stale_jobs_with_existing_output(app, tmp_path):
    with app.app_context():
        item = MediaItem(source_id="rec_item_1", title="Recovery Item 1")
        db.session.add(item)
        db.session.commit()

        # Create an actual test output file
        dummy_file = tmp_path / "finished_lecture.sim.txt"
        dummy_file.write_text("Completed data")

        job = DownloadJob(
            media_item_id=item.id,
            status=DownloadJob.STATUS_DOWNLOADING,
            output_path=str(dummy_file),
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    # Run recovery
    result = RecoveryService.recover_stale_jobs(app)
    assert result["preserved_as_completed"] == 1

    with app.app_context():
        recovered = db.session.get(DownloadJob, job_id)
        assert recovered.status == DownloadJob.STATUS_COMPLETED


def test_recovery_stale_jobs_without_output(app):
    with app.app_context():
        item = MediaItem(source_id="rec_item_2", title="Recovery Item 2")
        db.session.add(item)
        db.session.commit()

        job = DownloadJob(
            media_item_id=item.id,
            status=DownloadJob.STATUS_DOWNLOADING,
            output_path="non_existent_file.sim.txt",
            retry_count=0,
            max_retries=3,
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    # With AUTO_RETRY enabled in config, it should requeue
    result = RecoveryService.recover_stale_jobs(app)
    assert result["requeued_for_work"] == 1

    with app.app_context():
        recovered = db.session.get(DownloadJob, job_id)
        assert recovered.status == DownloadJob.STATUS_QUEUED
        assert recovered.retry_count == 1
