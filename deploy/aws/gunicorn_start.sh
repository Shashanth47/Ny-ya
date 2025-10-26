#!/usr/bin/env bash
set -euo pipefail

APP_HOME=/opt/legal-ai-chatbot
VENV=$APP_HOME/.venv

# Export env variables from .env if present
if [ -f "$APP_HOME/.env" ]; then
  set -a
  . "$APP_HOME/.env"
  set +a
fi

cd "$APP_HOME"
exec "$VENV/bin/gunicorn" \
  --workers 1 \
  --threads 2 \
  --bind 127.0.0.1:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  scripts.app:app