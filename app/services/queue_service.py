from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from extensions import db
from app.models.download_job import DownloadJob
from app.models.media_item import MediaItem


class QueueService:
    @staticmethod
    def enqueue_items(
        media_item_ids: List[int],
        job_type: str = "youtube_download",
        priority: int = 0,
        quality: str = "best",
    ) -> Dict[str, Any]:
        """
        Enqueue selected media items into DownloadJob queue with target resolution quality.
        Prevents duplicate pending/downloading jobs for the same media item.
        """
        if not media_item_ids:
            return {"added_count": 0, "skipped_count": 0, "job_ids": []}

        # Check existing non-terminal jobs to prevent redundant re-queueing
        active_or_waiting = (
            db.session.query(DownloadJob.media_item_id)
            .filter(
                DownloadJob.media_item_id.in_(media_item_ids),
                DownloadJob.status.in_([DownloadJob.STATUS_QUEUED, DownloadJob.STATUS_DOWNLOADING, DownloadJob.STATUS_PAUSED]),
            )
            .all()
        )
        existing_item_ids = {row[0] for row in active_or_waiting}

        items = MediaItem.query.filter(MediaItem.id.in_(media_item_ids)).all()
        added_jobs = []
        skipped_count = 0

        for item in items:
            if item.id in existing_item_ids:
                skipped_count += 1
                continue

            # Idempotency key based on item source_id, quality and timestamp
            idempotency = f"{job_type}_{item.id}_{quality}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            
            job = DownloadJob(
                media_item_id=item.id,
                job_type=job_type,
                quality=quality,
                status=DownloadJob.STATUS_QUEUED,
                priority=priority,
                progress_percent=0.0,
                retry_count=0,
                idempotency_key=idempotency,
            )
            added_jobs.append(job)

        if added_jobs:
            db.session.add_all(added_jobs)
            db.session.commit()

        return {
            "added_count": len(added_jobs),
            "skipped_count": skipped_count,
            "job_ids": [j.id for j in added_jobs],
        }

    @staticmethod
    def update_job_quality(job_id: int, quality: str) -> Dict[str, Any]:
        """Update download quality resolution for a queued or paused job."""
        job = db.session.get(DownloadJob, job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        if job.status not in (DownloadJob.STATUS_QUEUED, DownloadJob.STATUS_PAUSED):
            return {"success": False, "error": f"Cannot change quality for job in '{job.status}' state."}

        job.quality = quality
        if quality == "audio_mp3":
            job.job_type = "youtube_audio"
        else:
            job.job_type = "youtube_download"
        db.session.commit()
        return {"success": True, "job_id": job.id, "quality": job.quality, "job_type": job.job_type}

    @staticmethod
    def get_queue_status() -> Dict[str, Any]:
        """Get aggregate counts and overall queue progress."""
        counts = {
            "queued": 0,
            "downloading": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
            "interrupted": 0,
            "cancelled": 0,
            "total": 0,
        }

        # Group by status count
        rows = (
            db.session.query(DownloadJob.status, db.func.count(DownloadJob.id))
            .group_by(DownloadJob.status)
            .all()
        )
        for status, cnt in rows:
            if status in counts:
                counts[status] = cnt
            counts["total"] += cnt

        # Active job details if any
        active_job = (
            DownloadJob.query.filter_by(status=DownloadJob.STATUS_DOWNLOADING)
            .order_by(DownloadJob.started_at.desc())
            .first()
        )

        # Overall progress of all active or completed jobs
        completed = counts["completed"]
        total_processable = counts["queued"] + counts["downloading"] + counts["paused"] + counts["completed"]
        overall_progress = round((completed / total_processable * 100), 1) if total_processable > 0 else 0.0

        return {
            "counts": counts,
            "active_job": active_job.to_dict() if active_job else None,
            "overall_progress": overall_progress,
            "has_active_work": counts["downloading"] > 0 or counts["queued"] > 0,
        }

    @staticmethod
    def get_waiting_queue(limit: int = 100) -> List[DownloadJob]:
        """Fetch jobs waiting to be processed, sorted by priority (desc) then created_at (asc)."""
        return (
            DownloadJob.query.filter_by(status=DownloadJob.STATUS_QUEUED)
            .order_by(DownloadJob.priority.desc(), DownloadJob.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def prioritize_job(job_id: int) -> Dict[str, Any]:
        """
        Prioritize an urgent waiting job by moving it to the front of the queue.
        Does not interrupt the active job.
        """
        job = db.session.get(DownloadJob, job_id)
        if not job:
            return {"success": False, "error": f"Job #{job_id} not found."}

        if job.status != DownloadJob.STATUS_QUEUED:
            return {
                "success": False,
                "error": f"Only waiting (queued) jobs can be prioritized. Job is currently '{job.status}'.",
            }

        # Find current highest priority in waiting queue
        max_priority = db.session.query(db.func.max(DownloadJob.priority)).filter_by(status=DownloadJob.STATUS_QUEUED).scalar() or 0
        new_priority = max(max_priority + 10, job.priority + 10)
        
        job.priority = new_priority
        job.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return {
            "success": True,
            "job_id": job.id,
            "new_priority": job.priority,
            "message": f"Job #{job.id} '{job.media_item.title if job.media_item else ''}' prioritized to the front of the waiting queue.",
        }

    @staticmethod
    def cancel_job(job_id: int) -> Dict[str, Any]:
        """Cancel a queued, paused, or running job."""
        job = db.session.get(DownloadJob, job_id)
        if not job:
            return {"success": False, "error": f"Job #{job_id} not found."}

        if job.status == DownloadJob.STATUS_QUEUED or job.status == DownloadJob.STATUS_PAUSED:
            job.transition_to(DownloadJob.STATUS_CANCELLED)
            db.session.commit()
            return {"success": True, "status": "cancelled", "message": f"Job #{job_id} cancelled."}
        elif job.status == DownloadJob.STATUS_DOWNLOADING:
            job.cancel_requested = True
            db.session.commit()
            return {"success": True, "status": "cancel_requested", "message": f"Cancellation requested for active job #{job_id}."}
        else:
            return {"success": False, "error": f"Cannot cancel job in state '{job.status}'."}

    @staticmethod
    def retry_job(job_id: int) -> Dict[str, Any]:
        """Retry a failed or interrupted job."""
        job = db.session.get(DownloadJob, job_id)
        if not job:
            return {"success": False, "error": f"Job #{job_id} not found."}

        if not job.can_transition_to(DownloadJob.STATUS_QUEUED):
            return {
                "success": False,
                "error": f"Job #{job_id} in status '{job.status}' cannot be retried.",
            }

        job.retry_count += 1
        job.error_message = None
        job.progress_percent = 0.0
        job.transition_to(DownloadJob.STATUS_QUEUED)
        db.session.commit()

        return {"success": True, "job_id": job.id, "message": f"Job #{job_id} reset to queued for retry."}

    @staticmethod
    def retry_all_failed() -> Dict[str, Any]:
        """Retry all failed or interrupted jobs."""
        retryable_jobs = DownloadJob.query.filter(
            DownloadJob.status.in_([DownloadJob.STATUS_FAILED, DownloadJob.STATUS_INTERRUPTED])
        ).all()

        count = 0
        for job in retryable_jobs:
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.error_message = None
                job.progress_percent = 0.0
                job.transition_to(DownloadJob.STATUS_QUEUED)
                count += 1

        db.session.commit()
        return {"success": True, "retried_count": count}

    @staticmethod
    def pause_queue() -> Dict[str, Any]:
        """Request active job to pause and prevent new jobs from starting."""
        active_job = DownloadJob.query.filter_by(status=DownloadJob.STATUS_DOWNLOADING).first()
        if active_job:
            active_job.pause_requested = True
            db.session.commit()
            return {"success": True, "active_job_id": active_job.id, "message": "Queue pause signal sent to active worker."}
        return {"success": True, "message": "Queue paused (no active job was running)."}

    @staticmethod
    def resume_queue() -> Dict[str, Any]:
        """Resume paused jobs by returning them to queued status."""
        paused_jobs = DownloadJob.query.filter_by(status=DownloadJob.STATUS_PAUSED).all()
        for job in paused_jobs:
            job.pause_requested = False
            job.transition_to(DownloadJob.STATUS_QUEUED)
        db.session.commit()
        return {"success": True, "resumed_count": len(paused_jobs)}
