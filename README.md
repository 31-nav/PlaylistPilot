# PlaylistPilot — Smart Playlist & Batch Job Manager

> **Tagline:** *Your Playlist. Your Queue. Your Control.*  
> **Academic Project:** Master of Computer Applications (MCA) — Advanced Python Web Application  
> **Status:** Production-Ready & Verified (33/33 Automated Tests Passing)

---

## 1. Abstract & Project Summary

When managing educational playlists containing 100, 200, 360, or more video lectures, manually tracking items or relying on browser tabs is fragile, resource-heavy, and prone to connection loss. 

**PlaylistPilot** is an open-source, local-first Python web application designed to simplify playlist and batch media management. It delivers an ACID-compliant persistent SQLite queue, sequential background execution, priority promotion, pause/resume coordination, and deterministic crash recovery. 

The application operates completely offline with a built-in **Demonstration Mode** containing 105 pre-generated curricular records, allowing complete evaluation without API keys or an active internet connection.

---

## 2. Problem Statement

Learners and researchers frequently struggle with large educational video courses due to:
- **No selective batch control:** Inability to select specific subsets of 100+ item playlists.
- **Queue volatility:** In-memory queues lose all progress if the browser closes or the laptop reboots.
- **Uncontrolled network congestion:** Naive scripts launch 100 simultaneous downloads, exhausting bandwidth and freezing laptops.
- **Lack of priority management:** Urgent lectures cannot jump ahead of long waiting lists without stopping current transfers.
- **Vulnerability to connection drops:** Abrupt network loss fails entire batches without saving checkpoints.

---

## 3. Proposed Solution

PlaylistPilot resolves these challenges by introducing:
1. **Local-First Persistence:** SQLite database storing all playlists, media items, and execution audit history.
2. **Dedicated Single-Worker Queue:** Strictly enforces sequential processing (`MAX_WORKERS=1`), bounded hardware usage, and thread safety.
3. **Crash & Reboot Recovery:** Automatically reconciles interrupted transfers upon application startup.
4. **Urgent Priority Promotion:** Moves critical items to the front of the waiting queue without disrupting the active job.
5. **Demonstration Mode with Fault Injection:** Provides test buttons to simulate network drops and server timeouts for academic examination.
6. **Strict 4-Color UI with 3D Depth:** A cohesive visual aesthetic using Black, Red, Gray, and White with tactile buttons and raised surfaces.

---

## 4. Key Features

- **Zero-Credential Demonstration Mode:** 105 pre-generated lectures loaded out-of-the-box.
- **Sequential Background Processing:** Dedicated thread-safe worker with checkpoint progress updates.
- **Interactive Queue Controls:** Start, Pause, Resume, Cancel, and Retry failed jobs.
- **Urgent Priority Elevation:** Instantly re-order waiting items with FIFO tie-breaking.
- **Deterministic Crash Recovery:** Inspects disk artifacts on startup and auto-requeues interrupted work.
- **Simulated Network Interruption & Restoration:** Live test toggle for demonstrating fault recovery.
- **Storage Safety Checks:** Verifies disk space threshold and prevents directory traversal attacks.
- **Optional External Integrations:** Official YouTube Data API v3 for metadata; FFmpeg for authorized local media audio extraction and format conversion.

---

## 5. Website Screens & Workflows

1. **Dashboard (`/` or `/dashboard`):** Real-time queue metrics, disk capacity gauge, active job monitor, overall progress bar, and quick import controls.
2. **Playlists Catalog (`/playlists`):** Overview of all imported playlists, item counts, source indicators, and metadata management.
3. **Playlist Explorer (`/playlists/<id>`):** Paginated explorer (25 items/page) with multi-select checkboxes, search filters, and "Add Selected / Add All" queue actions.
4. **Queue Manager (`/queue`):** Central command screen displaying the active worker, waiting queue, priority adjustments, and pause/resume controls.
5. **Job History (`/history`):** Complete execution audit log with status filtering (completed, failed, interrupted, cancelled) and instant retry buttons.
6. **Settings (`/settings`):** Configuration of retry limits, storage thresholds, simulation speeds, and optional API credentials.
7. **About (`/about`):** Architecture overview, viva demonstration script, and responsible-use statements.

---

## 6. Technology Stack

- **Language:** Python 3.11 / 3.12 / 3.13
- **Web Framework:** Flask 3.1+ (Application Factory pattern)
- **Database / ORM:** SQLite 3 & SQLAlchemy 2.0+ (Flask-SQLAlchemy 3.1+)
- **Concurrency:** Standard library `threading.Thread`, `threading.Lock`, `threading.Event`
- **Frontend:** Semantic HTML5, Vanilla CSS3 (Custom 3D depth system), Vanilla JavaScript (Fetch API)
- **Design Tokens:** Strict Four-Color Palette: Black (`#111111`), Red (`#E62117`), Gray (`#808080`), White (`#FFFFFF`)
- **Testing:** Pytest 8.0+, Pytest-Cov

---

## 7. Folder Structure

```
PlaylistPilot/
├── app.py                      # WSGI entrypoint
├── run.py                      # Local development runner
├── config.py                   # Environment configurations
├── extensions.py               # Shared extensions (SQLAlchemy)
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Testing dependencies
├── .env.example                # Configuration template
├── .gitignore                  # Git ignore rules
├── pytest.ini                  # Pytest configuration
├── LICENSE                     # MIT License
├── README.md                   # Complete documentation
│
├── instance/                   # Runtime SQLite databases
│   └── playlistpilot.db
│
├── app/
│   ├── __init__.py             # Flask application factory
│   ├── models/                 # SQLAlchemy data models
│   │   ├── playlist.py
│   │   ├── media_item.py
│   │   └── download_job.py
│   ├── routes/                 # Flask blueprints & API
│   │   ├── dashboard.py
│   │   ├── playlists.py
│   │   ├── queue.py
│   │   ├── history.py
│   │   ├── settings.py
│   │   └── api.py
│   ├── services/               # Core business services
│   │   ├── playlist_service.py
│   │   ├── queue_service.py
│   │   ├── worker_service.py
│   │   ├── recovery_service.py
│   │   ├── storage_service.py
│   │   ├── media_service.py
│   │   └── youtube_metadata_service.py
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── playlists.html
│   │   ├── playlist_explorer.html
│   │   ├── queue.html
│   │   ├── history.html
│   │   ├── settings.html
│   │   ├── about.html
│   │   └── errors/
│   └── static/                 # Static assets
│       ├── css/
│       │   ├── design-system.css
│       │   ├── main.css
│       │   ├── components.css
│       │   └── responsive.css
│       ├── js/
│       │   ├── app.js
│       │   ├── dashboard.js
│       │   ├── playlist.js
│       │   ├── queue.js
│       │   ├── history.js
│       │   └── notifications.js
│       └── images/
│           └── placeholder-thumbnail.svg
│
├── data/                       # Seed dataset (105 educational items)
│   └── sample_playlist.json
├── downloads/                  # Output storage for downloads & artifacts
├── scripts/
│   ├── init_db.py              # Schema initialization script
│   └── seed_demo_data.py       # Standalone demo seeding script
├── tests/                      # Automated test suite (33 tests)
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_playlists.py
│   ├── test_queue.py
│   ├── test_worker.py
│   ├── test_recovery.py
│   ├── test_storage.py
│   ├── test_media_service.py
│   ├── test_api.py
│   └── test_views.py
└── docs/                       # Academic documentation
    ├── ARCHITECTURE.md
    ├── DATABASE_SCHEMA.md
    ├── PROJECT_REPORT.md
    ├── TESTING.md
    ├── TROUBLESHOOTING.md
    ├── VIVA_QUESTIONS.md
    └── DEVELOPMENT_PLAN.md
```

---

## 8. Installation & Setup (Windows / macOS / Linux)

### Prerequisites
- Python 3.11, 3.12, or 3.13 installed.

### Step-by-Step Installation Commands

```powershell
# 1. Clone or navigate to the project directory
cd c:\PLAYLISTPILOT

# 2. Create virtual environment
py -m venv .venv
# On macOS/Linux: python3 -m venv .venv

# 3. Activate the virtual environment
.venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 5. Initialize the database
python scripts/init_db.py

# 6. Seed the demonstration playlist (105 items)
python scripts/seed_demo_data.py

# 7. Start the application
python run.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 9. Automated Testing

Run the complete automated test suite with Pytest:

```bash
# Run all tests
pytest

# Run with verbose test names and code coverage report
pytest -v --cov=app tests/
```

**Verified Test Result:** `33 passed in ~7 seconds (100% pass rate)`.

---

## 10. Optional Integrations

### A. YouTube Data API v3 (Metadata Only)
1. Obtain an API Key from Google Cloud Console with YouTube Data API v3 enabled.
2. In PlaylistPilot, navigate to **Settings** &rarr; paste the key in **YouTube Data API Key** &rarr; click **Save Settings**.
3. Alternatively, add `YOUTUBE_API_KEY=AIzaSy...` to your `.env` file.
4. If omitted, Demonstration Mode functions without limitations.

### B. FFmpeg for Local Media Processing
1. Install FFmpeg:
   - Windows: `winget install Gyan.FFmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
2. PlaylistPilot automatically detects FFmpeg in your PATH and enables local audio extraction and video format conversion.

---

## 11. Security & Responsible-Use Notice

- **Compliance:** PlaylistPilot uses the official YouTube Data API v3 exclusively for public metadata. It does not contain stream scrapers, DRM bypasses, or access-control evasion mechanisms.
- **Demonstration Mode:** Simulated operations are explicitly identified as DEMO artifacts in both the database and the interface.
- **Injection Safety:** Path traversal attacks are rejected using strict ancestry verification; subprocesses execute using argument arrays rather than raw shell strings.

---

## 12. College Viva Demonstration Script

Follow these steps during your practical laboratory examination:

1. **Launch App:** Run `python run.py` and open `http://127.0.0.1:5000`.
2. **Review Dashboard:** Explain the strict four-color design, 3D raised cards, and disk capacity gauge.
3. **Explore Curriculum:** Navigate to **Playlists** &rarr; click **Open Explorer** &rarr; demonstrate paginated browsing of the 105-video educational Python course.
4. **Enqueue Batch:** Select 5 lectures &rarr; click **"Add Selected to Queue"**.
5. **Verify Single Worker:** Navigate to **Queue Manager** &rarr; observe that Job #1 is actively downloading while Jobs #2 to #5 wait in FIFO sequence.
6. **Demonstrate Urgent Priority:** Click **"Prioritize Urgent"** on Job #5 &rarr; show how Job #5 jumps to the top of the waiting queue without preempting Job #1.
7. **Simulate Network Failure:** Click **"Simulate Network Drop"** in the top navigation &rarr; show how the active job detects the dropout, halts safely, and transitions to `interrupted`.
8. **Demonstrate Automatic Recovery:** Click **"Restore Simulated Network"** &rarr; show how the worker automatically resumes the interrupted job from its saved checkpoint.
9. **Simulate Crash Recovery:** While a job is running, terminate Flask with `Ctrl+C` in the terminal &rarr; restart with `python run.py` &rarr; refresh the browser to verify the startup recovery service restored all unfinished jobs.
10. **Review History:** Navigate to **Job History** &rarr; filter by status and show the audit log.

---

## 13. Academic Project Details

- **Project:** Master of Computer Applications (MCA) Project
- **Course:** Advanced Python Web Application Development
- **Developer:** MCA Engineering Candidate
- **Documentation:** See `docs/PROJECT_REPORT.md` and `docs/VIVA_QUESTIONS.md`.
- **License:** MIT License
