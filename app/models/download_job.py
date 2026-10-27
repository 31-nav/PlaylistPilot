from datetime import datetime, timezone
from extensions import db


class DownloadJob(db.Model):
    __tablename__ = "download_jobs"

    STATUS_QUEUED = "queued"
    STATUS_DOWNLOADING = "downloading"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_INTERRUPTED = "interrupted"
    STATUS_CANCELLED = "cancelled"

    VALID_TRANSITIONS = {
        STATUS_QUEUED: {STATUS_DOWNLOADING, STATUS_CANCELLED},
        STATUS_DOWNLOADING: {STATUS_COMPLETED, STATUS_PAUSED, STATUS_FAILED, STATUS_INTERRUPTED, STATUS_CANCELLED},
        STATUS_PAUSED: {STATUS_QUEUED, STATUS_CANCELLED},
        STATUS_FAILED: {STATUS_QUEUED},  # Retry
        STATUS_INTERRUPTED: {STATUS_QUEUED, STATUS_CANCELLED},  # Resume/Retry
        STATUS_CANCELLED: {STATUS_QUEUED},  # Allow re-queueing cancelled jobs
        STATUS_COMPLETED: set(),  # Terminal state
    }

    id = db.Column(db.Integer, primary_key=True)
    media_item_id = db.Column(
        db.Integer,
        db.ForeignKey("media_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type = db.Column(db.String(50), nullable=False, default="youtube_download")  # youtube_download, youtube_audio, local_process, media_convert
    quality = db.Column(db.String(50), nullable=True, default="best")  # best, 1080p, 720p, 480p, 360p, audio_mp3
    status = db.Column(db.String(50), nullable=False, default=STATUS_QUEUED, index=True)
    priority = db.Column(db.Integer, default=0, index=True)  # Higher values = higher priority
    progress_percent = db.Column(db.Float, default=0.0)
    bytes_processed = db.Column(db.BigInteger, default=0)
    total_bytes = db.Column(db.BigInteger, default=0)
    output_path = db.Column(db.String(500), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    cancel_requested = db.Column(db.Boolean, default=False)
    pause_requested = db.Column(db.Boolean, default=False)
    idempotency_key = db.Column(db.String(100), nullable=True, unique=True, index=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    user = db.relationship("User", back_populates="jobs")
    media_item = db.relationship("MediaItem", back_populates="jobs")

    def can_transition_to(self, target_status: str) -> bool:
        """Check if transitioning from current status to target status is valid."""
        return target_status in self.VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, target_status: str) -> bool:
        """Safely transition to target status if allowed."""
        if not self.can_transition_to(target_status):
            return False
        
        now = datetime.now(timezone.utc)
        self.status = target_status
        self.updated_at = now
        
        if target_status == self.STATUS_DOWNLOADING and not self.started_at:
            self.started_at = now
        elif target_status in (self.STATUS_COMPLETED, self.STATUS_FAILED, self.STATUS_CANCELLED):
            self.completed_at = now
        elif target_status == self.STATUS_QUEUED:
            self.cancel_requested = False
            self.pause_requested = False
            
        return True

    @property
    def is_terminal(self) -> bool:
        return self.status in (self.STATUS_COMPLETED, self.STATUS_CANCELLED, self.STATUS_FAILED)

    @property
    def is_retryable(self) -> bool:
        return self.status in (self.STATUS_FAILED, self.STATUS_INTERRUPTED) and self.retry_count < self.max_retries

    @property
    def is_demo(self) -> bool:
        return self.job_type == "demo_download"

    def to_dict(self):
        item_data = None
        if self.media_item:
            item_data = {
                "id": self.media_item.id,
                "title": self.media_item.title,
                "source_id": self.media_item.source_id,
                "duration_seconds": self.media_item.duration_seconds,
                "formatted_duration": self.media_item.formatted_duration,
                "thumbnail_url": self.media_item.thumbnail_url,
                "playlist_id": self.media_item.playlist_id,
                "playlist_title": self.media_item.playlist.title if self.media_item.playlist else None,
            }

        return {
            "id": self.id,
            "media_item_id": self.media_item_id,
            "media_item": item_data,
            "job_type": self.job_type,
            "quality": self.quality or "best",
            "is_demo": self.is_demo,
            "status": self.status,
            "priority": self.priority,
            "progress_percent": round(self.progress_percent, 1),
            "bytes_processed": self.bytes_processed,
            "total_bytes": self.total_bytes,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "is_retryable": self.is_retryable,
            "cancel_requested": self.cancel_requested,
            "pause_requested": self.pause_requested,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "download_url": f"/api/jobs/{self.id}/download" if (self.status == self.STATUS_COMPLETED and self.output_path) else None,
        }

    def __repr__(self):
        return f"<DownloadJob id={self.id} status='{self.status}' priority={self.priority}>"
