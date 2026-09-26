#!/bin/sh
# Dev server: builds the frontend (if needed), then serves the app + API
# from FastAPI on 0.0.0.0:$PORT. Used for both preview and production.
set -e
cd "$(dirname "$0")/.."

PORT="${PORT:-8000}"

# Self-heal Python deps (skipped by lightweight install commands).
if ! python3 -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "==> Installing Python dependencies..."
  pip3 install -q -r requirements.txt -r api/requirements.txt
fi

# Build the frontend unless a fresh build already exists
if [ ! -d frontend/dist ]; then
  echo "==> Building frontend..."
  (cd frontend && [ -d node_modules ] || bun install)
  (cd frontend && bun run build)
fi

echo "==> Starting BioSynthetica on 0.0.0.0:${PORT}"
exec python3 api/server.py
