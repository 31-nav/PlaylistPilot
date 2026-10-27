import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from extensions import db
from app.models.playlist import Playlist
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob


class PlaylistService:
    DEMO_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample_playlist.json"

    @classmethod
    def seed_demo_playlist(cls, force: bool = False) -> Playlist:
        """
        Seed the 105-item demo educational playlist into SQLite.
        If already present and force=False, returns the existing record.
        """
        existing = Playlist.query.filter_by(source_type="demo", source_id="PL_DEMO_MCA_PYTHON_2026").first()
        if existing and not force:
            return existing

        if not cls.DEMO_JSON_PATH.exists():
            raise FileNotFoundError(f"Demo playlist JSON file not found at {cls.DEMO_JSON_PATH}")

        with open(cls.DEMO_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if existing and force:
            # Delete old items if re-seeding
            MediaItem.query.filter_by(playlist_id=existing.id).delete()
            playlist = existing
            playlist.title = data.get("title", "Demo Playlist")
            playlist.description = data.get("description", "")
            playlist.thumbnail_url = data.get("thumbnail_url", "/static/images/placeholder-thumbnail.svg")
            playlist.item_count = len(data.get("items", []))
            playlist.import_status = "completed"
            playlist.metadata_json = json.dumps({"is_demo": True, "total_generated": len(data.get("items", []))})
        else:
            playlist = Playlist(
                title=data.get("title", "Demo Playlist"),
                source_type="demo",
                source_id=data.get("source_id", "PL_DEMO_MCA_PYTHON_2026"),
                source_url=data.get("source_url", "https://playlistpilot.local/demo"),
                description=data.get("description", ""),
                thumbnail_url=data.get("thumbnail_url", "/static/images/placeholder-thumbnail.svg"),
                item_count=len(data.get("items", [])),
                import_status="completed",
                metadata_json=json.dumps({"is_demo": True, "total_generated": len(data.get("items", []))}),
            )
            db.session.add(playlist)
            db.session.flush()

        items = []
        for raw in data.get("items", []):
            item = MediaItem(
                playlist_id=playlist.id,
                source_id=raw.get("source_id", f"item_{raw.get('position', 1)}"),
                title=raw.get("title", "Untitled Item"),
                duration_seconds=raw.get("duration_seconds", 300),
                media_type=raw.get("media_type", "video"),
                thumbnail_url=raw.get("thumbnail_url", "/static/images/placeholder-thumbnail.svg"),
                position=raw.get("position", 0),
                availability_status=raw.get("availability_status", "available"),
                metadata_json=json.dumps(raw.get("metadata", {})),
            )
            items.append(item)

        db.session.bulk_save_objects(items)
        db.session.commit()
        return playlist

    @staticmethod
    def get_all_playlists(search: Optional[str] = None, sort_by: str = "created_at", order: str = "desc") -> List[Playlist]:
        query = Playlist.query
        if search:
            query = query.filter(Playlist.title.ilike(f"%{search}%"))

        col = getattr(Playlist, sort_by, Playlist.created_at)
        if order == "desc":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())

        return query.all()

    @staticmethod
    def get_playlist_by_id(playlist_id: int) -> Optional[Playlist]:
        return db.session.get(Playlist, playlist_id)

    @staticmethod
    def get_playlist_items(
        playlist_id: int,
        page: int = 1,
        per_page: int = 25,
        search: Optional[str] = None,
        sort_by: str = "position",
        order: str = "asc",
        module_filter: Optional[str] = None,
    ) -> Tuple[List[MediaItem], int, int]:
        """
        Get paginated media items for a playlist.
        Returns: (items, total_count, total_pages)
        """
        query = MediaItem.query.filter_by(playlist_id=playlist_id)

        if search:
            query = query.filter(MediaItem.title.ilike(f"%{search}%"))

        if module_filter:
            query = query.filter(MediaItem.metadata_json.like(f"%{module_filter}%"))

        col = getattr(MediaItem, sort_by, MediaItem.position)
        if order == "desc":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())

        total_count = query.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()

        return items, total_count, total_pages

    @staticmethod
    def delete_playlist(playlist_id: int) -> bool:
        """
        Delete playlist metadata safely.
        Dissociates media items by setting playlist_id to None so jobs and
        audit records are preserved without silent data loss.
        """
        playlist = db.session.get(Playlist, playlist_id)
        if not playlist:
            return False

        # Dissociate items so foreign keys don't cascade delete job history
        MediaItem.query.filter_by(playlist_id=playlist_id).update({"playlist_id": None})
        db.session.delete(playlist)
        db.session.commit()
        return True

    @staticmethod
    def import_custom_playlist(
        title: str,
        source_type: str,
        items_data: List[Dict[str, Any]],
        source_url: Optional[str] = None,
        source_id: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Playlist:
        """Create a new playlist and its media items."""
        playlist = Playlist(
            title=title,
            source_type=source_type,
            source_url=source_url,
            source_id=source_id,
            description=description,
            thumbnail_url=thumbnail_url or "/static/images/placeholder-thumbnail.svg",
            item_count=len(items_data),
            import_status="completed",
            metadata_json=json.dumps(metadata or {}),
        )
        db.session.add(playlist)
        db.session.flush()

        items = []
        for idx, raw in enumerate(items_data, 1):
            item = MediaItem(
                playlist_id=playlist.id,
                source_id=raw.get("source_id", f"item_{idx}"),
                title=raw.get("title", f"Item #{idx}"),
                duration_seconds=raw.get("duration_seconds", 0),
                media_type=raw.get("media_type", "video"),
                thumbnail_url=raw.get("thumbnail_url", "/static/images/placeholder-thumbnail.svg"),
                position=raw.get("position", idx),
                availability_status=raw.get("availability_status", "available"),
                metadata_json=json.dumps(raw.get("metadata", {})),
            )
            items.append(item)

        db.session.bulk_save_objects(items)
        db.session.commit()
        return playlist
