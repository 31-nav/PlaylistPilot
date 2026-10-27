import logging
from pathlib import Path
from typing import Dict, Any
from extensions import db
from app.models.download_job import DownloadJob

logger = logging.getLogger("playlistpilot.recovery")


class RecoveryService:
    @staticmethod
    def recover_stale_jobs(app) -> Dict[str, Any]:
        """
        Inspect the database for orphaned or interrupted jobs from previous application runs.
        Ensures idempotency, preserves completed work, and safely recovers active jobs.
        """
        recovered_count = 0
        preserved_count = 0
        requeued_count = 0

        auto_retry = app.config.get("AUTO_RETRY", True)

        with app.app_context():
            # 1. Find jobs left in 'downloading' status when the app previously shut down or crashed
            stale_jobs = DownloadJob.query.filter_by(status=DownloadJob.STATUS_DOWNLOADING).all()

            for job in stale_jobs:
                # Check if output file exists and is valid
                if job.output_path and Path(job.output_path).exists():
                    job.transition_to(DownloadJob.STATUS_COMPLETED)
                    job.progress_percent = 100.0
                    preserved_count += 1
                    logger.info(f"Recovery: Job #{job.id} output file exists. Marked as COMPLETED.")
                else:
                    # Job was interrupted mid-stream
                    job.transition_to(DownloadJob.STATUS_INTERRUPTED)
                    job.error_message = "Application restarted while job was active. Interrupted state recorded for recovery."
                    
                    # If auto-retry is configured and retries are available, return to queued
                    if auto_retry and job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.transition_to(DownloadJob.STATUS_QUEUED)
                        job.error_message = "Automatically requeued after application restart."
                        requeued_count += 1
                        logger.info(f"Recovery: Job #{job.id} automatically requeued for execution.")
                    else:
                        recovered_count += 1
                        logger.info(f"Recovery: Job #{job.id} marked as INTERRUPTED.")

            db.session.commit()

        return {
            "stale_jobs_found": len(stale_jobs),
            "preserved_as_completed": preserved_count,
            "requeued_for_work": requeued_count,
            "marked_as_interrupted": recovered_count,
        }
