# LIFEOS Architecture

## Overview

LIFEOS is a local-first personal operating system with three components:

- **backend/** — Django + Django REST Framework + SQLite. This is the source of truth. Serves both the desktop web UI (server-rendered templates) and a REST API (consumed by Android, and by a handful of AJAX interactions in the desktop UI).
- **android/** — a native Kotlin/Jetpack Compose app with its own Room database. Works fully offline; syncs with the backend over the LAN when reachable.
- **desktop/** — a small native Swift/AppKit wrapper (`LIFEOS.app`) that starts the backend, waits for it to become healthy, and shows it in a native window via `WKWebView`. It contains no application logic of its own.

There is no cloud component. The Mac is the server; SQLite is the database; the LAN is the only network the system depends on.

## Why this split

The backend owns all business logic (finance math, the study timer's event-replay engine, sync reconciliation rules) so that the desktop UI and the API serve the *same* logic — desktop templates call into `apps/<domain>/services.py` functions directly; the API calls the same functions through DRF viewsets. Android can't share Python code, so `apps/study/engine.py`'s duration-replay algorithm is deliberately small (~30 lines) and mirrored by hand in `android/.../study/StudyTimerEngine.kt`, with matching unit test suites on both sides (`apps/study/tests.py::TimerEngineTests` and `StudyTimerEngineTest.kt`) so the two staying in sync is verifiable, not just asserted.

## Backend app layout

Each domain lives in its own Django app under `backend/apps/`:

| App | Owns |
|---|---|
| `core` | Base model (UUID/versioning/soft-delete), Profile, first-run, settings, health endpoint, backup/export, activity log, design-system template tags |
| `devices` | Device registration, pairing tokens, device credentials, the `DeviceTokenAuthentication` DRF class |
| `people` | Person (clients, contacts, friends, family — one flexible model) |
| `school` | Course, Topic, Exam |
| `projects` | Project (business/school/personal) |
| `tasks` | Task, including Waiting-For fields |
| `finance` | Account, Transaction, Transfer, Allocation, RecurringCommitment, Budget, Category, Card |
| `study` | StudySession, StudySessionEvent, StudyGoal, the timer engine and statistics service |
| `calendar_app` | Event, and the Home dashboard's "Today" aggregation |
| `journal`, `writing`, `goals`, `notes` | Personal-area content |
| `inbox` | Universal capture, with convert-to-task/note actions |
| `dashboard` | The Home screen — reads from every other app, owns none of the data |
| `sync` | Present as an app for symmetry with the domain list; the actual sync endpoints live on each domain's DRF viewset plus `apps/devices/api.py::claim_device` — there's no separate sync-specific model beyond what's documented in `docs/SYNC.md` |
| `security` | `apps/security/crypto.py` — the Keychain-backed field-encryption helper (see `docs/SECURITY.md`; not currently used by any field, since Cards deliberately avoids needing it) |
| `search` | Cross-app search, backing both the command palette and (if extended) a dedicated search page |

Every domain model inherits `apps.core.models.BaseModel`: a UUID primary key, `created_at`/`updated_at`, an auto-incrementing `version` (for sync conflict detection), and soft delete (`deleted_at`, with `objects` excluding deleted rows and `all_objects` including them).

## Request paths

- **Desktop UI**: browser → Django view (in `apps/<domain>/views.py`) → `apps/<domain>/services.py` → ORM → template. Session-authenticated, CSRF-protected.
- **Android / external API**: HTTP client → DRF viewset (`apps/<domain>/api.py`) → same services where they exist (Finance, Study) or directly to the ORM for simpler CRUD apps → JSON. `DeviceTokenAuthentication` (`Authorization: Device <token>`) or Django session auth.
- **Command palette / quick-add**: same Django views, via `fetch()` from `static/js/app.js`.

## Running it

- `scripts/setup_mac.sh` — one-time: venv, dependencies, migrations.
- `scripts/start_lifeos.sh` / `scripts/stop_lifeos.sh` — foreground run / stop, for development.
- `scripts/build_mac_app.sh` — compiles `desktop/LIFEOS.app`.
- `scripts/build_android.sh` — builds the Android debug APK.
- `backend/run_server.py` — what `LIFEOS.app` and the shell scripts actually launch: Django running under `waitress` (not `manage.py runserver`), with `WhiteNoise` serving static files (see `docs/SECURITY.md` and the note in `backend/lifeos/settings.py` — `runserver`'s automatic static-file serving does not apply once you're not using `runserver`).

See `docs/DATABASE.md`, `docs/FINANCE.md`, `docs/STUDY_ENGINE.md`, `docs/SYNC.md`, `docs/DEVICES.md`, `docs/SECURITY.md`, and `docs/UI_DESIGN.md` for the areas that have their own design decisions worth documenting in detail.
