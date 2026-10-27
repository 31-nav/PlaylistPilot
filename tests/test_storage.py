from pathlib import Path
from app.services.storage_service import StorageService


def test_format_bytes():
    assert StorageService.format_bytes(500) == "500.0 B"
    assert StorageService.format_bytes(1024) == "1.0 KB"
    assert StorageService.format_bytes(1048576) == "1.0 MB"
    assert StorageService.format_bytes(1073741824) == "1.0 GB"
    assert StorageService.format_bytes(None) == "Unknown"


def test_get_disk_info():
    info = StorageService.get_disk_info()
    assert "total_bytes" in info
    assert "free_bytes" in info
    assert "free_mb" in info
    assert "used_percent" in info
    assert info["total_bytes"] > 0


def test_validate_safe_path(tmp_path):
    base = tmp_path / "downloads"
    base.mkdir()

    # Valid sub-path
    safe_child = base / "media" / "video.mp4"
    assert StorageService.validate_safe_path(base, safe_child) is True

    # Path traversal attack attempting to escape
    evil_path = base / ".." / ".." / "system32" / "secret.txt"
    assert StorageService.validate_safe_path(base, evil_path) is False


def test_validate_download_directory(tmp_path):
    custom_dir = tmp_path / "custom_downloads"
    res = StorageService.validate_download_directory(str(custom_dir))
    assert res["valid"] is True
    assert res["path"] == str(custom_dir.resolve())
    assert custom_dir.exists()
    assert "free_formatted" in res

    # Empty path test
    empty_res = StorageService.validate_download_directory("")
    assert empty_res["valid"] is False


def test_get_suggested_paths(tmp_path):
    suggestions = StorageService.get_suggested_paths(tmp_path)
    assert len(suggestions) >= 1
    assert any(s["label"] == "Project Default" for s in suggestions)
