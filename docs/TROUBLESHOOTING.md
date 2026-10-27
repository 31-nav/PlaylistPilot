# PlaylistPilot — Troubleshooting & Diagnostics Guide

This document lists known operational scenarios, error codes, and troubleshooting steps.

---

## 1. Installation & Environment

### Issue: `python` command is not recognized on Windows
**Symptom:** PowerShell displays `Python was not found...`  
**Resolution:**  
On Windows, use the Python Launcher `py`:
```powershell
py -3.11 -m venv .venv
# or
py -m venv .venv
.venv\Scripts\activate
```

### Issue: `pip` fails to install dependencies
**Symptom:** Permission error or build failure during `pip install -r requirements.txt`.  
**Resolution:**  
Ensure your virtual environment is active and upgrade `pip`:
```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt -r requirements-dev.txt
```

---

## 2. Database & Persistence

### Issue: SQLite `database is locked` error
**Symptom:** Concurrency exception when multiple threads attempt writes simultaneously.  
**Cause:** SQLite allows multiple readers but only one exclusive writer lock at any time.  
**Resolution:**  
PlaylistPilot enforces short-lived database transactions:
1. Long-running I/O or sleep calls occur **outside** of database transactions.
2. The background worker uses isolated application contexts (`with app.app_context():`).
3. If database file is stuck, stop any running server instances and remove `instance/test_playlistpilot.db` if testing.

### Issue: Missing demo playlist on startup
**Symptom:** Playlists list is empty.  
**Resolution:**  
Run the seed script manually:
```bash
python scripts/seed_demo_data.py
```

---

## 3. Queue & Worker Diagnostics

### Issue: Queue appears paused or won't start
**Checklist:**
1. Check available disk space: If free space is below `MIN_FREE_SPACE_MB` (default 200MB), the worker automatically pauses to protect the host OS.
2. Check simulated network state: Verify whether the top header pill displays `Offline (Simulated)`. If so, click "Restore Simulated Network".
3. Check worker thread status via API:
   ```bash
   curl http://127.0.0.1:5000/api/queue/status
   ```

### Issue: Job stuck in `downloading` after crash
**Resolution:**  
Simply restart the application:
```bash
python run.py
```
`RecoveryService` will automatically detect the stale job on startup and transition it to `interrupted` or requeue it.

---

## 4. YouTube API Integration

### Issue: `QUOTA_EXCEEDED` error
**Symptom:** API returns `YouTube API quota exceeded or key unauthorized (HTTP 403)`.  
**Resolution:**  
The official YouTube Data API v3 enforces a default daily quota limit (10,000 units).  
- Switch to **Demonstration Mode** by using the built-in 105-item educational playlist.
- Ensure your API key is correctly entered in `Settings` and has the YouTube Data API v3 enabled in Google Cloud Console.

### Issue: `INVALID_URL` error
**Symptom:** System rejects the input URL.  
**Resolution:**  
Ensure the playlist link contains a valid `list=PL...` query parameter:
- Correct: `https://www.youtube.com/playlist?list=PLr6-GrHGFlycQgeCG5VvK2f7wD3G0_1GZ`
- Incorrect: Standard video URLs lacking `list=`.

---

## 5. Local Media & FFmpeg Integration

### Issue: `FFMPEG_MISSING` error
**Symptom:** "FFmpeg is not installed or not in PATH."  
**Resolution:**  
Install FFmpeg on your host machine:
- **Windows (Winget):** `winget install Gyan.FFmpeg`
- **Windows (Chocolatey):** `choco install ffmpeg`
- **macOS (Homebrew):** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install -y ffmpeg`  
Restart your terminal after installation so PATH is refreshed.
