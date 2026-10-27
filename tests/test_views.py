from extensions import db
from app.models.media_item import MediaItem
from app.models.download_job import DownloadJob


def test_view_dashboard(client, sample_playlist):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Playlist" in res.data
    assert b"Queue Engine Execution State" in res.data


def test_view_about(client):
    res = client.get("/about")
    assert res.status_code == 200
    assert b"About PlaylistPilot" in res.data


def test_view_playlists_list(client, sample_playlist):
    res = client.get("/playlists")
    assert res.status_code == 200
    assert b"Playlists Repository" in res.data


def test_view_playlist_explorer(client, sample_playlist):
    res = client.get(f"/playlists/{sample_playlist.id}")
    assert res.status_code == 200
    assert b"Videos in Playlist" in res.data


def test_view_queue_screen(client, sample_playlist):
    res = client.get("/queue")
    assert res.status_code == 200
    assert b"Queue Manager" in res.data


def test_view_history_screen(client, sample_playlist, app):
    with app.app_context():
        item = MediaItem.query.first()
        job = DownloadJob(media_item_id=item.id, status=DownloadJob.STATUS_COMPLETED)
        db.session.add(job)
        db.session.commit()

    res = client.get("/history")
    assert res.status_code == 200
    assert b"Job Execution History" in res.data


def test_view_settings_screen(client, tmp_path):
    res = client.get("/settings")
    assert res.status_code == 200
    assert b"Configuration Parameters" in res.data
    assert b"Local System Download Path" in res.data

    custom_dir = tmp_path / "user_selected_downloads"

    # Test POST settings update with custom download directory
    post_res = client.post(
        "/settings",
        data={
            "download_directory": str(custom_dir),
            "youtube_api_key": "AIzaSyTestKey1234567890",
            "auto_retry": "on",
            "max_retries": "4",
            "queue_poll_interval": "1.5",
            "simulation_speed": "2.0",
        },
        follow_redirects=True,
    )
    assert post_res.status_code == 200
    assert b"Settings and storage path saved successfully" in post_res.data
