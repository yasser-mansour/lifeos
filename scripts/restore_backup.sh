#!/usr/bin/env bash
# Usage: scripts/restore_backup.sh [backup_filename]
# With no argument, restores the most recent backup in backups/.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "No virtual environment found. Run scripts/setup_mac.sh first." >&2
  exit 1
fi

"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/backend/manage.py" restore_backup "${1:-}"
