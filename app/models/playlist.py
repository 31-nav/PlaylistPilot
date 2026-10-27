from datetime import datetime, timezone
import json
from extensions import db


class Playlist(db.Model):
    __tablename__ = "playlists"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(50), nullable=False, default="demo")  # demo, youtube, local
    source_url = db.Column(db.String(500), nullable=True)
    source_id = db.Column(db.String(100), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    item_count = db.Column(db.Integer, default=0)
    import_status = db.Column(db.String(50), default="completed")  # pending, completed, failed
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    user = db.relationship("User", back_populates="playlists")
    media_items = db.relationship("MediaItem", back_populates="playlist", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self, include_items=False):
        meta = {}
        if self.metadata_json:
            try:
                meta = json.loads(self.metadata_json)
            except Exception:
                meta = {}
        data = {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "item_count": self.item_count,
            "import_status": self.import_status,
            "metadata": meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.media_items.order_by("position").all()]
        return data

    def __repr__(self):
        return f"<Playlist id={self.id} title='{self.title[:30]}'>"
