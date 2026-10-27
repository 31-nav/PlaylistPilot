from flask import Blueprint, render_template, current_app
from app.models.playlist import Playlist
from app.models.download_job import DownloadJob
from app.services.storage_service import StorageService
from app.services.queue_service import QueueService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    status = QueueService.get_queue_status()
    download_dir = current_app.config.get("DOWNLOAD_DIR")
    disk_info = StorageService.get_disk_info(download_dir)
    recent_playlists = Playlist.query.order_by(Playlist.created_at.desc()).limit(5).all()
    recent_jobs = DownloadJob.query.order_by(DownloadJob.updated_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        status=status,
        disk_info=disk_info,
        recent_playlists=recent_playlists,
        recent_jobs=recent_jobs,
    )


@dashboard_bp.route("/about")
def about():
    return render_template("about.html", active_page="about")
