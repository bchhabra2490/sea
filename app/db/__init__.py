"""Supabase / PostgreSQL database access."""

from app.db.client import get_supabase_client, is_supabase_configured

__all__ = ["get_supabase_client", "is_supabase_configured"]
