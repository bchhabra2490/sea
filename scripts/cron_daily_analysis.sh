#!/usr/bin/env bash
# Wrapper for cron: activate venv, load .env, run daily re-analysis, log output.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
CRON_LOG="$LOG_DIR/cron.log"

{
  echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') daily analysis cron ==="

  if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
  fi

  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
  else
    PYTHON="${PYTHON:-python3}"
  fi

  "$PYTHON" "$ROOT/scripts/run_daily_analysis.py"
  echo "Exit code: $?"
} >> "$CRON_LOG" 2>&1
