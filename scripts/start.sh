#!/bin/sh
# Production start script for Railway / Docker.
set -e

PORT="${PORT:-8000}"
APP_ROOT="${APP_ROOT:-/app}"

export APP_ROOT

DATA_DIR="${DATA_DIR:-$APP_ROOT/data}"

mkdir -p "$DATA_DIR" "$DATA_DIR/uploads" "$APP_ROOT/logs"

echo "Starting Sentiment Engine on port $PORT"
echo "  DATA_DIR=$DATA_DIR (temp uploads only; persistence in Supabase)"

exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
