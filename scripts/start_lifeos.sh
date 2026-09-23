#!/usr/bin/env bash
# Starts the LIFEOS backend in the foreground (Ctrl+C to stop). This is the
# "run it from a terminal" path for development — normal usage is opening
# LIFEOS.app, which manages the same process for you.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "No virtual environment found. Run scripts/setup_mac.sh first." >&2
  exit 1
fi

if curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:${LIFEOS_PORT:-8420}/api/health/" 2>/dev/null | grep -q "200"; then
  echo "LIFEOS is already running on port ${LIFEOS_PORT:-8420}."
  exit 0
fi

exec "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/backend/run_server.py"
