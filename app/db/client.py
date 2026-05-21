"""Supabase client factory."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_client = None


def is_supabase_configured() -> bool:
    """True when Supabase URL and service role key are set."""
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _import_create_client():
    """
    Import create_client from supabase-py.

    The repo has a ./supabase/ migrations folder that can shadow the PyPI
    package when supabase-py is not installed. Clear a bad cached module first.
    """
    project_root = Path(__file__).resolve().parents[2]
    migrations_dir = project_root / "supabase"

    mod = sys.modules.get("supabase")
    if mod is not None and not hasattr(mod, "create_client"):
        del sys.modules["supabase"]
        for key in list(sys.modules):
            if key == "supabase" or key.startswith("supabase."):
                del sys.modules[key]

    try:
        from supabase import create_client
    except ImportError as exc:
        if migrations_dir.is_dir():
            raise ImportError(
                "supabase-py is not installed (local supabase/ folder was imported instead). "
                "Run: pip install -r requirements.txt"
            ) from exc
        raise ImportError(
            "supabase-py is not installed. Run: pip install -r requirements.txt"
        ) from exc

    mod_path = getattr(sys.modules.get("supabase"), "__file__", "") or ""
    if migrations_dir.is_dir() and mod_path and str(migrations_dir) in mod_path:
        raise ImportError(
            "Local supabase/ migrations folder is shadowing supabase-py. "
            "Run: pip install -r requirements.txt"
        )

    return create_client


@lru_cache
def get_supabase_client():
    """
    Return a cached Supabase client (service role).

    Raises:
        RuntimeError: If Supabase is not configured.
    """
    global _client  # noqa: PLW0603

    if _client is not None:
        return _client

    settings = get_settings()
    if not is_supabase_configured():
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )

    create_client = _import_create_client()
    _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    logger.info("Supabase client initialized")
    return _client
