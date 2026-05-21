#!/usr/bin/env python3
"""
Run a full pipeline re-analysis (for cron or manual use).

Example:
  python scripts/run_daily_analysis.py
  CRON_INPUT_PATH=data/sample_conversations.jsonl python scripts/run_daily_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.jobs.daily_reanalysis import run_daily_reanalysis  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_daily_reanalysis())
