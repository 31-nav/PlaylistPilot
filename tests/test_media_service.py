from app.services.media_service import MediaService


def test_inspect_nonexistent_file():
    info = MediaService.inspect_local_file("c:/nonexistent_video_path.mp4")
    assert info["valid"] is False
    assert "File does not exist" in info["error"]


def test_inspect_unsupported_extension(tmp_path):
    bad_file = tmp_path / "document.pdf"
    bad_file.write_text("dummy pdf content")
    info = MediaService.inspect_local_file(str(bad_file))
    assert info["valid"] is False
    assert "Unsupported media format" in info["error"]


def test_inspect_valid_media_file(tmp_path):
    sample_mp4 = tmp_path / "lecture.mp4"
    sample_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")
    info = MediaService.inspect_local_file(str(sample_mp4))
    assert info["valid"] is True
    assert info["extension"] == ".mp4"
    assert info["is_video"] is True
    assert info["size_bytes"] > 0


def test_download_youtube_media_mock(tmp_path, monkeypatch):
    class MockYoutubeDL:
        def __init__(self, opts):
            self.opts = opts
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def extract_info(self, url, download=True):
            out_file = tmp_path / "mock_download.mp4"
            out_file.write_bytes(b"mock video payload")
            if "progress_hooks" in self.opts:
                for h in self.opts["progress_hooks"]:
                    h({"status": "downloading", "downloaded_bytes": 1000, "total_bytes": 1000, "filename": str(out_file)})
                    h({"status": "finished", "total_bytes": 1000, "filename": str(out_file)})
            return {"title": "Test Video", "id": "12345"}
        def prepare_filename(self, info):
            return str(tmp_path / "mock_download.mp4")

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", MockYoutubeDL)

    progresses = []
    res = MediaService.download_youtube_media(
        video_id_or_url="https://youtube.com/watch?v=12345",
        output_dir=tmp_path,
        progress_callback=lambda p: progresses.append(p),
    )
    assert res["success"] is True
    assert "mock_download.mp4" in res["output_path"]
    assert len(progresses) > 0


def test_ytdlp_playlist_fetch_mock(monkeypatch):
    from app.services.youtube_metadata_service import YouTubeMetadataService
    class MockYoutubeDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def extract_info(self, url, download=False):
            return {
                "id": "PLmock",
                "title": "Mock Playlist",
                "entries": [
                    {"id": "vid_1", "title": "Lecture 1", "duration": 180},
                    {"id": "vid_2", "title": "Lecture 2", "duration": 240},
                ]
            }

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", MockYoutubeDL)

    res = YouTubeMetadataService.fetch_playlist_with_ytdlp("PLmock")
    assert res["success"] is True
    assert res["playlist"]["title"] == "Mock Playlist"
    assert len(res["items"]) == 2
    assert res["items"][0]["source_id"] == "vid_1"
