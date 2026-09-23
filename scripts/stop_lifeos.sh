#!/usr/bin/env bash
# Stops any running LIFEOS backend process (started via start_lifeos.sh,
# LIFEOS.app, or run_server.py directly).
set -euo pipefail

PORT="${LIFEOS_PORT:-8420}"
PIDS=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)

if [ -z "$PIDS" ]; then
  echo "LIFEOS is not running on port $PORT."
  exit 0
fi

echo "Stopping LIFEOS (pid(s): $PIDS)…"
kill $PIDS
sleep 1

STILL_RUNNING=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$STILL_RUNNING" ]; then
  echo "Process didn't stop gracefully, forcing…"
  kill -9 $STILL_RUNNING
fi

echo "Stopped."
