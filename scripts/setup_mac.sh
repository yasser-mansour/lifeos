#!/usr/bin/env bash
# One-time setup: creates the Python virtual environment, installs
# dependencies, and runs migrations. Safe to re-run — never touches
# existing data.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$ROOT_DIR/.venv"

echo "==> Checking for Python 3.10+"
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version=$("$candidate" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON_BIN=$(command -v "$candidate")
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "No Python 3.10+ found. Install it with: brew install python@3.12" >&2
  exit 1
fi
echo "    Using $PYTHON_BIN"

if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtual environment"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "==> Virtual environment already exists — reusing it"
fi

echo "==> Installing dependencies"
"$VENV_DIR/bin/python" -m pip install -q --upgrade pip
"$VENV_DIR/bin/python" -m pip install -q -r "$BACKEND_DIR/requirements.txt"

echo "==> Preparing local directories"
mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/backups" "$ROOT_DIR/data/logs" "$BACKEND_DIR/media"
touch "$ROOT_DIR/data/.gitkeep" "$ROOT_DIR/backups/.gitkeep"

echo "==> Running database migrations"
"$VENV_DIR/bin/python" "$BACKEND_DIR/manage.py" migrate --noinput

echo ""
echo "Setup complete."
echo "Next steps:"
echo "  scripts/start_lifeos.sh     # start the backend directly"
echo "  scripts/build_mac_app.sh    # build LIFEOS.app"
