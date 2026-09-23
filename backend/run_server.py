#!/usr/bin/env python3
"""Runs the LIFEOS backend with waitress instead of Django's dev server —
this is what actually gets launched by LIFEOS.app and by scripts/start_lifeos.sh.
`manage.py runserver` remains available for day-to-day development."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lifeos.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from waitress import serve  # noqa: E402

from lifeos.wsgi import application  # noqa: E402


def _has_pending_migrations() -> bool:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    return bool(executor.migration_plan(targets))


def _backup_before_migrating():
    """Part of update safety: an app update that ships new migrations must
    never run them against an existing database without a fresh safety copy
    first (spec "Pre-migration backups"). Skipped on an ordinary launch with
    nothing pending, and on a brand first launch with no database file yet —
    neither case has anything worth backing up."""
    db_path = Path(settings.DATABASES["default"]["NAME"])
    if not db_path.exists():
        return
    if not _has_pending_migrations():
        return
    from apps.core.backup import create_backup

    backup = create_backup()
    print(f"Pending migrations detected — safety backup created: {backup.path}", flush=True)


def main():
    port = int(os.environ.get("LIFEOS_PORT", "8420"))
    host = os.environ.get("LIFEOS_HOST", "127.0.0.1")

    _backup_before_migrating()
    call_command("migrate", verbosity=0, interactive=False)

    print(f"LIFEOS backend serving on http://{host}:{port}", flush=True)
    serve(application, host=host, port=port, threads=8)


if __name__ == "__main__":
    main()
