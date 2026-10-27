# PlaylistPilot — System Architecture & Engineering Design

## 1. System Overview

**PlaylistPilot** is a local-first Python web application engineered for deterministic, persistent playlist queue execution, crash recovery, and batch media management. It is designed specifically for students and engineers needing structured control over large educational playlist workloads (100–360+ videos) without relying on heavyweight cloud queues like Celery, Redis, or RabbitMQ.

```
                      +-----------------------------------+
                      |      Web Browser Interface        |
                      |  HTML5 + Vanilla CSS3 (3D depth)  |
                      |    Fetch API + Polling Engine     |
                      +-----------------+-----------------+
                                        | HTTP / JSON
                                        v
+-------------------------------------------------------------------------+
|                        Flask Application Factory                        |
|                                                                         |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | Dashboard / Views |  |  Queue Endpoints  |  | Playlists & Storage |  |
|  +-------------------+  +-------------------+  +---------------------+  |
+-----------------------------------+-------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+------------------------+                     +-------------------------+
|   SQLAlchemy 2.0 ORM   |                     | Dedicated Worker Thread |
|                        |                     |                         |
| - Playlists            |                     | - Sequential Execution  |
| - MediaItems           |                     | - Checkpoint Throttling |
| - DownloadJobs (Audit) |                     | - Priority Sorting      |
+-----------+------------+                     +------------+------------+
            |                                               |
            v                                               v
+------------------------+                     +-------------------------+
|   SQLite Persistent    |                     |  Crash Recovery Engine  |
|   Database File        |                     |  & Demonstration Layer  |
+------------------------+                     +-------------------------+
```

---

## 2. Component Responsibilities

### 2.1 Flask Application Factory (`app/__init__.py`)
- Configures environment and database bindings.
- Registers Blueprints (`dashboard`, `playlists`, `queue`, `history`, `settings`, `api`).
- Configures error handling for HTTP 404, 500, and 503.
- Runs database table synchronization (`db.create_all()`).
- Triggers the `RecoveryService` on startup to inspect and reconcile orphaned jobs.
- Auto-seeds the demonstration dataset if the database is newly initialized.
- Spawns the dedicated singleton worker thread (`WorkerService`).

### 2.2 SQLAlchemy Models & Data Layer (`app/models/`)
- **`Playlist`**: Holds playlist metadata, source URLs, source identifiers, item counts, and timestamps.
- **`MediaItem`**: Represents individual videos or audio lectures with position indexing, duration formatting, availability states, and extensible JSON metadata.
- **`DownloadJob`**: Tracks execution state, priority levels, byte accounting, progress percentages, error messages, retry counters, and idempotency keys. Validates finite state machine transitions.

### 2.3 Service Layer (`app/services/`)
- **`PlaylistService`**: Handles playlist imports, paginated retrieval, module categorization, and safe metadata deletion that preserves job audit history.
- **`QueueService`**: Enqueues media items with duplicate prevention, handles queue pause/resume, and elevates urgent waiting jobs via priority increments.
- **`WorkerService`**: Runs a dedicated thread loop to execute jobs one-at-a-time (`MAX_WORKERS=1`). Prevents duplicate worker threads and coordinate thread-safe pause, cancel, and simulation flags.
- **`RecoveryService`**: Detects uncompleted jobs left in `downloading` status from sudden application shutdown or power loss, verifies output files, and requeues retryable jobs.
- **`StorageService`**: Monitors free disk space, validates safe directory paths against directory traversal attacks, and formats byte counts.
- **`YouTubeMetadataService`**: Connects to the official YouTube Data API v3 for public metadata, with graceful offline degradation.
- **`MediaService`**: Provides safe local media inspection and audio extraction/format conversion using FFmpeg argument arrays (preventing shell injection).

---

## 3. Worker Concurrency & Thread Safety

### 3.1 Single-Worker Invariant
To ensure bounded resource usage on standard student hardware, PlaylistPilot enforces a single-active-worker policy:
- Exactly **one job is executed at a time**.
- Thread coordination uses standard library primitives: `threading.Lock`, `threading.Event`, and a dedicated daemon thread.
- Duplicate thread creation is blocked via atomic lock checks in `WorkerService.start()`.

### 3.2 Database Session Isolation
SQLAlchemy sessions are bound to thread locals. PlaylistPilot adheres strictly to session lifecycles:
- The background thread never shares open sessions with HTTP request threads.
- In every worker iteration, a fresh `with app.app_context():` block is instantiated.
- Database transactions are kept minimal: states are committed immediately and sessions are closed before executing sleep intervals or I/O waits.

---

## 4. State Machine & Finite Transition Model

The `DownloadJob` finite state machine is mathematically bounded:

```
           +--------------------------------------------+
           |                                            |
           v                                            |
      [ queued ] ------> [ downloading ] ------> [ completed ] (terminal)
           |                     |
           | (cancel)            +------> [ paused ] ------> [ queued ] (resume)
           v                     |
      [ cancelled ]              +------> [ interrupted ] ------> [ queued ] (recover/retry)
                                 |
                                 +------> [ failed ] ------> [ queued ] (retry)
                                 |
                                 +------> [ cancelled ] (safe cancel)
```

Transitions are strictly validated in Python via `can_transition_to(target_status)`. Direct transitions from invalid states (such as `downloading -> queued` without passing through paused/interrupted) are rejected.

---

## 5. Fault Tolerance & Crash Recovery Strategy

### 5.1 Power Cut / Abrupt Termination
1. Upon application restart, `RecoveryService.recover_stale_jobs()` executes inside the application startup hook.
2. It queries for any jobs marked `downloading`.
3. If an output artifact already exists on disk and is intact, the job status is preserved as `completed`.
4. If the transfer was incomplete, the job is marked `interrupted`.
5. If `AUTO_RETRY` is enabled and `retry_count < max_retries`, the job is incremented and returned to `queued` to be picked up automatically.

### 5.2 Network Drops & Jitter
- When network failure is detected (or simulated via the UI test button), the active worker immediately halts, saves the current progress percentage, and marks the job as `interrupted`.
- Once connectivity is restored, the queue engine automatically resumes waiting and interrupted work without creating duplicate jobs.
