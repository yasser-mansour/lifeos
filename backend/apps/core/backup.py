"""Local backup/restore. Every backup is a straight SQLite copy using
SQLite's own online backup API (safe to run while the server is up — it
doesn't require an exclusive lock), written under <repo>/backups/. Nothing
is ever uploaded anywhere (spec §93: "Do NOT upload automatically
anywhere")."""

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings


@dataclass
class BackupInfo:
    path: Path
    created_at: datetime
    size_bytes: int

    @property
    def filename(self):
        return self.path.name

    @property
    def size_mb(self):
        return round(self.size_bytes / (1024 * 1024), 2)


def _db_path() -> Path:
    return Path(settings.DATABASES["default"]["NAME"])


def create_backup() -> BackupInfo:
    settings.LIFEOS_BACKUP_DIR.mkdir(exist_ok=True)
    # Microsecond resolution, plus an explicit collision fallback: two
    # backups (e.g. a restore's safety copy immediately following a manual
    # one) landing in the same second must never overwrite each other —
    # restore_backup() depends on the source file it reads from surviving
    # untouched (see its docstring).
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest_path = settings.LIFEOS_BACKUP_DIR / f"lifeos_{timestamp}.sqlite3"
    suffix = 1
    while dest_path.exists():
        dest_path = settings.LIFEOS_BACKUP_DIR / f"lifeos_{timestamp}_{suffix}.sqlite3"
        suffix += 1

    source_conn = sqlite3.connect(str(_db_path()))
    dest_conn = sqlite3.connect(str(dest_path))
    with dest_conn:
        source_conn.backup(dest_conn)
    source_conn.close()
    dest_conn.close()

    stat = dest_path.stat()
    return BackupInfo(path=dest_path, created_at=datetime.fromtimestamp(stat.st_mtime), size_bytes=stat.st_size)


def list_backups() -> list[BackupInfo]:
    settings.LIFEOS_BACKUP_DIR.mkdir(exist_ok=True)
    backups = []
    for path in sorted(settings.LIFEOS_BACKUP_DIR.glob("lifeos_*.sqlite3"), reverse=True):
        stat = path.stat()
        backups.append(BackupInfo(path=path, created_at=datetime.fromtimestamp(stat.st_mtime), size_bytes=stat.st_size))
    return backups


def latest_backup() -> BackupInfo | None:
    backups = list_backups()
    return backups[0] if backups else None


class RestoreError(Exception):
    pass


def restore_backup(backup_filename: str) -> BackupInfo:
    """Restores a named backup over the live database. Always makes a
    safety copy of the *current* state first (spec §94: "Before restore:
    create safety backup of current state") so a bad restore is itself
    recoverable."""
    # Resolve before comparing — Path("a/b/../..").parent == Path("a") would
    # otherwise let ".." segments walk straight out of the backups directory.
    backup_dir_resolved = settings.LIFEOS_BACKUP_DIR.resolve()
    backup_path = (settings.LIFEOS_BACKUP_DIR / backup_filename).resolve()
    if backup_path.parent != backup_dir_resolved or not backup_path.exists():
        raise RestoreError("Backup file not found.")

    safety = create_backup()

    try:
        source_conn = sqlite3.connect(str(backup_path))
        dest_conn = sqlite3.connect(str(_db_path()))
        with dest_conn:
            source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()
    except Exception as exc:
        # The live database may now be partially overwritten — the backup
        # API doesn't guarantee all-or-nothing on a mid-copy failure. The
        # safety snapshot taken above is the recovery path.
        raise RestoreError(
            f"Restore failed partway through. Restore from the safety backup to recover: {safety.filename}. Original error: {exc}"
        ) from exc

    return safety
