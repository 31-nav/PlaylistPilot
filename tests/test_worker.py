import time
from extensions import db
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.queue_service import QueueService
from app.services.worker_service import WorkerService


def test_worker_duplicate_prevention(app):
    worker = WorkerService.get_instance(app)
    started1 = worker.start()
    # Attempting to start again should return False
    started2 = worker.start()
    assert started2 is False
    worker.stop(timeout=1.0)


def test_worker_process_single_job(app, sample_playlist):
    worker = WorkerService.get_instance(app)
    
    with app.app_context():
        item = MediaItem.query.first()
        res = QueueService.enqueue_items([item.id])
        job_id = res["job_ids"][0]

    worker.start()

    # Wait for completion (simulation speed in test config is 10x)
    completed = False
    for _ in range(30):
        time.sleep(0.15)
        with app.app_context():
            job = db.session.get(DownloadJob, job_id)
            if job and job.status == DownloadJob.STATUS_COMPLETED:
                completed = True
                assert job.progress_percent == 100.0
                assert job.output_path is not None
                break

    worker.stop(timeout=1.0)
    assert completed is True


def test_worker_simulation_failure_and_retry(app, sample_playlist):
    worker = WorkerService.get_instance(app)
    
    with app.app_context():
        item = MediaItem.query.first()
        res = QueueService.enqueue_items([item.id])
        job_id = res["job_ids"][0]
        # Inject simulated failure
        worker.simulate_failure_job_id = job_id

    worker.start()

    failed = False
    for _ in range(30):
        time.sleep(0.15)
        with app.app_context():
            job = db.session.get(DownloadJob, job_id)
            if job and job.status == DownloadJob.STATUS_FAILED:
                failed = True
                assert "DEMO failure simulation" in (job.error_message or "")
                break

    worker.stop(timeout=1.0)
    assert failed is True
