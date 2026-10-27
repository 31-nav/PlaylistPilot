import json
from extensions import db
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob


def test_api_list_playlists(client, sample_playlist):
    res = client.get("/api/playlists")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] >= 1


def test_api_get_playlist_items(client, sample_playlist):
    res = client.get(f"/api/playlists/{sample_playlist.id}/items?page=1&per_page=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 10
    assert data["total_count"] == 105


def test_api_enqueue_and_status(client, sample_playlist, app):
    with app.app_context():
        item = MediaItem.query.first()
        item_id = item.id

    # Enqueue item
    res = client.post(
        "/api/queue",
        data=json.dumps({"item_ids": [item_id]}),
        content_type="application/json",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["added_count"] == 1

    # Check queue status
    status_res = client.get("/api/queue/status")
    assert status_res.status_code == 200
    s_data = status_res.get_json()
    assert s_data["success"] is True
    assert "counts" in s_data


def test_api_simulate_network_toggle(client):
    res = client.post("/api/simulate/network", data=json.dumps({}), content_type="application/json")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "simulated_network_offline" in data


def test_api_json_404(client):
    res = client.get("/api/nonexistent_endpoint")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False
    assert "status_code" in data


def test_api_validate_storage_path(client, tmp_path):
    check_dir = tmp_path / "api_test_dir"
    res = client.post(
        "/api/storage/validate-path",
        data=json.dumps({"path": str(check_dir)}),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["valid"] is True
    assert "free_formatted" in data


def test_api_download_job_file(client, app, sample_playlist, tmp_path):
    # Create sample media item and completed job with real dummy mp4 file
    test_mp4 = tmp_path / "test_lecture.mp4"
    test_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isomtestdata")

    with app.app_context():
        item = MediaItem.query.first()
        job = DownloadJob(
            media_item_id=item.id,
            status=DownloadJob.STATUS_COMPLETED,
            output_path=str(test_mp4),
            quality="best",
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    # Test downloading the completed file
    res = client.get(f"/api/jobs/{job_id}/download")
    assert res.status_code == 200
    assert res.mimetype == "video/mp4"
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert "test_lecture.mp4" in res.headers.get("Content-Disposition", "")
    assert res.data.startswith(b"\x00\x00\x00\x18ftypmp42")


def test_api_quick_download_single_video(client, app, monkeypatch):
    from app.services.youtube_metadata_service import YouTubeMetadataService

    def mock_fetch_video(url):
        return {
            "success": True,
            "video": {
                "id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "duration_seconds": 212,
                "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "uploader": "Rick Astley",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            }
        }

    monkeypatch.setattr(YouTubeMetadataService, "fetch_single_video_metadata", mock_fetch_video)

    res = client.post(
        "/api/download/quick",
        data=json.dumps({"url": "https://youtu.be/dQw4w9WgXcQ", "quality": "best"}),
        content_type="application/json",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["is_playlist"] is False
    assert "job_id" in data
    assert "download_url" in data
    assert data["video"]["id"] == "dQw4w9WgXcQ"


def test_youtube_video_id_parsing():
    from app.services.youtube_metadata_service import YouTubeMetadataService

    assert YouTubeMetadataService.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YouTubeMetadataService.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YouTubeMetadataService.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YouTubeMetadataService.extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YouTubeMetadataService.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YouTubeMetadataService.extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=abcdef123") == "dQw4w9WgXcQ"


def test_api_fetch_content_single_video(client, monkeypatch):
    from app.services.youtube_metadata_service import YouTubeMetadataService

    def mock_fetch(url):
        return {
            "success": True,
            "video": {
                "id": "abc12345678",
                "title": "Sample Tutorial Video",
                "duration_seconds": 300,
                "thumbnail_url": "https://img.youtube.com/vi/abc12345678/hqdefault.jpg",
                "uploader": "CodeChannel",
                "url": "https://www.youtube.com/watch?v=abc12345678",
            }
        }

    monkeypatch.setattr(YouTubeMetadataService, "fetch_single_video_metadata", mock_fetch)

    res = client.post(
        "/api/fetch",
        data=json.dumps({"url": "https://youtu.be/abc12345678"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["is_playlist"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "abc12345678"


def test_api_batch_download_selection(client, app):
    selected_items = [
        {"id": "vid_sel_1", "title": "Lecture 1", "duration_seconds": 120, "thumbnail_url": "/thumb1.jpg"},
        {"id": "vid_sel_2", "title": "Lecture 2", "duration_seconds": 240, "thumbnail_url": "/thumb2.jpg"},
        {"id": "vid_sel_3", "title": "Lecture 3", "duration_seconds": 360, "thumbnail_url": "/thumb3.jpg"},
    ]

    res = client.post(
        "/api/batch-download",
        data=json.dumps({"items": selected_items, "quality": "best"}),
        content_type="application/json",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] == 3
    assert len(data["jobs"]) == 3
    assert "download_url" in data["jobs"][0]


