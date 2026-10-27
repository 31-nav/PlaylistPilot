from flask import Blueprint, render_template
from app.models.download_job import DownloadJob
from app.services.queue_service import QueueService

queue_bp = Blueprint("queue", __name__, url_prefix="/queue")


@queue_bp.route("")
def index():
    status = QueueService.get_queue_status()
    waiting_jobs = (
        DownloadJob.query.filter_by(status=DownloadJob.STATUS_QUEUED)
        .order_by(DownloadJob.priority.desc(), DownloadJob.created_at.asc())
        .limit(100)
        .all()
    )
    active_job = (
        DownloadJob.query.filter_by(status=DownloadJob.STATUS_DOWNLOADING)
        .order_by(DownloadJob.started_at.desc())
        .first()
    )

    return render_template(
        "queue.html",
        active_page="queue",
        status=status,
        waiting_jobs=waiting_jobs,
        active_job=active_job,
    )
