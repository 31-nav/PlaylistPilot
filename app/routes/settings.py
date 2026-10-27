from pathlib import Path
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.services.media_service import MediaService
from app.services.storage_service import StorageService

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        api_key = request.form.get("youtube_api_key", "").strip()
        download_dir_input = request.form.get("download_directory", "").strip()
        auto_retry = request.form.get("auto_retry") == "on"
        max_retries = int(request.form.get("max_retries", 3))
        poll_interval = float(request.form.get("queue_poll_interval", 2.0))
        default_quality = request.form.get("default_quality", "best")

        if api_key:
            current_app.config["YOUTUBE_API_KEY"] = api_key
        
        # Handle custom download path
        if download_dir_input:
            val = StorageService.validate_download_directory(download_dir_input)
            if val.get("valid"):
                current_app.config["DOWNLOAD_DIR"] = Path(val["path"])
            else:
                flash(val.get("error"), "error")
                return redirect(url_for("settings.index"))

        current_app.config["AUTO_RETRY"] = auto_retry
        current_app.config["MAX_RETRIES"] = max_retries
        current_app.config["QUEUE_POLL_INTERVAL"] = poll_interval
        current_app.config["DEFAULT_QUALITY"] = default_quality

        flash("Settings and storage path saved successfully.", "success")
        return redirect(url_for("settings.index"))

    api_key = current_app.config.get("YOUTUBE_API_KEY", "")
    masked_key = f"{api_key[:4]}••••••••{api_key[-4:]}" if len(api_key) >= 8 else ("Configured" if api_key else "Not Configured")

    current_download_dir = Path(current_app.config.get("DOWNLOAD_DIR")).resolve()
    disk_info = StorageService.get_disk_info(current_download_dir)
    suggested_paths = StorageService.get_suggested_paths(current_download_dir)
    ffmpeg_available = MediaService.is_ffmpeg_available()

    return render_template(
        "settings.html",
        active_page="settings",
        has_api_key=bool(api_key),
        masked_key=masked_key,
        auto_retry=current_app.config.get("AUTO_RETRY", True),
        max_retries=current_app.config.get("MAX_RETRIES", 3),
        poll_interval=current_app.config.get("QUEUE_POLL_INTERVAL", 2.0),
        default_quality=current_app.config.get("DEFAULT_QUALITY", "best"),
        download_dir=str(current_download_dir),
        disk_info=disk_info,
        suggested_paths=suggested_paths,
        ffmpeg_available=ffmpeg_available,
    )
