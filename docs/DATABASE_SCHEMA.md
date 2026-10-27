# PlaylistPilot — Database Schema & Data Models

## 1. Relational ER Diagram

```
+-----------------------------------+
|            playlists              |
+-----------------------------------+
| PK  id               INTEGER      |
|     title            VARCHAR(255) |
|     source_type      VARCHAR(50)  |
|     source_url       VARCHAR(500) |
| IX  source_id        VARCHAR(100) |
|     description      TEXT         |
|     thumbnail_url    VARCHAR(500) |
|     item_count       INTEGER      |
|     import_status    VARCHAR(50)  |
|     metadata_json    TEXT         |
|     created_at       DATETIME     |
|     updated_at       DATETIME     |
+-----------------+-----------------+
                  | 1
                  |
                  | 0..*
+-----------------v-----------------+
|           media_items             |
+-----------------------------------+
| PK  id                  INTEGER   |
| FK  playlist_id         INTEGER   | (nullable, ondelete=CASCADE/SET NULL)
| IX  source_id           VARCHAR   |
|     title               VARCHAR   |
|     duration_seconds    INTEGER   |
|     media_type          VARCHAR   |
|     thumbnail_url       VARCHAR   |
|     position            INTEGER   |
|     availability_status VARCHAR   |
|     metadata_json       TEXT      |
|     created_at          DATETIME  |
+-----------------+-----------------+
                  | 1
                  |
                  | 0..*
+-----------------v-----------------+
|          download_jobs            |
+-----------------------------------+
| PK  id                INTEGER     |
| FK  media_item_id     INTEGER     | (not null, ondelete=CASCADE)
|     job_type          VARCHAR(50) |
| IX  status            VARCHAR(50) |
| IX  priority          INTEGER     |
|     progress_percent  FLOAT       |
|     bytes_processed   BIGINT      |
|     total_bytes       BIGINT      |
|     output_path       VARCHAR     |
|     error_message     TEXT        |
|     retry_count       INTEGER     |
|     max_retries       INTEGER     |
|     cancel_requested  BOOLEAN     |
|     pause_requested   BOOLEAN     |
| UQ  idempotency_key   VARCHAR     |
|     created_at        DATETIME    |
|     started_at        DATETIME    |
|     updated_at        DATETIME    |
|     completed_at      DATETIME    |
+-----------------------------------+
```

---

## 2. Table Specifications

### 2.1 `playlists`
Stores top-level collection metadata for imported playlists.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | No | PK (Autoincrement) | Unique identifier |
| `title` | VARCHAR(255) | No | — | Display title of the playlist |
| `source_type` | VARCHAR(50) | No | `'demo'` | Origin type: `demo`, `youtube`, `local` |
| `source_url` | VARCHAR(500) | Yes | NULL | Canonical URL |
| `source_id` | VARCHAR(100) | Yes | NULL | External ID (e.g. `PL...` or demo seed ID) |
| `description` | TEXT | Yes | NULL | Extended syllabus or notes |
| `thumbnail_url`| VARCHAR(500) | Yes | NULL | Image path or URL |
| `item_count` | INTEGER | No | 0 | Cached count of associated media items |
| `import_status`| VARCHAR(50) | No | `'completed'` | Status: `pending`, `completed`, `failed` |
| `metadata_json`| TEXT | Yes | NULL | JSON string of arbitrary metadata |
| `created_at` | DATETIME (UTC)| No | `CURRENT_TIMESTAMP` | Creation time |
| `updated_at` | DATETIME (UTC)| No | `CURRENT_TIMESTAMP` | Last updated timestamp |

### 2.2 `media_items`
Stores individual lecture or media records belonging to a playlist.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | No | PK (Autoincrement) | Unique item identifier |
| `playlist_id` | INTEGER | Yes | NULL | Foreign Key referencing `playlists.id` |
| `source_id` | VARCHAR(100) | No | — | Video or file identifier (Indexed) |
| `title` | VARCHAR(255) | No | — | Video title |
| `duration_seconds` | INTEGER | Yes | NULL | Length in seconds |
| `media_type` | VARCHAR(50) | No | `'video'` | `video`, `audio`, `local_file` |
| `thumbnail_url`| VARCHAR(500) | Yes | NULL | Thumbnail image path |
| `position` | INTEGER | No | 0 | 1-based order in playlist |
| `availability_status` | VARCHAR(50) | No | `'available'` | `available`, `unavailable`, `private` |
| `metadata_json`| TEXT | Yes | NULL | Category, tags, estimated size |
| `created_at` | DATETIME (UTC)| No | `CURRENT_TIMESTAMP` | Record creation timestamp |

### 2.3 `download_jobs`
Audit log and active queue entity for batch processing.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | No | PK (Autoincrement) | Unique job identifier |
| `media_item_id` | INTEGER | No | — | Foreign Key referencing `media_items.id` |
| `job_type` | VARCHAR(50) | No | `'demo_download'` | `demo_download`, `media_convert` |
| `status` | VARCHAR(50) | No | `'queued'` | Current state (Indexed) |
| `priority` | INTEGER | No | 0 | Higher values processed first (Indexed)|
| `progress_percent`| FLOAT | No | 0.0 | 0.0 to 100.0 completion percentage |
| `bytes_processed` | BIGINT | No | 0 | Byte transfer progress |
| `total_bytes` | BIGINT | No | 0 | Expected total file size |
| `output_path` | VARCHAR(500) | Yes | NULL | Final stored file artifact path |
| `error_message` | TEXT | Yes | NULL | Failure diagnostics or traceback |
| `retry_count` | INTEGER | No | 0 | Number of retry attempts executed |
| `max_retries` | INTEGER | No | 3 | Maximum allowable retries |
| `cancel_requested` | BOOLEAN | No | FALSE | Cancellation signal flag |
| `pause_requested` | BOOLEAN | No | FALSE | Pause checkpoint signal flag |
| `idempotency_key` | VARCHAR(100) | Yes | NULL | Unique key preventing duplicate queues |
| `created_at` | DATETIME (UTC)| No | `CURRENT_TIMESTAMP` | Enqueue timestamp |
| `started_at` | DATETIME (UTC)| Yes | NULL | Time worker started processing |
| `updated_at` | DATETIME (UTC)| No | `CURRENT_TIMESTAMP` | Last state update timestamp |
| `completed_at` | DATETIME (UTC)| Yes | NULL | Time job entered terminal state |

---

## 3. Database Indexes

To maintain responsive querying even with thousands of queued records, the schema defines the following explicit indexes:
- `ix_playlists_source_id`: Fast lookup of existing playlists to avoid duplicate imports.
- `ix_media_items_playlist_id`: Fast retrieval of all media items for a playlist.
- `ix_media_items_source_id`: Fast item resolution during queue operations.
- `ix_download_jobs_status`: Accelerates polling of active worker state and queued items (`WHERE status = 'queued'`).
- `ix_download_jobs_priority`: Accelerates priority sorting (`ORDER BY priority DESC, created_at ASC`).
- `uq_download_jobs_idempotency_key`: Unique constraint ensuring zero duplicate jobs.
