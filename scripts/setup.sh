#!/bin/sh
# One-time setup: install Python + frontend dependencies.
set -e
cd "$(dirname "$0")/.."
echo "==> Installing Python dependencies..."
pip3 install -q -r requirements.txt -r api/requirements.txt
echo "==> Installing frontend dependencies..."
cd frontend && bun install
echo "==> Setup complete."
