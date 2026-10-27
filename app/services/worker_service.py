import time
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from flask import Flask

from extensions import db
from app.models.download_job import DownloadJob
from app.models.media_item import MediaItem
from app.services.storage_service import StorageService

logger = logging.getLogger("playlistpilot.worker")


class WorkerService:
    _instance: Optional["WorkerService"] = None
    _lock = threading.Lock()

    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self.is_running = False
        
        # Simulation controls for College Viva & Demonstration
        self.simulated_network_offline = False
        self.simulate_next_job_failure = False
        self.simulate_failure_job_id: Optional[int] = None

    @classmethod
    def get_instance(cls, app: Optional[Flask] = None) -> "WorkerService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(app)
            elif app and not cls._instance.app:
                cls._instance.app = app
            return cls._instance

    def start(self) -> bool:
        """Start the background worker thread safely. Prevents duplicate workers."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.info("Worker thread is already running.")
                return False

            self._stop_event.clear()
            self._pause_event.clear()
            self.is_running = True
            
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="PlaylistPilot-WorkerThread",
                daemon=True,
            )
            self._thread.start()
            logger.info("Background worker thread started successfully.")
            return True

    def stop(self, timeout: float = 3.0) -> bool:
        """Gracefully signal worker thread to stop."""
        with self._lock:
            self._stop_event.set()
            self.is_running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                return not self._thread.is_alive()
            return True

    def pause(self) -> None:
        """Pause worker processing loop."""
        self._pause_event.set()

    def resume(self) -> None:
        """Resume worker processing loop."""
        self._pause_event.clear()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def _worker_loop(self):
        """Main single-worker processing loop with isolated database sessions."""
        logger.info("Worker loop started.")

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.5)
                continue

            if not self.app:
                time.sleep(0.5)
                continue

            # Process next job inside fresh application context
            job_processed = False
            try:
                with self.app.app_context():
                    job_processed = self._process_next_job()
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)

            # Rest briefly if no job was waiting, or respect polling interval
            if not job_processed:
                poll_interval = self.app.config.get("QUEUE_POLL_INTERVAL", 2.0) if self.app else 2.0
                time.sleep(min(poll_interval, 1.0))

        self.is_running = False
        logger.info("Worker loop exited cleanly.")

    def _process_next_job(self) -> bool:
        """Find and execute the highest priority waiting job."""
        # Check storage space before picking a job
        download_dir = self.app.config.get("DOWNLOAD_DIR")
        disk_info = StorageService.get_disk_info(download_dir)
        min_space_mb = self.app.config.get("MIN_FREE_SPACE_MB", 200)

        if disk_info.get("free_mb", 9999) < min_space_mb:
            logger.warning(f"Low disk space ({disk_info.get('free_mb')} MB < {min_space_mb} MB). Pausing queue.")
            self._pause_event.set()
            return False

        # Query highest priority waiting job (FIFO for ties)
        job = (
            DownloadJob.query.filter_by(status=DownloadJob.STATUS_QUEUED)
            .order_by(DownloadJob.priority.desc(), DownloadJob.created_at.asc())
            .first()
        )

        if not job:
            return False

        # Transition to downloading
        job.transition_to(DownloadJob.STATUS_DOWNLOADING)
        job.started_at = datetime.now(timezone.utc)
        db.session.commit()
        job_id = job.id

        logger.info(f"Worker picked Job #{job_id} (Priority: {job.priority}). Starting execution.")

        try:
            # Determine whether this job is a real YouTube download or a curriculum simulation
            is_real_youtube = False
            if job.media_item:
                src_id = job.media_item.source_id or ""
                is_demo = (
                    src_id.startswith("demo_")
                    or src_id.startswith("item_")
                    or (job.media_item.playlist and job.media_item.playlist.source_type == "demo")
                    or job.job_type == "demo_download"
                )
                if not is_demo:
                    pl = job.media_item.playlist
                    if (pl and pl.source_type == "youtube") or job.job_type in ("youtube_download", "youtube_audio", "download"):
                        is_real_youtube = True

            if is_real_youtube:
                self._execute_youtube_job(job_id)
            elif job.job_type == "media_conversion":
                self._execute_media_job(job_id)
            else:
                self._execute_demo_job(job_id)
            return True
        except Exception as e:
            logger.error(f"Error executing Job #{job_id}: {e}", exc_info=True)
            with self.app.app_context():
                current_job = db.session.get(DownloadJob, job_id)
                if current_job and current_job.status == DownloadJob.STATUS_DOWNLOADING:
                    current_job.error_message = str(e)
                    current_job.transition_to(DownloadJob.STATUS_FAILED)
                    db.session.commit()
            return True

    def _execute_youtube_job(self, job_id: int):
        """Execute genuine YouTube video download using yt-dlp into local storage directory."""
        from app.services.media_service import MediaService

        # Fetch job and target video info
        with self.app.app_context():
            job = db.session.get(DownloadJob, job_id)
            if not job or not job.media_item:
                return

            video_target = job.media_item.source_id
            target_title = job.media_item.title
            target_quality = job.quality or "best"
            media_format = "audio" if (target_quality == "audio_mp3" or job.job_type == "youtube_audio") else "video"
            dest_dir = self.app.config.get("DOWNLOAD_DIR")

        logger.info(f"Starting real YouTube download for Job #{job_id} [{target_quality}]: '{target_title}' -> {dest_dir}")

        last_update_time = [0.0]

        def on_progress(p_data: Dict[str, Any]):
            now = time.time()
            if now - last_update_time[0] < 0.4 and p_data.get("status") != "finished":
                return
            last_update_time[0] = now

            with self.app.app_context():
                j = db.session.get(DownloadJob, job_id)
                if not j or j.status != DownloadJob.STATUS_DOWNLOADING:
                    return

                if "percent" in p_data:
                    j.progress_percent = min(99.0, max(0.0, round(float(p_data["percent"]), 1)))
                if "downloaded_bytes" in p_data:
                    j.bytes_processed = int(p_data["downloaded_bytes"])
                if "total_bytes" in p_data and p_data["total_bytes"]:
                    j.total_bytes = int(p_data["total_bytes"])
                db.session.commit()

        def cancel_check() -> bool:
            if self._stop_event.is_set():
                return True
            with self.app.app_context():
                j = db.session.get(DownloadJob, job_id)
                return bool(j and j.cancel_requested)

        res = MediaService.download_youtube_media(
            video_id_or_url=video_target,
            output_dir=dest_dir,
            media_format=media_format,
            quality=target_quality,
            progress_callback=on_progress,
            cancel_check=cancel_check,
        )

        with self.app.app_context():
            j = db.session.get(DownloadJob, job_id)
            if not j:
                return

            if cancel_check():
                j.transition_to(DownloadJob.STATUS_CANCELLED)
                j.error_message = "Download cancelled by user."
                db.session.commit()
                logger.info(f"Job #{job_id} cancelled upon user request.")
                return

            if res.get("success"):
                j.output_path = res.get("output_path")
                j.progress_percent = 100.0
                if res.get("file_size"):
                    j.bytes_processed = res["file_size"]
                    j.total_bytes = res["file_size"]
                j.transition_to(DownloadJob.STATUS_COMPLETED)
                db.session.commit()
                logger.info(f"Job #{job_id} successfully completed. Saved to: {j.output_path}")
            else:
                err_msg = res.get("error", "Download failed.")
                j.error_message = err_msg
                j.transition_to(DownloadJob.STATUS_FAILED)
                db.session.commit()
                logger.error(f"Job #{job_id} failed: {err_msg}")

    def _execute_demo_job(self, job_id: int):
        """Simulate an educational download job with checkpointing, pause, cancel, and recovery."""
        sim_speed = self.app.config.get("SIMULATION_SPEED", 1.0)
        # 10 steps to 100%
        step_delay = max(0.05, 0.4 / sim_speed)

        # Simulation check: Test failure injection
        fail_this_job = False
        if self.simulate_next_job_failure or (self.simulate_failure_job_id == job_id):
            fail_this_job = True
            self.simulate_next_job_failure = False
            self.simulate_failure_job_id = None

        for step in range(1, 11):
            if self._stop_event.is_set():
                # Application shutting down
                return

            # Check network interruption simulation
            if self.simulated_network_offline:
                with self.app.app_context():
                    j = db.session.get(DownloadJob, job_id)
                    if j and j.status == DownloadJob.STATUS_DOWNLOADING:
                        j.error_message = "Simulated Network Interruption: Connection lost. Job paused for automatic recovery when network is restored."
                        j.transition_to(DownloadJob.STATUS_INTERRUPTED)
                        db.session.commit()
                        logger.warning(f"Job #{job_id} marked as INTERRUPTED due to simulated offline state.")
                return

            # Check if this job should fail for demonstration
            if fail_this_job and step == 5:
                with self.app.app_context():
                    j = db.session.get(DownloadJob, job_id)
                    if j and j.status == DownloadJob.STATUS_DOWNLOADING:
                        j.error_message = "Simulated Transfer Error: Remote server timeout at 50% (DEMO failure simulation)."
                        j.transition_to(DownloadJob.STATUS_FAILED)
                        db.session.commit()
                        logger.warning(f"Job #{job_id} marked as FAILED due to deliberate demo injection.")
                return

            # Refresh job state to check cancellation or pause requests
            with self.app.app_context():
                j = db.session.get(DownloadJob, job_id)
                if not j:
                    return

                if j.cancel_requested:
                    j.transition_to(DownloadJob.STATUS_CANCELLED)
                    j.error_message = "User cancelled download job."
                    db.session.commit()
                    logger.info(f"Job #{job_id} safely CANCELLED upon request.")
                    return

                if j.pause_requested or self._pause_event.is_set():
                    j.transition_to(DownloadJob.STATUS_PAUSED)
                    db.session.commit()
                    logger.info(f"Job #{job_id} safely PAUSED at {j.progress_percent}%.")
                    return

                # Normal progress increment
                target_pct = step * 10.0
                j.progress_percent = target_pct
                total_est = (j.media_item.duration_seconds or 300) * 150000  # estimated bytes
                j.total_bytes = total_est
                j.bytes_processed = int(total_est * (target_pct / 100.0))
                db.session.commit()

            time.sleep(step_delay)

        # Job Completed Successfully
        with self.app.app_context():
            j = db.session.get(DownloadJob, job_id)
            if j and j.status == DownloadJob.STATUS_DOWNLOADING:
                # Write a simulated demonstration receipt file
                dest_dir = StorageService.ensure_directory(self.app.config.get("DOWNLOAD_DIR") / "demo")
                safe_title = "".join(c for c in (j.media_item.title if j.media_item else f"item_{job_id}") if c.isalnum() or c in (" ", "-", "_")).strip()
                sim_file = dest_dir / f"DEMO_{j.id}_{safe_title[:40]}.sim.txt"
                
                with open(sim_file, "w", encoding="utf-8") as f:
                    f.write(f"PlaylistPilot Demonstration Processing Receipt\n")
                    f.write(f"Job ID: {j.id}\n")
                    f.write(f"Title: {j.media_item.title if j.media_item else 'N/A'}\n")
                    f.write(f"Source ID: {j.media_item.source_id if j.media_item else 'N/A'}\n")
                    f.write(f"Status: COMPLETED (Simulated Demo Operation)\n")
                    f.write(f"Completed At: {datetime.now(timezone.utc).isoformat()}\n")
                    f.write(f"Notice: This is a verified demonstration artifact for academic presentation.\n")

                j.output_path = str(sim_file)
                j.progress_percent = 100.0
                j.transition_to(DownloadJob.STATUS_COMPLETED)
                db.session.commit()
                logger.info(f"Job #{job_id} completed successfully. Artifact saved: {sim_file.name}")

    def _execute_media_job(self, job_id: int):
        """Execute a local media processing or conversion job."""
        from app.services.media_service import MediaService
        with self.app.app_context():
            job = db.session.get(DownloadJob, job_id)
            if not job:
                return

            MediaService.process_media_job(job)
