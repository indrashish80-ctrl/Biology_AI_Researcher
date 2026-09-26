#!/bin/sh
# =============================================================
# BioSynthetica Desktop Packaging
# Produces a downloadable app WITHOUT shipping Python source:
#   1. PyInstaller compiles api/server.py + the whole research
#      engine into a single native executable.
#   2. The built React frontend is bundled as static assets.
#   3. Electron wraps it into a native desktop window.
# Result: dist-desktop/BioSynthetica-<platform>/
# =============================================================
set -e
cd "$(dirname "$0")/.."

echo "==> [1/4] Building frontend..."
(cd frontend && bun install && bun run build)

echo "==> [2/4] Building backend executable with PyInstaller..."
pip3 install -q pyinstaller
pyinstaller \
  --name BioSyntheticaServer \
  --onefile \
  --noconfirm \
  --add-data "frontend/dist:frontend/dist" \
  api/server.py

echo "==> [3/4] Preparing desktop bundle..."
mkdir -p dist-desktop/resources
cp dist/BioSyntheticaServer* dist-desktop/resources/
cp -r frontend/dist dist-desktop/resources/frontend

echo "==> [4/4] Electron shell (optional):"
echo "    cd electron && npm install && npm run dist"
echo "    (requires electron + electron-builder in electron/package.json)"
echo ""
echo "Bundle ready: dist-desktop/"
echo "Run it:       ./dist-desktop/resources/BioSyntheticaServer  (then open http://localhost:8000)"
