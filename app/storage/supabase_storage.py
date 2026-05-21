"""Upload CSV / JSONL files to Supabase Storage bucket `proofs`."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from app.db.client import get_supabase_client
from app.db.schema import STORAGE_BUCKET_PROOFS
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _guess_content_type(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".jsonl"):
        return "application/jsonl"
    if name.endswith(".csv"):
        return "text/csv"
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in base)[:200]


class SupabaseProofsStorage:
    """Store raw conversation files in the `proofs` bucket."""

    def __init__(self, bucket: str | None = None) -> None:
        settings = get_settings()
        self.bucket = bucket or settings.storage_bucket or STORAGE_BUCKET_PROOFS
        self.client = get_supabase_client()

    def upload_bytes(
        self,
        content: bytes,
        filename: str,
        folder: str = "uploads",
    ) -> str:
        if not content:
            raise ValueError("Cannot upload empty file")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = _sanitize_filename(filename)
        storage_path = f"{folder}/{timestamp}_{safe_name}"
        content_type = _guess_content_type(filename)

        self.client.storage.from_(self.bucket).upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
        logger.info("Uploaded %s to bucket %s", storage_path, self.bucket)
        return storage_path

    def download_bytes(self, storage_path: str) -> bytes:
        return self.client.storage.from_(self.bucket).download(storage_path)

    def get_public_url(self, storage_path: str) -> str:
        return self.client.storage.from_(self.bucket).create_signed_url(
            storage_path,
            expires_in=3600,
        )["signedURL"]


def upload_proof_file(content: bytes, filename: str) -> str:
    """Upload to Supabase proofs bucket; returns storage path."""
    storage = SupabaseProofsStorage()
    return storage.upload_bytes(content, filename)
