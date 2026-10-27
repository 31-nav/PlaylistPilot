import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_file
from extensions import db
from app.models.playlist import Playlist
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob
from app.services.storage_service import StorageService
from app.services.playlist_service import PlaylistService
from app.services.queue_service import QueueService
from app.services.worker_service import WorkerService
from app.services.youtube_metadata_service import YouTubeMetadataService
from app.services.media_service import MediaService

api_bp = Blueprint("api", __name__, url_prefix="/api")


# --- Playlists API ---

@api_bp.route("/playlists", methods=["GET"])
def list_playlists():
    search = request.args.get("search", "").strip() or None
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")
    playlists = PlaylistService.get_all_playlists(search=search, sort_by=sort_by, order=order)
    return jsonify({
        "success": True,
        "count": len(playlists),
        "playlists": [p.to_dict() for p in playlists],
    })


@api_bp.route("/playlists/<int:playlist_id>", methods=["GET"])
def get_playlist(playlist_id):
    playlist = PlaylistService.get_playlist_by_id(playlist_id)
    if not playlist:
        return jsonify({"success": False, "error": f"Playlist #{playlist_id} not found."}), 404
    return jsonify({"success": True, "playlist": playlist.to_dict(include_items=False)})


@api_bp.route("/playlists/<int:playlist_id>/items", methods=["GET"])
def get_playlist_items(playlist_id):
    playlist = PlaylistService.get_playlist_by_id(playlist_id)
    if not playlist:
        return jsonify({"success": False, "error": f"Playlist #{playlist_id} not found."}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    search = request.args.get("search", "").strip() or None
    sort_by = request.args.get("sort_by", "position")
    order = request.args.get("order", "asc")
    module_filter = request.args.get("module", "").strip() or None

    items, total_count, total_pages = PlaylistService.get_playlist_items(
        playlist_id=playlist_id,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        order=order,
        module_filter=module_filter,
    )

    return jsonify({
        "success": True,
        "playlist_id": playlist_id,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "items": [item.to_dict() for item in items],
    })


@api_bp.route("/playlists/<int:playlist_id>", methods=["DELETE"])
def delete_playlist(playlist_id):
    success = PlaylistService.delete_playlist(playlist_id)
    if not success:
        return jsonify({"success": False, "error": f"Playlist #{playlist_id} not found."}), 404
    return jsonify({"success": True, "message": f"Playlist #{playlist_id} metadata removed safely. Media files and audit history preserved."})


@api_bp.route("/playlists/import", methods=["POST"])
def import_playlist():
    payload = request.get_json(silent=True) or {}
    source_url = payload.get("url", "").strip()

    if not source_url:
        return jsonify({"success": False, "error": "Playlist URL or ID is required."}), 400

    # Handle YouTube Import
    res = YouTubeMetadataService.fetch_playlist_metadata(source_url)
    if not res.get("success"):
        return jsonify(res), 400

    pl_meta = res.get("playlist", {})
    items_meta = res.get("items", [])

    playlist = PlaylistService.import_custom_playlist(
        title=pl_meta.get("title", "Imported YouTube Playlist"),
        source_type="youtube",
        source_url=pl_meta.get("source_url"),
        source_id=pl_meta.get("source_id"),
        description=pl_meta.get("description"),
        thumbnail_url=pl_meta.get("thumbnail_url"),
        items_data=items_meta,
    )

    return jsonify({
        "success": True,
        "message": f"Imported '{playlist.title}' with {len(items_meta)} items.",
        "playlist": playlist.to_dict(),
    }), 201


@api_bp.route("/playlists/demo", methods=["POST"])
def seed_demo():
    payload = request.get_json(silent=True) or {}
    force = payload.get("force", False)
    try:
        pl = PlaylistService.seed_demo_playlist(force=force)
        return jsonify({
            "success": True,
            "message": f"Sample playlist loaded ({pl.item_count} items).",
            "playlist": pl.to_dict(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Queue API ---

@api_bp.route("/queue", methods=["GET"])
def list_queue():
    status_filter = request.args.get("status", DownloadJob.STATUS_QUEUED)
    limit = request.args.get("limit", 100, type=int)

    query = DownloadJob.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    jobs = query.order_by(DownloadJob.priority.desc(), DownloadJob.created_at.asc()).limit(limit).all()
    return jsonify({
        "success": True,
        "status_filter": status_filter,
        "count": len(jobs),
        "jobs": [j.to_dict() for j in jobs],
    })


@api_bp.route("/queue/status", methods=["GET"])
def queue_status():
    status = QueueService.get_queue_status()
    worker = WorkerService.get_instance(current_app)
    status["worker_running"] = worker.is_running
    status["worker_paused"] = worker.is_paused
    status["network_offline"] = worker.simulated_network_offline
    return jsonify({"success": True, **status})


@api_bp.route("/queue", methods=["POST"])
def enqueue():
    payload = request.get_json(silent=True) or {}
    item_ids = payload.get("item_ids", [])
    quality = payload.get("quality", "best")
    default_job_type = "youtube_audio" if quality == "audio_mp3" else "youtube_download"
    job_type = payload.get("job_type", default_job_type)
    priority = payload.get("priority", 0)

    if not item_ids:
        return jsonify({"success": False, "error": "No media item IDs provided."}), 400

    res = QueueService.enqueue_items(item_ids, job_type=job_type, priority=priority, quality=quality)
    
    # Auto-start worker if not already running
    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()

    return jsonify({
        "success": True,
        "message": f"Enqueued {res['added_count']} items [{quality}] ({res['skipped_count']} duplicate items skipped).",
        **res,
    }), 201


@api_bp.route("/queue/<int:job_id>/quality", methods=["PUT", "PATCH"])
def update_job_quality(job_id: int):
    payload = request.get_json(silent=True) or {}
    quality = payload.get("quality", "best")
    res = QueueService.update_job_quality(job_id, quality)
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res)


@api_bp.route("/queue/start", methods=["POST"])
def start_queue():
    worker = WorkerService.get_instance(current_app)
    worker.resume()
    started = worker.start()
    return jsonify({
        "success": True,
        "started": started,
        "worker_running": worker.is_running,
        "message": "Queue processor is active.",
    })


@api_bp.route("/queue/pause", methods=["POST"])
def pause_queue():
    worker = WorkerService.get_instance(current_app)
    worker.pause()
    res = QueueService.pause_queue()
    return jsonify({"success": True, "message": "Queue paused.", **res})


@api_bp.route("/queue/resume", methods=["POST"])
def resume_queue():
    worker = WorkerService.get_instance(current_app)
    worker.resume()
    res = QueueService.resume_queue()
    if not worker.is_running:
        worker.start()
    return jsonify({"success": True, "message": "Queue resumed.", **res})


@api_bp.route("/queue/cancel", methods=["POST"])
def cancel_all_or_job():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("job_id")
    if job_id:
        res = QueueService.cancel_job(job_id)
        return jsonify(res)

    # Cancel all queued
    queued_jobs = DownloadJob.query.filter_by(status=DownloadJob.STATUS_QUEUED).all()
    for j in queued_jobs:
        j.transition_to(DownloadJob.STATUS_CANCELLED)
    db.session.commit()
    return jsonify({"success": True, "message": f"Cancelled {len(queued_jobs)} waiting jobs."})


@api_bp.route("/queue/retry", methods=["POST"])
def retry_job():
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("job_id")
    if not job_id:
        return jsonify({"success": False, "error": "job_id is required"}), 400

    res = QueueService.retry_job(job_id)
    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()
    return jsonify(res)


@api_bp.route("/queue/retry-all", methods=["POST"])
def retry_all_failed():
    res = QueueService.retry_all_failed()
    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()
    return jsonify(res)


@api_bp.route("/queue/<int:job_id>/prioritize", methods=["POST"])
def prioritize_job(job_id):
    res = QueueService.prioritize_job(job_id)
    return jsonify(res)


@api_bp.route("/queue/<int:job_id>", methods=["DELETE"])
def remove_queue_job(job_id):
    res = QueueService.cancel_job(job_id)
    return jsonify(res)


# --- History & Jobs API ---

@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_detail(job_id):
    job = db.session.get(DownloadJob, job_id)
    if not job:
        return jsonify({"success": False, "error": f"Job #{job_id} not found."}), 404
    return jsonify({"success": True, "job": job.to_dict()})


@api_bp.route("/jobs/<int:job_id>/download", methods=["GET"])
@api_bp.route("/download/<int:job_id>", methods=["GET"])
def download_job_file(job_id):
    """
    Download the completed MP4 video or MP3 audio file directly to the user's phone or computer.
    Sets Content-Disposition attachment to trigger automatic browser download.
    """
    job = db.session.get(DownloadJob, job_id)
    if not job:
        return jsonify({"success": False, "error": f"Job #{job_id} not found."}), 404

    if job.status != DownloadJob.STATUS_COMPLETED:
        return jsonify({
            "success": False,
            "error": f"Job #{job_id} is not completed yet (current status: {job.status}).",
        }), 400

    if not job.output_path:
        return jsonify({"success": False, "error": "No output media file registered for this job."}), 404

    target_path = Path(job.output_path).resolve()
    if not target_path.exists():
        download_dir = Path(current_app.config.get("DOWNLOAD_DIR", "downloads")).resolve()
        candidate = download_dir / target_path.name
        if candidate.exists():
            target_path = candidate
        else:
            return jsonify({
                "success": False,
                "error": f"Media file '{target_path.name}' is no longer present on the server.",
            }), 404

    suffix = target_path.suffix.lower()
    if suffix == ".mp4":
        mimetype = "video/mp4"
    elif suffix == ".mp3":
        mimetype = "audio/mpeg"
    elif suffix in (".webm", ".mkv"):
        mimetype = "video/webm" if suffix == ".webm" else "video/x-matroska"
    elif suffix == ".txt":
        mimetype = "text/plain"
    else:
        mimetype = "application/octet-stream"

    return send_file(
        str(target_path),
        as_attachment=True,
        download_name=target_path.name,
        mimetype=mimetype,
        max_age=0,
    )


@api_bp.route("/metadata/inspect-url", methods=["POST"])
def inspect_youtube_url():
    """Fast URL inspection to detect video or playlist without starting download."""
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "").strip()
    if not raw_url:
        return jsonify({"success": False, "error": "Please provide a valid YouTube URL or ID."}), 400

    pl_id = YouTubeMetadataService.extract_playlist_id(raw_url)
    v_id = YouTubeMetadataService.extract_video_id(raw_url)

    if pl_id and not v_id:
        return jsonify({
            "success": True,
            "is_playlist": True,
            "playlist_id": pl_id,
            "url": raw_url,
        })

    meta_res = YouTubeMetadataService.fetch_single_video_metadata(raw_url)
    if meta_res.get("success"):
        return jsonify({
            "success": True,
            "is_playlist": False,
            "video": meta_res["video"],
        })
    elif v_id:
        return jsonify({
            "success": True,
            "is_playlist": False,
            "video": {
                "id": v_id,
                "title": f"YouTube Video ({v_id})",
                "duration_seconds": 0,
                "thumbnail_url": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                "uploader": "YouTube",
                "url": f"https://www.youtube.com/watch?v={v_id}",
            }
        })
    return jsonify({"success": False, "error": meta_res.get("error", "Invalid YouTube link.")}), 400


@api_bp.route("/download/quick", methods=["POST"])
def quick_download():
    """
    Direct 1-click video/audio download for mobile phones and web browsers.
    Accepts any YouTube video/shorts/mobile link, creates high-priority job, and starts processing.
    """
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "").strip()
    quality = payload.get("quality", "best")
    is_audio = (quality == "audio_mp3")

    if not raw_url:
        return jsonify({"success": False, "error": "Please enter a YouTube video or playlist link."}), 400

    pl_id = YouTubeMetadataService.extract_playlist_id(raw_url)
    v_id = YouTubeMetadataService.extract_video_id(raw_url)

    # If it's a playlist link with NO specific video target, import it
    if pl_id and not v_id:
        res = YouTubeMetadataService.fetch_playlist_metadata(raw_url)
        if not res.get("success"):
            return jsonify(res), 400
        pl_meta = res.get("playlist", {})
        items_meta = res.get("items", [])
        playlist = PlaylistService.import_custom_playlist(
            title=pl_meta.get("title", "Imported YouTube Playlist"),
            source_type="youtube",
            source_url=pl_meta.get("source_url"),
            source_id=pl_meta.get("source_id"),
            description=pl_meta.get("description"),
            thumbnail_url=pl_meta.get("thumbnail_url"),
            items_data=items_meta,
        )
        return jsonify({
            "success": True,
            "is_playlist": True,
            "playlist_id": playlist.id,
            "message": f"Imported '{playlist.title}' with {len(items_meta)} items.",
        })

    # Single video download flow
    meta_res = YouTubeMetadataService.fetch_single_video_metadata(raw_url)
    if meta_res.get("success"):
        v_meta = meta_res["video"]
    elif v_id:
        v_meta = {
            "id": v_id,
            "title": f"YouTube Video ({v_id})",
            "duration_seconds": 0,
            "thumbnail_url": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
            "uploader": "YouTube",
            "url": f"https://www.youtube.com/watch?v={v_id}",
        }
    else:
        return jsonify({"success": False, "error": meta_res.get("error", "Unable to resolve YouTube video.")}), 400

    # Ensure a parent collection exists for direct video downloads
    direct_pl = Playlist.query.filter_by(source_type="youtube_direct").first()
    if not direct_pl:
        direct_pl = Playlist(
            title="Quick YouTube Downloads",
            source_type="youtube_direct",
            source_id="QUICK_DOWNLOADS",
            description="Individual videos downloaded via quick download.",
            thumbnail_url=v_meta.get("thumbnail_url"),
        )
        db.session.add(direct_pl)
        db.session.flush()

    # Find or create MediaItem
    item = MediaItem.query.filter_by(playlist_id=direct_pl.id, source_id=v_meta["id"]).first()
    if not item:
        item = MediaItem(
            playlist_id=direct_pl.id,
            source_id=v_meta["id"],
            title=v_meta["title"],
            duration_seconds=v_meta.get("duration_seconds", 0),
            media_type="audio" if is_audio else "video",
            thumbnail_url=v_meta.get("thumbnail_url"),
            availability_status="available",
        )
        db.session.add(item)
        db.session.flush()

    # Create top-priority download job
    job_type = "youtube_audio" if is_audio else "youtube_download"
    job = DownloadJob(
        media_item_id=item.id,
        job_type=job_type,
        quality=quality,
        status=DownloadJob.STATUS_QUEUED,
        priority=10,  # Urgent priority: executes immediately
    )
    db.session.add(job)
    db.session.commit()

    # Ensure worker engine is active
    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()

    format_name = "MP3 Audio" if is_audio else f"MP4 Video ({'Best Quality' if quality == 'best' else quality.upper()})"
    return jsonify({
        "success": True,
        "is_playlist": False,
        "job_id": job.id,
        "video": v_meta,
        "quality": quality,
        "format_label": format_name,
        "download_url": f"/api/jobs/{job.id}/download",
        "message": f"Downloading '{v_meta['title']}' as {format_name}. Progress is updating live...",
    }), 201


@api_bp.route("/fetch", methods=["POST"])
def fetch_content():
    """
    Fetch metadata for a YouTube video or playlist link.
    Returns playlist info along with list of all items so users can pick individual videos (e.g. 3, 4, 7, etc.).
    """
    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("url", "").strip()

    if not raw_url:
        return jsonify({"success": False, "error": "Please enter a YouTube video or playlist link."}), 400

    pl_id = YouTubeMetadataService.extract_playlist_id(raw_url)
    v_id = YouTubeMetadataService.extract_video_id(raw_url)

    # 1. If it's a playlist URL
    if pl_id and not v_id:
        res = YouTubeMetadataService.fetch_playlist_metadata(raw_url)
        if not res.get("success"):
            return jsonify(res), 400

        pl_meta = res.get("playlist", {})
        raw_items = res.get("items", [])

        items = []
        for idx, it in enumerate(raw_items, 1):
            dur = it.get("duration_seconds", 0)
            mins, secs = divmod(dur, 60)
            dur_str = f"{mins}:{secs:02d}" if dur > 0 else "--:--"
            v_id_item = it.get("source_id")
            items.append({
                "index": idx,
                "id": v_id_item,
                "title": it.get("title", f"Video #{idx}"),
                "duration_seconds": dur,
                "duration_formatted": dur_str,
                "thumbnail_url": it.get("thumbnail_url") or (f"https://img.youtube.com/vi/{v_id_item}/hqdefault.jpg" if v_id_item else "/static/images/placeholder-thumbnail.svg"),
                "uploader": it.get("metadata", {}).get("channelTitle") or it.get("metadata", {}).get("uploader") or pl_meta.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={v_id_item}",
            })

        return jsonify({
            "success": True,
            "is_playlist": True,
            "title": pl_meta.get("title", "YouTube Playlist"),
            "thumbnail_url": pl_meta.get("thumbnail_url"),
            "uploader": pl_meta.get("uploader") or "YouTube",
            "total_items": len(items),
            "items": items,
        })

    # 2. Single video or Short
    meta_res = YouTubeMetadataService.fetch_single_video_metadata(raw_url)
    if meta_res.get("success"):
        v_meta = meta_res["video"]
    elif v_id:
        v_meta = {
            "id": v_id,
            "title": f"YouTube Video ({v_id})",
            "duration_seconds": 0,
            "thumbnail_url": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
            "uploader": "YouTube",
            "url": f"https://www.youtube.com/watch?v={v_id}",
        }
    else:
        return jsonify({"success": False, "error": meta_res.get("error", "Could not retrieve video details.")}), 400

    dur = v_meta.get("duration_seconds", 0)
    mins, secs = divmod(dur, 60)
    dur_str = f"{mins}:{secs:02d}" if dur > 0 else "--:--"

    single_item = {
        "index": 1,
        "id": v_meta["id"],
        "title": v_meta["title"],
        "duration_seconds": dur,
        "duration_formatted": dur_str,
        "thumbnail_url": v_meta.get("thumbnail_url") or f"https://img.youtube.com/vi/{v_meta['id']}/hqdefault.jpg",
        "uploader": v_meta.get("uploader", "YouTube"),
        "url": v_meta.get("url") or f"https://www.youtube.com/watch?v={v_meta['id']}",
    }

    return jsonify({
        "success": True,
        "is_playlist": False,
        "title": v_meta["title"],
        "thumbnail_url": v_meta.get("thumbnail_url"),
        "uploader": v_meta.get("uploader", "YouTube"),
        "total_items": 1,
        "items": [single_item],
    })


@api_bp.route("/batch-download", methods=["POST"])
def batch_download():
    """
    Enqueues selected videos (e.g. 1, 3, 4, 7 items) for step-by-step sequential processing.
    Each job is prioritized in order, and the worker executes them one by one.
    """
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    quality = payload.get("quality", "best")
    is_audio = (quality == "audio_mp3")

    if not items:
        return jsonify({"success": False, "error": "No videos selected for download."}), 400

    direct_pl = Playlist.query.filter_by(source_type="youtube_direct").first()
    if not direct_pl:
        direct_pl = Playlist(
            title="Quick YouTube Downloads",
            source_type="youtube_direct",
            source_id="QUICK_DOWNLOADS",
            description="Videos downloaded directly by users.",
        )
        db.session.add(direct_pl)
        db.session.flush()

    job_records = []
    base_priority = 100

    for idx, it in enumerate(items):
        v_id = str(it.get("id") or it.get("video_id") or it.get("source_id") or "").strip()
        if not v_id:
            continue
        v_title = it.get("title") or f"Video ({v_id})"
        v_dur = it.get("duration_seconds") or 0
        v_thumb = it.get("thumbnail_url") or f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"

        media_item = MediaItem.query.filter_by(playlist_id=direct_pl.id, source_id=v_id).first()
        if not media_item:
            media_item = MediaItem(
                playlist_id=direct_pl.id,
                source_id=v_id,
                title=v_title,
                duration_seconds=v_dur,
                media_type="audio" if is_audio else "video",
                thumbnail_url=v_thumb,
                availability_status="available",
            )
            db.session.add(media_item)
            db.session.flush()

        job_type = "youtube_audio" if is_audio else "youtube_download"
        job = DownloadJob(
            media_item_id=media_item.id,
            job_type=job_type,
            quality=quality,
            status=DownloadJob.STATUS_QUEUED,
            priority=base_priority - idx,
        )
        db.session.add(job)
        db.session.flush()

        job_records.append({
            "job_id": job.id,
            "video_id": v_id,
            "title": v_title,
            "thumbnail_url": v_thumb,
            "quality": quality,
            "download_url": f"/api/jobs/{job.id}/download",
        })

    db.session.commit()

    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()

    return jsonify({
        "success": True,
        "count": len(job_records),
        "jobs": job_records,
        "message": f"Enqueued {len(job_records)} video(s) for sequential download.",
    }), 201


@api_bp.route("/history", methods=["GET"])
def list_history():
    status = request.args.get("status")
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = DownloadJob.query.filter(
        DownloadJob.status.in_([
            DownloadJob.STATUS_COMPLETED,
            DownloadJob.STATUS_FAILED,
            DownloadJob.STATUS_CANCELLED,
            DownloadJob.STATUS_INTERRUPTED,
        ])
    )

    if status:
        query = query.filter(DownloadJob.status == status)

    if search:
        query = query.join(MediaItem).filter(MediaItem.title.ilike(f"%{search}%"))

    total = query.count()
    jobs = query.order_by(DownloadJob.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "success": True,
        "page": page,
        "per_page": per_page,
        "total": total,
        "jobs": [j.to_dict() for j in jobs],
    })


# --- Storage API ---

@api_bp.route("/storage", methods=["GET"])
def get_storage():
    download_dir = current_app.config.get("DOWNLOAD_DIR")
    info = StorageService.get_disk_info(download_dir)
    return jsonify({"success": True, **info})


@api_bp.route("/storage/validate-path", methods=["POST"])
def validate_storage_path():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path", "").strip()
    val = StorageService.validate_download_directory(path)
    return jsonify(val)


# --- Demonstration & Simulation APIs ---

@api_bp.route("/simulate/network", methods=["POST"])
def toggle_network_simulation():
    """Toggle simulated network connection to demonstrate interruption and recovery."""
    payload = request.get_json(silent=True) or {}
    worker = WorkerService.get_instance(current_app)
    
    # If offline parameter explicitly provided, set it; otherwise toggle
    if "offline" in payload:
        worker.simulated_network_offline = bool(payload["offline"])
    else:
        worker.simulated_network_offline = not worker.simulated_network_offline

    state_str = "OFFLINE (Disconnected)" if worker.simulated_network_offline else "ONLINE (Restored)"
    
    # If restored, automatically recover interrupted jobs if auto_retry is set
    auto_recovered = 0
    if not worker.simulated_network_offline:
        res = QueueService.resume_queue()
        auto_recovered = res.get("resumed_count", 0)
        # Also requeue interrupted jobs
        interrupted = DownloadJob.query.filter_by(status=DownloadJob.STATUS_INTERRUPTED).all()
        for j in interrupted:
            j.transition_to(DownloadJob.STATUS_QUEUED)
            auto_recovered += 1
        db.session.commit()
        if not worker.is_running:
            worker.start()

    return jsonify({
        "success": True,
        "simulated_network_offline": worker.simulated_network_offline,
        "status_label": state_str,
        "auto_recovered_jobs": auto_recovered,
        "message": f"Simulated network is now {state_str}.",
    })


@api_bp.route("/simulate/fail-next", methods=["POST"])
def simulate_job_failure():
    """Inject a deliberate demonstration failure into the active or next job."""
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("job_id")
    worker = WorkerService.get_instance(current_app)

    if job_id:
        worker.simulate_failure_job_id = int(job_id)
        msg = f"Injected simulated failure trigger for Job #{job_id}."
    else:
        worker.simulate_next_job_failure = True
        msg = "Injected simulated failure trigger for the next active job."

    return jsonify({"success": True, "message": msg})


# --- Local Media Processing API ---

@api_bp.route("/media/inspect", methods=["POST"])
def inspect_media_file():
    payload = request.get_json(silent=True) or {}
    file_path = payload.get("file_path", "").strip()
    if not file_path:
        return jsonify({"success": False, "error": "file_path is required."}), 400

    info = MediaService.inspect_local_file(file_path)
    return jsonify(info)


@api_bp.route("/media/convert", methods=["POST"])
def convert_media():
    payload = request.get_json(silent=True) or {}
    source_file = payload.get("file_path", "").strip()
    output_format = payload.get("output_format", "mp3")

    if not source_file:
        return jsonify({"success": False, "error": "file_path is required."}), 400

    inspect = MediaService.inspect_local_file(source_file)
    if not inspect.get("valid"):
        return jsonify({"success": False, "error": inspect.get("error")}), 400

    # Create MediaItem and DownloadJob for local conversion
    item = MediaItem(
        source_id=source_file,
        title=f"Local: {inspect['name']}",
        media_type="local_file",
        thumbnail_url="/static/images/placeholder-thumbnail.svg",
    )
    db.session.add(item)
    db.session.flush()

    job = DownloadJob(
        media_item_id=item.id,
        job_type="media_convert",
        status=DownloadJob.STATUS_QUEUED,
        priority=5,
    )
    db.session.add(job)
    db.session.commit()

    worker = WorkerService.get_instance(current_app)
    if not worker.is_running:
        worker.start()

    return jsonify({
        "success": True,
        "message": f"Enqueued local media conversion for '{inspect['name']}'.",
        "job_id": job.id,
    }), 201
