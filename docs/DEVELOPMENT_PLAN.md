# PlaylistPilot — Software Development Plan & Milestones

## 1. Project Phases & Work Breakdown

```
Phase 1: Architecture & Data Modeling (Completed)
  |-- Requirements analysis and finite state machine formalization
  |-- SQLite schema design (Playlists, MediaItems, DownloadJobs)
  |-- Strict 4-color palette tokens and 3D elevation variables

Phase 2: Foundation & Factory Setup (Completed)
  |-- Flask application factory (`create_app`)
  |-- SQLAlchemy 2.0 configuration and thread-safe session patterns
  |-- Seeding scripts and 105-item educational dataset generation

Phase 3: Frontend Implementation (Completed)
  |-- Responsive layout with 3D tactile buttons and raised cards
  |-- Dashboard, Playlist Catalog, Explorer, Queue Manager, History, Settings, About
  |-- Error handling templates (404, 500, 503)

Phase 4: Queue Engine & Concurrency (Completed)
  |-- Dedicated singleton worker thread (`MAX_WORKERS=1`)
  |-- Priority elevation without active job preemption
  |-- Checkpoint-aware pause, resume, and cancellation mechanics

Phase 5: Fault Tolerance & Recovery (Completed)
  |-- Startup crash recovery (`RecoveryService.recover_stale_jobs`)
  |-- Network drop simulation and automatic recovery
  |-- Bounded exponential backoff and error tracking

Phase 6: Integrations & Media Safeguards (Completed)
  |-- Official YouTube Data API v3 metadata retrieval
  |-- Safe FFmpeg argument array invocation for local audio/video conversion
  |-- Free disk space verification and path traversal defenses

Phase 7: Automated Testing & Verification (Completed)
  |-- 33 Pytest unit, integration, and view tests
  |-- Verification of zero race conditions and thread termination

Phase 8: Documentation & Viva Delivery (Completed)
  |-- Architecture, Database Schema, Project Report, Testing, Troubleshooting, Viva Q&A
```

---

## 2. Milestone Acceptance Criteria Matrix

| Milestone | Target Deliverable | Acceptance Criteria | Status |
|---|---|---|---|
| **M1: Core Engine** | Flask + SQLite | App starts cleanly, database tables created, models validate state transitions | Verified |
| **M2: Demo Dataset** | 100+ item sample | 105 realistic Python Systems Architecture items seeded without credentials | Verified |
| **M3: UI & Palette** | HTML5 + CSS3 | Strict Black/Red/Gray/White palette, 3D tactile buttons, responsive layout | Verified |
| **M4: Queue Control** | Queue Manager | Start, pause, resume, cancel, prioritize; exactly 1 active job at a time | Verified |
| **M5: Recovery** | RecoveryService | Stale jobs detected on reboot, completed files preserved, interrupted requeued | Verified |
| **M6: Testing** | Pytest Suite | 100% pass rate across models, services, routes, and views (33 tests) | Verified |
| **M7: Viva Readiness**| Academic Docs | Complete project report, architecture blueprint, and 30 viva interview answers | Verified |
