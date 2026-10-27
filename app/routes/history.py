from flask import Blueprint, render_template, request
from app.models.download_job import DownloadJob
from app.models.media_item import MediaItem

history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.route("")
def index():
    status_filter = request.args.get("status", "").strip() or None
    search = request.args.get("search", "").strip() or None
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    query = DownloadJob.query.filter(
        DownloadJob.status.in_([
            DownloadJob.STATUS_COMPLETED,
            DownloadJob.STATUS_FAILED,
            DownloadJob.STATUS_CANCELLED,
            DownloadJob.STATUS_INTERRUPTED,
        ])
    )

    if status_filter:
        query = query.filter(DownloadJob.status == status_filter)

    if search:
        query = query.join(MediaItem).filter(MediaItem.title.ilike(f"%{search}%"))

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    jobs = query.order_by(DownloadJob.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "history.html",
        active_page="history",
        jobs=jobs,
        total=total,
        page=page,
        total_pages=total_pages,
        status_filter=status_filter or "",
        search=search or "",
    )
