import os
import shutil
from pathlib import Path
from typing import Dict, Any, Union


class StorageService:
    @staticmethod
    def format_bytes(num_bytes: Union[int, float]) -> str:
        """Format bytes into human-readable string (KB, MB, GB)."""
        if num_bytes is None or num_bytes < 0:
            return "Unknown"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num_bytes < 1024.0 or unit == "TB":
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} GB"

    @classmethod
    def get_disk_info(cls, target_path: Union[str, Path] = None) -> Dict[str, Any]:
        """
        Get total, used, and free disk space in bytes and human-readable format.
        Safe against non-existent paths.
        """
        if target_path is None:
            target_path = Path.cwd()
        else:
            target_path = Path(target_path)
            if not target_path.exists():
                target_path = Path.cwd()

        try:
            total, used, free = shutil.disk_usage(target_path)
            free_mb = free / (1024 * 1024)
            used_percent = (used / total * 100) if total > 0 else 0
            
            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "free_mb": round(free_mb, 1),
                "total_formatted": cls.format_bytes(total),
                "used_formatted": cls.format_bytes(used),
                "free_formatted": cls.format_bytes(free),
                "used_percent": round(used_percent, 1),
                "path": str(target_path),
                "is_low_space": free_mb < 200,  # Warning if under 200MB
            }
        except Exception as e:
            return {
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "free_mb": 0.0,
                "total_formatted": "Unknown",
                "used_formatted": "Unknown",
                "free_formatted": "Unknown",
                "used_percent": 0.0,
                "path": str(target_path),
                "is_low_space": False,
                "error": str(e),
            }

    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Create directory safely if it does not exist."""
        p = Path(path).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def validate_safe_path(base_dir: Union[str, Path], user_path: Union[str, Path]) -> bool:
        """
        Prevent path traversal attacks. Ensure user_path is within base_dir.
        """
        try:
            resolved_base = Path(base_dir).resolve()
            resolved_target = (resolved_base / user_path).resolve() if not Path(user_path).is_absolute() else Path(user_path).resolve()
            return resolved_base in resolved_target.parents or resolved_base == resolved_target
        except Exception:
            return False

    @staticmethod
    def safe_delete_file(file_path: Union[str, Path]) -> bool:
        """Safely delete a temporary file if it exists."""
        try:
            p = Path(file_path)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            pass
        return False

    @classmethod
    def validate_download_directory(cls, target_path: str) -> Dict[str, Any]:
        """Validate that target_path exists or can be created, and is writable."""
        if not target_path or not str(target_path).strip():
            return {"valid": False, "error": "Download path cannot be empty."}

        try:
            p = Path(target_path).resolve()
            p.mkdir(parents=True, exist_ok=True)

            # Test write access with temporary verification file
            test_file = p / ".playlistpilot_write_test.tmp"
            test_file.write_text("test_write_access", encoding="utf-8")
            if test_file.exists():
                test_file.unlink()

            disk_info = cls.get_disk_info(p)
            return {
                "valid": True,
                "path": str(p),
                "free_formatted": disk_info.get("free_formatted", "Unknown"),
                "free_mb": disk_info.get("free_mb", 0.0),
                "disk_info": disk_info,
            }
        except Exception as e:
            return {"valid": False, "error": f"Cannot use selected path: {str(e)}"}

    @classmethod
    def get_suggested_paths(cls, app_download_dir: Union[str, Path] = None) -> list:
        """Return quick-pick local directory choices on the user's host system."""
        suggestions = []

        if app_download_dir:
            suggestions.append({
                "label": "Project Default",
                "path": str(Path(app_download_dir).resolve()),
            })

        home = Path.home()

        # Windows/macOS/Linux Downloads folder
        downloads = home / "Downloads"
        if downloads.exists():
            suggestions.append({
                "label": "System Downloads",
                "path": str(downloads.resolve()),
            })

        # Videos folder
        videos = home / "Videos"
        if videos.exists():
            suggestions.append({
                "label": "System Videos",
                "path": str(videos.resolve()),
            })

        # Desktop folder
        desktop = home / "Desktop"
        if desktop.exists():
            suggestions.append({
                "label": "Desktop",
                "path": str(desktop.resolve()),
            })

        return suggestions
