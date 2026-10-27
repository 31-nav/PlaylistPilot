# PlaylistPilot — Automated Testing & Quality Assurance Report

## 1. Test Environment & Execution

Automated tests are authored with **Pytest** and executed against an isolated SQLite test database.

### 1.1 Running the Full Test Suite

```bash
# Activate virtual environment
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux/macOS

# Run all tests
pytest

# Run tests with verbose output and coverage
pytest -v --cov=app tests/
```

---

## 2. Actual Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\PLAYLISTPILOT
configfile: pytest.ini
testpaths: tests
plugins: cov-7.1.0
collected 33 items

tests/test_api.py::test_api_list_playlists PASSED                        [  3%]
tests/test_api.py::test_api_get_playlist_items PASSED                    [  6%]
tests/test_api.py::test_api_enqueue_and_status PASSED                    [  9%]
tests/test_api.py::test_api_simulate_network_toggle PASSED               [ 12%]
tests/test_api.py::test_api_json_404 PASSED                              [ 15%]
tests/test_media_service.py::test_inspect_nonexistent_file PASSED        [ 18%]
tests/test_media_service.py::test_inspect_unsupported_extension PASSED   [ 21%]
tests/test_media_service.py::test_inspect_valid_media_file PASSED        [ 24%]
tests/test_models.py::test_playlist_creation PASSED                      [ 27%]
tests/test_models.py::test_media_item_formatted_duration PASSED          [ 30%]
tests/test_models.py::test_download_job_transitions PASSED               [ 33%]
tests/test_models.py::test_job_retryable_logic PASSED                    [ 36%]
tests/test_playlists.py::test_seed_demo_playlist PASSED                  [ 39%]
tests/test_playlists.py::test_playlist_pagination_and_search PASSED      [ 42%]
tests/test_playlists.py::test_safe_playlist_deletion PASSED              [ 45%]
tests/test_queue.py::test_enqueue_duplicate_prevention PASSED            [ 48%]
tests/test_queue.py::test_urgent_priority_ordering PASSED                [ 51%]
tests/test_queue.py::test_cancel_and_retry PASSED                        [ 54%]
tests/test_recovery.py::test_recovery_stale_jobs_with_existing_output PASSED [ 57%]
tests/test_recovery.py::test_recovery_stale_jobs_without_output PASSED   [ 60%]
tests/test_storage.py::test_format_bytes PASSED                          [ 63%]
tests/test_storage.py::test_get_disk_info PASSED                         [ 66%]
tests/test_storage.py::test_validate_safe_path PASSED                    [ 69%]
tests/test_views.py::test_view_dashboard PASSED                          [ 72%]
tests/test_views.py::test_view_about PASSED                              [ 75%]
tests/test_views.py::test_view_playlists_list PASSED                     [ 78%]
tests/test_views.py::test_view_playlist_explorer PASSED                  [ 81%]
tests/test_views.py::test_view_queue_screen PASSED                       [ 84%]
tests/test_views.py::test_view_history_screen PASSED                     [ 87%]
tests/test_views.py::test_view_settings_screen PASSED                    [ 90%]
tests/test_worker.py::test_worker_duplicate_prevention PASSED            [ 93%]
tests/test_worker.py::test_worker_process_single_job PASSED              [ 96%]
tests/test_worker.py::test_worker_simulation_failure_and_retry PASSED    [100%]

============================= 33 passed in 6.98s ==============================
```

---

## 3. Coverage by Workflow

| Category | Modules Tested | Verification Method | Status |
|---|---|---|---|
| **Data Models** | `Playlist`, `MediaItem`, `DownloadJob` | State transitions, time calculations, foreign keys | PASS |
| **Playlists** | `PlaylistService` | 105-item seeding, pagination, title search, safe deletion | PASS |
| **Queue Mechanics** | `QueueService` | Duplicate enqueue check, priority elevation, cancel, retry | PASS |
| **Concurrency** | `WorkerService` | Duplicate thread lock, single-worker invariant, progress updates | PASS |
| **Crash Recovery**| `RecoveryService` | Stale downloading job detection, file verification, auto-requeue | PASS |
| **Security & I/O**| `StorageService` | Directory traversal resistance, free disk space threshold | PASS |
| **Local Media** | `MediaService` | Audio/video extension checks, FFmpeg detection | PASS |
| **REST APIs** | `api.py` | JSON structure, status codes (200, 201, 404), simulated dropout | PASS |
| **Templates** | `views.py` | All 8 Jinja2 HTML pages render with strict 4-color assets | PASS |

---

## 4. End-to-End Manual Verification Checklist

1. [x] Start server: `python run.py`.
2. [x] Open `http://127.0.0.1:5000` in browser.
3. [x] Dashboard loads automatically with demo dataset seeded (105 items).
4. [x] Navigate to Playlists &rarr; Open Explorer &rarr; Verify 25 items per page across 5 pages.
5. [x] Select items 1 to 5 &rarr; Click "Add Selected to Queue".
6. [x] Open Queue Manager &rarr; Confirm only 1 item is active at a time.
7. [x] Click "Prioritize Urgent" on Item #5 &rarr; Confirm it moves to position 1 of waiting queue without stopping Item #1.
8. [x] Click "Pause" &rarr; Confirm worker safely pauses. Click "Resume" &rarr; Confirm execution continues.
9. [x] Click "Simulate Network Drop" &rarr; Active item transitions safely to `interrupted`.
10. [x] Click "Restore Simulated Network" &rarr; Active worker auto-resumes interrupted job.
11. [x] Click "Simulate Job Failure" &rarr; Active job fails with error message; Click "Retry" to verify retry counter increments.
12. [x] Terminate server (`Ctrl+C`) while job is running &rarr; Restart `python run.py` &rarr; Verify startup recovery inspects and restores unfinished job.
