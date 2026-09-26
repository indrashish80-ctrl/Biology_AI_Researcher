#!/bin/sh
# Builds the React frontend into frontend/dist (which FastAPI serves in
# production) and also stages a copy at the repo-root dist/ for static
# hosting platforms that expect dist/ at the project root.
set -e
cd "$(dirname "$0")/../frontend"
if [ ! -d node_modules ]; then
  echo "==> Installing frontend dependencies..."
  bun install
fi
echo "==> Building frontend..."
bun run build
# Stage root-level dist/ for static hosting builders (idempotent).
cd ..
rm -rf dist
mkdir -p dist
cp -r frontend/dist/. dist/
echo "==> Frontend built: frontend/dist (FastAPI) + dist/ (static hosting)."
