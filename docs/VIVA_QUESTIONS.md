# PlaylistPilot — Academic Viva & Technical Interview Questions

This document contains 30 comprehensive questions and answers covering Python, Flask, Object-Oriented Programming, Relational Databases, Concurrency, Queue Engineering, Fault Recovery, API Integration, and Software Testing.

---

### Category 1: Python & Object-Oriented Programming (OOP)

#### Q1. What is the Global Interpreter Lock (GIL) in CPython, and how does it impact PlaylistPilot?
**Answer:** The GIL is a mutual exclusion lock used by CPython to prevent multiple native threads from executing Python bytecode simultaneously. In PlaylistPilot, our background worker performs primarily I/O-bound tasks (network requests, disk writes, and simulated delays). During I/O operations and system calls, Python releases the GIL, allowing concurrent background queue processing without blocking the Flask web request thread.

#### Q2. How does PlaylistPilot implement the Singleton pattern, and why is it necessary?
**Answer:** `WorkerService.get_instance(app)` implements the Singleton pattern using a class-level lock (`threading.Lock`) and an internal `_instance` variable. This ensures that exactly one worker thread manager exists across the entire Flask application, preventing duplicate background worker threads from being spawned on repeated requests.

#### Q3. What are Python context managers (`with` statement) and where are they used in this project?
**Answer:** Context managers ensure deterministic resource acquisition and cleanup via `__enter__` and `__exit__` dunder methods. PlaylistPilot uses context managers in:
1. `with app.app_context():` to bind Flask application contexts to threads.
2. File I/O (`with open(...) as f:`) to ensure file handles close safely on exceptions.
3. Thread locks (`with self._lock:`) for automatic mutex release.

#### Q4. Explain the difference between inheritance and composition in PlaylistPilot's design.
**Answer:** PlaylistPilot uses **inheritance** when extending frameworks (e.g. `Playlist(db.Model)` inherits SQLAlchemy ORM capabilities), and **composition** for domain logic (e.g. `PlaylistService` contains instances of `MediaItem` and interacts with `StorageService`). Composition is preferred for service design to reduce coupling.

#### Q5. What is the difference between `@classmethod`, `@staticmethod`, and instance methods?
**Answer:** 
- **Instance method:** Receives `self` as the first argument; operates on specific object state.
- **Class method (`@classmethod`):** Receives `cls` as the first argument; used for factory methods like `WorkerService.get_instance(app)`.
- **Static method (`@staticmethod`):** Receives neither `self` nor `cls`; acts as a utility function encapsulated in a class namespace, like `StorageService.format_bytes(bytes)`.

---

### Category 2: Flask Web Architecture

#### Q6. What is the Flask Application Factory pattern and why is it beneficial?
**Answer:** The Application Factory pattern encapsulates application creation inside a function (`create_app(config_name)`), rather than using a global module-level app instance. This allows creating multiple isolated instances with different configurations (e.g. `DevelopmentConfig` vs `TestingConfig`), prevents circular imports, and allows clean testing with Pytest.

#### Q7. What are Flask Blueprints and how are they organized in this application?
**Answer:** Blueprints are modular components that group related views, templates, and static assets. PlaylistPilot defines six Blueprints:
- `dashboard`: Root metrics and summary views.
- `playlists`: Playlist catalog and paginated explorer.
- `queue`: Queue manager and real-time execution controls.
- `history`: Processed job audit logs.
- `settings`: System configuration and API credentials.
- `api`: JSON REST endpoints for AJAX and polling.

#### Q8. How does Flask handle request-response lifecycles, and how is state communicated to the frontend?
**Answer:** Flask handles HTTP requests using WSGI/Werkzeug workers. In PlaylistPilot, requests trigger controller functions in Blueprints that interact with SQLAlchemy and return either rendered Jinja2 HTML templates (for page views) or serialized JSON payloads (via `jsonify`) for asynchronous polling.

#### Q9. How are custom error handlers registered in Flask, and how do they differentiate between web pages and API requests?
**Answer:** Using `@app.errorhandler(code)`. PlaylistPilot's handlers inspect `request.path.startswith("/api/")` or the `Accept: application/json` header: if true, they return a structured JSON response (`{"success": false, "error": "...", "status_code": 404}`); otherwise, they render a styled HTML error template (`errors/404.html`).

---

### Category 3: Relational Databases & SQLAlchemy ORM

#### Q10. What are ACID properties and how does SQLite uphold them in this project?
**Answer:** 
- **Atomicity:** All state transitions and job updates commit completely or roll back entirely.
- **Consistency:** Foreign key constraints (`media_item_id -> media_items.id`) and unique constraints (`idempotency_key`) prevent invalid states.
- **Isolation:** SQLite uses database-level locking to ensure serialized writes.
- **Durability:** Committed transactions are immediately synced to the persistent `.db` file on disk.

#### Q11. Why shouldn't a long-running job hold open a database transaction?
**Answer:** Holding an open transaction during long-running I/O or sleep cycles locks the SQLite database, causing `sqlite3.OperationalError: database is locked` on incoming web requests. PlaylistPilot keeps database transactions short: status is updated, committed immediately, and the transaction is closed before I/O processing occurs.

#### Q12. What causes SQLAlchemy's `DetachedInstanceError` and how is it prevented?
**Answer:** It occurs when an ORM object whose session has been closed or committed is accessed for an attribute that was not pre-loaded. In PlaylistPilot, we prevent this by:
1. Accessing attributes inside active `app_context()` blocks.
2. Using lightweight reference objects (`SamplePlaylistRef`) in Pytest fixtures.
3. Keeping database operations scoped within clearly defined session boundaries.

#### Q13. Why did you choose SQLite over MySQL or PostgreSQL for this MCA project?
**Answer:** SQLite is serverless, zero-configuration, ACID-compliant, and stores data in a single cross-platform file (`instance/playlistpilot.db`). For an MCA college submission and local desktop tool, SQLite eliminates the overhead of managing a background database daemon while providing full relational integrity and sub-millisecond query execution.

---

### Category 4: Concurrency & Threading

#### Q14. What is a daemon thread in Python and why is the background worker set to `daemon=True`?
**Answer:** A daemon thread runs in the background and does not prevent the Python process from exiting when the main application terminates. Setting `daemon=True` ensures that when the user presses `Ctrl+C` to stop Flask, the application exits promptly without hanging on infinite background loops.

#### Q15. How does the worker thread coordinate stopping, pausing, and resuming without busy waiting?
**Answer:** Using `threading.Event` objects (`_stop_event` and `_pause_event`). Instead of busy-waiting in a tight CPU-burning loop, the worker thread checks event flags and uses timed sleep (`time.sleep(poll_interval)`), yielding CPU cycles back to the operating system.

#### Q16. Why must each thread maintain its own database session rather than sharing one?
**Answer:** SQLAlchemy `Session` objects are not thread-safe. Concurrent access to the same session from multiple threads leads to race conditions, corrupted internal identity maps, and broken rollback boundaries. In PlaylistPilot, the worker thread instantiates its own fresh session inside `with self.app.app_context():`.

---

### Category 5: Queue Engineering & State Machines

#### Q17. How does PlaylistPilot achieve sequential processing (`MAX_WORKERS=1`)?
**Answer:** The worker loop queries for the single highest-priority waiting job (`ORDER BY priority DESC, created_at ASC LIMIT 1`). It transitions that job to `downloading`, processes it to completion, and only then queries the database for the next job. This guarantees sequential order and bounded hardware consumption.

#### Q18. How does the "Prioritize Urgent" feature work without disrupting the active job?
**Answer:** When a user prioritizes a waiting job, `QueueService.prioritize_job(job_id)` calculates `max(priority) + 10` among all queued items and assigns it to that job. Because the active running job is already in `downloading` status, its execution is not preempted; the prioritized job simply moves to index 0 of the waiting queue.

#### Q19. What is an idempotency key and how does it prevent duplicate downloads?
**Answer:** An idempotency key is a unique token generated per media item and operation (e.g. `demo_download_15_1730000000`). By storing it with a `UNIQUE` database constraint and checking existing non-terminal jobs before enqueueing, repeated clicks or duplicate imports are safely skipped without creating redundant jobs.

#### Q20. Explain the finite state machine transitions of a `DownloadJob`.
**Answer:** States include: `queued`, `downloading`, `paused`, `completed`, `failed`, `interrupted`, and `cancelled`. Transitions are strictly enforced:
- `queued -> downloading`
- `downloading -> completed | paused | failed | interrupted | cancelled`
- `paused -> queued` (on resume)
- `failed -> queued` (on retry)
- `interrupted -> queued` (on recovery or network restoration)

---

### Category 6: Fault Tolerance, Interruption & Crash Recovery

#### Q21. What happens when the application crashes or power is lost mid-download?
**Answer:** When restarted, `RecoveryService.recover_stale_jobs()` runs automatically during Flask initialization. It queries all jobs left in `downloading` status:
1. If the target output file exists and is valid, the job is marked `completed`.
2. If incomplete, it is marked `interrupted`.
3. If `AUTO_RETRY` is enabled and retries remain, it is requeued automatically. Completed jobs are never repeated.

#### Q22. How is network disconnection simulated and recovered in the demonstration mode?
**Answer:** The user clicks "Simulate Network Drop", which sets `worker.simulated_network_offline = True`. The worker detects this flag at its next checkpoint, records the latest byte progress, and marks the job as `interrupted`. When the user clicks "Restore Simulated Network", the system automatically requeues interrupted jobs and resumes execution from their saved checkpoints.

#### Q23. What is bounded exponential backoff?
**Answer:** Exponential backoff increases the delay before each subsequent retry (e.g. $t = base \times 2^{retry\_count}$). "Bounded" means capping the delay at a maximum upper limit (e.g. 60 seconds) and terminating retries once `retry_count >= max_retries` to avoid infinite loops on permanent errors.

---

### Category 7: External Integrations & Storage Security

#### Q24. How does PlaylistPilot protect against Path Traversal (Directory Traversal) attacks?
**Answer:** In `StorageService.validate_safe_path()`, user-supplied filenames and paths are resolved to their canonical absolute paths (`Path(p).resolve()`). The service verifies that the resolved path is strictly a descendant of the authorized base directory (`resolved_base in resolved_target.parents`). Any attempt to traverse upward via `../` is rejected.

#### Q25. How does PlaylistPilot safely invoke FFmpeg without vulnerability to Command Injection?
**Answer:** The system uses `subprocess.run()` with **argument arrays** (`["ffmpeg", "-i", str(src), "-vn", str(dest)]`) rather than raw shell strings (`shell=True`). This ensures that malicious filenames containing spaces, semicolons, or pipe characters (`|`) cannot execute arbitrary shell commands.

#### Q26. How does the application handle missing YouTube API keys without breaking?
**Answer:** The application factory and services treat the YouTube API key as strictly optional. If the key is missing or invalid, `YouTubeMetadataService` returns an error response with error code `MISSING_API_KEY`. The core application and Demonstration Mode remain 100% operational with the local 105-item curriculum.

#### Q27. Why does PlaylistPilot check disk space before picking a job?
**Answer:** Running out of disk space during large batch processing can corrupt SQLite database files or destabilize the host operating system. `WorkerService` checks `StorageService.get_disk_info()` before every job; if free space is below `MIN_FREE_SPACE_MB` (200MB), the worker automatically pauses the queue and logs a warning.

---

### Category 8: Software Testing & Quality Assurance

#### Q28. What is the role of Pytest fixtures and how does `autouse=True` work?
**Answer:** Fixtures provide baseline data, configurations, or mock clients to tests. In PlaylistPilot's `tests/conftest.py`, `clean_db` is marked `autouse=True`, meaning Pytest automatically invokes it before every test function to clear database tables and ensure test isolation without manual calls.

#### Q29. How do you test background worker threads deterministically in automated tests?
**Answer:** 
1. `TestingConfig` accelerates simulation speed to 20x (`SIMULATION_SPEED = 20.0`) and polling interval to 0.1s.
2. Tests enqueue an item and poll `db.session.get(DownloadJob, job_id)` in a bounded loop (`for _ in range(30): time.sleep(0.15)`).
3. The worker is explicitly stopped with `worker.stop(timeout=1.0)` in fixture teardown to prevent thread leaks.

#### Q30. Why is the user interface designed with a strict four-color palette?
**Answer:** To provide an ultra-clean, accessible, high-contrast aesthetic that communicates status unambiguously through typography, borders, and dimensional 3D cues rather than distracting multi-color schemes. The strict palette—Black (#111111), Red (#E62117), Gray (#808080), and White (#FFFFFF)—maintains a focused and modern desktop dashboard look.
