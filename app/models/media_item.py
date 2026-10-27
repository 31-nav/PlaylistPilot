from datetime import datetime, timezone
import json
from extensions import db


class MediaItem(db.Model):
    __tablename__ = "media_items"

    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=True, index=True)
    source_id = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=True)
    media_type = db.Column(db.String(50), default="video")  # video, audio, local_file
    thumbnail_url = db.Column(db.String(500), nullable=True)
    position = db.Column(db.Integer, default=0)
    availability_status = db.Column(db.String(50), default="available")  # available, unavailable, private
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    playlist = db.relationship("Playlist", back_populates="media_items")
    jobs = db.relationship("DownloadJob", back_populates="media_item", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def formatted_duration(self):
        if not self.duration_seconds:
            return "--:--"
        mins, secs = divmod(self.duration_seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    def to_dict(self):
        meta = {}
        if self.metadata_json:
            try:
                meta = json.loads(self.metadata_json)
            except Exception:
                meta = {}
        # Latest job status if any
        latest_job = self.jobs.order_by(db.desc("created_at")).first()
        return {
            "id": self.id,
            "playlist_id": self.playlist_id,
            "source_id": self.source_id,
            "title": self.title,
            "duration_seconds": self.duration_seconds,
            "formatted_duration": self.formatted_duration,
            "media_type": self.media_type,
            "thumbnail_url": self.thumbnail_url,
            "position": self.position,
            "availability_status": self.availability_status,
            "metadata": meta,
            "latest_job_status": latest_job.status if latest_job else None,
            "latest_job_id": latest_job.id if latest_job else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<MediaItem id={self.id} title='{self.title[:30]}'>"
