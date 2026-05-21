"""Daily full re-analysis of conversations stored in Supabase."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.api.pipeline import AnalysisPipeline
from app.utils.config import Settings, get_settings
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)

LOG_DIR = "logs"
LOG_FILE = "daily_analysis.log"


def _resolve_input_path(settings: Settings, input_path: str | Path | None) -> Path | None:
    """Return a file path for ingest, or None to load all conversations from Supabase."""
    if input_path:
        path = Path(input_path)
        if not path.is_absolute():
            path = settings.project_root / path
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path
    return None


def run_daily_reanalysis(
    input_path: str | Path | None = None,
    log_to_file: bool = True,
) -> int:
    """
    Run the full analysis pipeline with force_recompute=True.

    When input_path is omitted, analyzes all conversations in Supabase.
    """
    settings = get_settings()
    setup_logging()

    if log_to_file:
        log_dir = settings.project_root / LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(file_handler)

    started = datetime.now(timezone.utc).isoformat()
    logger.info("Daily re-analysis started at %s", started)

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is not set; aborting daily job")
        return 1

    try:
        path = _resolve_input_path(settings, input_path)
        logger.info("Input: %s", path or "database")

        pipeline = AnalysisPipeline(settings)
        result = pipeline.run(input_path=path, force_recompute=True)

        logger.info(
            "Daily re-analysis completed: %d conversations, %d clusters, %d topics",
            result.conversations_processed,
            result.clusters_found,
            result.topics_labeled,
        )
        return 0
    except Exception:  # noqa: BLE001
        logger.exception("Daily re-analysis failed")
        return 1


def main() -> None:
    sys.exit(run_daily_reanalysis())
