# MCA Project Report: PlaylistPilot — Smart Playlist & Batch Job Manager

**Course:** Master of Computer Applications (MCA)  
**Academic Project:** Python Web Application Development  
**System Name:** PlaylistPilot  
**Version:** 1.0.0 (Production-Ready Educational Build)  

---

## 1. Abstract
In modern online education and digital research, learners frequently consume educational video series organized in large playlists spanning 100, 200, or more lectures. Standard browsers and video platforms lack granular batch job controls, persistent queue orchestration, selective downloading, priority reassignment, and deterministic recovery after connectivity drops or system crashes. 

**PlaylistPilot** addresses these critical gaps by providing a local-first Python web application powered by Flask, SQLAlchemy, and SQLite. It features a dedicated thread-safe queue engine, finite-state-machine job management, startup crash recovery, strict four-color UI design, and an educational demonstration mode with 105 pre-generated curricular items. The application operates 100% offline without mandatory API credentials, ensuring seamless evaluation in academic viva and laboratory environments.

---

## 2. Introduction & Problem Definition

### 2.1 Background
Managing large video playlists poses substantial usability and technical challenges. When handling playlists with over 100 items, users often require:
1. Selective batch queueing rather than indiscriminate downloads.
2. The ability to prioritize urgent topics ahead of existing queued items.
3. Resilience against sudden internet disconnections and power outages.
4. Prevention of duplicate processing to conserve storage and bandwidth.
5. Storage capacity verification before initiating heavy I/O operations.

### 2.2 Shortcomings of Existing Solutions
- **Browser-based downloaders:** Crash on large batches, consume unbounded RAM, and lose all queue state upon browser closure.
- **Enterprise job queues (Celery, Redis):** Impose heavy infrastructure prerequisites, requiring Linux daemons, external message brokers, and complex network configurations unsuitable for desktop or local academic presentation.
- **Command-line scripts:** Lack intuitive visual feedback, selective item filtering, and live progress monitoring for non-technical users.

---

## 3. Objectives of Proposed System
1. **Local-First Architecture:** Deliver an application that operates entirely on standard student hardware using Python and SQLite without external daemons.
2. **Persistent Queue Engine:** Maintain a persistent database-backed queue supporting FIFO scheduling, priority boosting, pause/resume, and safe cancellation.
3. **Fault Tolerance & Recovery:** Automatically detect aborted jobs upon system restart and recover them without manual intervention or data loss.
4. **Demonstration Mode:** Provide an out-of-the-box educational playlist (105 items) with simulated network interruption and error injection tools for viva demonstration.
5. **Strict 4-Color Visual Design:** Adhere to a minimalist visual palette (Black, Red, Gray, White) with tactile 3D-inspired controls.
6. **Legitimate Integration Safeguards:** Adhere to YouTube Data API v3 terms for public metadata and FFmpeg for authorized local media files.

---

## 4. System Requirements

### 4.1 Software Requirements
- **Operating System:** Windows 10/11, macOS, or Linux.
- **Runtime Environment:** Python 3.11, 3.12, or 3.13.
- **Web Framework:** Flask 3.1+.
- **Database / ORM:** SQLite 3, SQLAlchemy 2.0+, Flask-SQLAlchemy 3.1+.
- **Optional Tools:** FFmpeg (for media conversion), YouTube Data API v3 key.
- **Testing Framework:** Pytest 8.0+, Pytest-Cov.

### 4.2 Minimum Hardware Requirements
- **Processor:** 1.6 GHz Dual-Core x86_64 or ARM64.
- **Memory (RAM):** 2 GB minimum (4 GB recommended).
- **Disk Space:** 250 MB free disk space for runtime and database.

---

## 5. Implementation Methodology

### 5.1 Application Factory & Modular Routing
The application is structured using the Flask Application Factory pattern (`create_app()`), segregating responsibilities into distinct Blueprints:
- `dashboard`: Real-time system metrics, recent activity, and import forms.
- `playlists`: Catalog management and paginated lecture explorer.
- `queue`: Core queue manager and live execution controls.
- `history`: Permanent audit log with status filtering and retry actions.
- `settings`: Configuration of retry policies, disk thresholds, and API keys.
- `api`: RESTful JSON endpoints for asynchronous client interactions.

### 5.2 Thread-Safe Worker & Queue Mechanics
To avoid unbounded thread spawning and race conditions:
- A single daemon background thread (`WorkerService`) handles job processing.
- The thread coordinates via standard library `threading.Lock` and `threading.Event`.
- Database sessions are strictly isolated: each iteration executes inside a fresh Flask application context, preventing detached session leaks across threads.

### 5.3 Crash Recovery Protocol
The `RecoveryService` runs during application boot before accepting HTTP traffic:
1. Queries all jobs with `status = 'downloading'`.
2. Inspects the file system for existing output artifacts.
3. Marks completed transfers as `completed` and incomplete transfers as `interrupted` (or requeues them if `AUTO_RETRY` is active).

---

## 6. Testing & Quality Assurance

### 6.1 Automated Pytest Suite
The project includes a comprehensive suite of 33 automated tests across 9 test modules:
1. `test_models.py`: Model creation, duration formatting, and state transition validation.
2. `test_playlists.py`: 105-item seeding, pagination, search filters, and safe deletion.
3. `test_queue.py`: Duplicate enqueue prevention, FIFO scheduling, priority boosting, and cancellation.
4. `test_worker.py`: Single worker invariant, simulated job execution, and error handling.
5. `test_recovery.py`: Startup recovery of interrupted jobs and output file preservation.
6. `test_storage.py`: Disk free-space calculation and directory traversal protection.
7. `test_media_service.py`: File format validation and FFmpeg detection.
8. `test_api.py`: REST JSON endpoints and error responses.
9. `test_views.py`: Full HTML template rendering and flash message validation.

**Result:** 100% test pass rate (33 passed in ~7 seconds).

---

## 7. Results & Key Achievements
- Delivered an end-to-end, working Python web application.
- Verified priority management: urgent items move to the top of the waiting queue without disrupting the active job.
- Successfully demonstrated deterministic network dropouts and seamless recovery.
- Successfully verified zero-credential demonstration with 105 curricular records.
- Maintained a strict 4-color palette with 3D tactile interface elements.

---

## 8. Limitations & Future Scope

### 8.1 Limitations
- By design, the local MVP uses a single-worker model to avoid overwhelming client hardware.
- Official YouTube Data API integration provides metadata only; actual media downloading from YouTube is not supported due to platform terms of service.
- Multi-user authentication is intentionally omitted to keep the project lightweight and local-first.

### 8.2 Future Scope
- Optional multi-worker support with user-configurable concurrency limits (2–4 workers).
- WebSocket streaming via Flask-SocketIO as an alternative to polling.
- Exporting playlist audit reports to CSV and PDF formats.
