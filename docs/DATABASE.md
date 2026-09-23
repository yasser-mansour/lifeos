# Database

## Engine

SQLite, deliberately. LIFEOS is a single-user local application — there is no concurrent-writer load that would justify Postgres, and SQLite means zero setup (no server process, no credentials, trivial backup — see `docs/SECURITY.md` and section below).

The database file lives at `backend/lifeos.sqlite3` for a from-source dev checkout (gitignored, never committed). A **packaged distributable install** (macOS `.dmg` or Windows installer — see `packaging/`) instead stores it under the OS's own per-user application-data directory (`~/Library/Application Support/LIFEOS/database/lifeos.sqlite3` on macOS, `%LOCALAPPDATA%\LIFEOS\database\lifeos.sqlite3` on Windows), controlled by the `LIFEOS_APP_DATA_DIR` environment variable the desktop wrapper sets before starting the backend — see `docs/SECURITY.md`'s "App-data location" section. Either way, `LIFEOS_DB_PATH` can override the exact file path directly if needed.

## Conventions

Every domain model extends `apps.core.models.BaseModel`:

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(...)
    updated_at = models.DateTimeField(...)
    version = models.PositiveIntegerField(default=1, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ActiveManager()      # excludes soft-deleted rows
    all_objects = models.Manager() # includes everything
```

- **UUID primary keys**, not auto-increment integers — required for Android to generate IDs offline (a locally-created task needs an ID before it's ever synced) and to make a future move to Postgres a non-event for every foreign key in the schema.
- **`version`** increments on every `save()` after the first. Used for optimistic-concurrency checks during sync (see `docs/SYNC.md`) — never for anything user-facing.
- **Soft delete**: `deleted_at` instead of a real `DELETE`. Financial transactions, journal entries, and study history must never actually disappear (spec: "Never silently destroy financial or journal history"). `Model.objects` (the default manager) filters `deleted_at__isnull=True` automatically, so soft-deleted rows are invisible everywhere without every query needing to remember to filter them out. `all_objects` is there for the rare admin/recovery case.
- A few lightweight models intentionally do **not** extend `BaseModel` — `core.ActivityEvent` (an append-only log; soft-delete and versioning don't mean anything for a log line) and `finance.Category` (a small shared lookup table).

## Money

Every monetary field is a `DecimalField(max_digits=14, decimal_places=2)`, paired with an explicit `currency` field (default from `Profile.default_currency`, itself defaulting to `MAD`). Floats are never used for money anywhere in the codebase — see `apps/core/money.py`. `Transaction.amount` is always stored positive; the sign is derived from `type` (see `docs/FINANCE.md`) rather than baked into the stored number, so a transaction's "what actually happened" (an expense of 100) is separated from "how it affects a balance" (-100), which matters once allocations and refunds enter the picture.

## Balances are derived, not stored

`Account` has no `balance` column. `Account.balance` is a Python property that computes `opening_balance + Σ(signed transaction amounts) + Σ(transfers in) - Σ(transfers out)` at read time (`apps/finance/services.py::account_balance`). This is the spec's explicit requirement ("Do not store current balance as unrecoverable source of truth... Optimize with cached calculations only if correctness remains reconstructible"). At single-user scale this is fast enough that no caching has been added; if it ever needs to be, the cached value would be reconstructible by replaying the same function, so nothing about correctness would change.

## Backups

`apps/core/backup.py` uses SQLite's own online backup API (`sqlite3.Connection.backup()`) rather than copying the file — safe to run while the server is live, since it doesn't require an exclusive lock the way `cp` on an actively-written file would risk. Backups land in `backups/lifeos_<timestamp>.sqlite3` (microsecond-resolution timestamps, with a collision-safe suffix fallback — two backups landing in the same wall-clock second must never overwrite each other, since `restore_backup()` always takes a fresh safety backup of the *current* state before overwriting, and that safety backup must not collide with the very backup file being restored from). See `docs/SECURITY.md` for what is and isn't included in a backup.
