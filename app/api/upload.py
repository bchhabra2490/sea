"""Save and validate uploaded conversation files (JSONL or CSV)."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.ingest.csv_converter import conversations_to_jsonl_bytes, csv_to_conversations
from app.models.conversation import Conversation
from app.models.upload_result import UploadResult
from app.storage.supabase_storage import upload_proof_file
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jsonl", ".csv"}


def _sanitize_filename(name: str, suffix: str = ".jsonl") -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]", "_", base)
    if not base.lower().endswith(suffix):
        base = Path(base).stem + suffix
    return base[:200]


def _decode_content(content: bytes) -> None:
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )


def _validate_jsonl_content(content: bytes) -> int:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from exc

    valid_lines = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            Conversation.model_validate(payload)
            valid_lines += 1
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSONL at line {line_no}: {exc}",
            ) from exc

    if valid_lines == 0:
        raise HTTPException(status_code=400, detail="JSONL file contains no valid conversations")
    return valid_lines


def _csv_to_jsonl_bytes(content: bytes, source_name: str) -> tuple[bytes, int]:
    try:
        conversations = csv_to_conversations(content, source_name=source_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return conversations_to_jsonl_bytes(conversations), len(conversations)


async def save_conversation_upload(file: UploadFile, data_dir: Path) -> UploadResult:
    """
    Validate upload, store in Supabase `proofs` bucket, and save a temp JSONL for ingest.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .jsonl and .csv files are accepted",
        )

    content = await file.read()
    _decode_content(content)

    proofs_path = upload_proof_file(content, file.filename)

    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stem = Path(_sanitize_filename(file.filename, suffix=ext)).stem
    line_count = 0

    if ext == ".csv":
        jsonl_bytes, line_count = _csv_to_jsonl_bytes(content, source_name=stem)
        dest = uploads_dir / f"{timestamp}_{stem}.jsonl"
        dest.write_bytes(jsonl_bytes)
        upload_proof_file(jsonl_bytes, f"{stem}.jsonl")
        logger.info(
            "CSV upload %s -> %s (%d conversations), proofs=%s",
            file.filename,
            dest.name,
            line_count,
            proofs_path,
        )
    else:
        line_count = _validate_jsonl_content(content)
        dest = uploads_dir / f"{timestamp}_{stem}.jsonl"
        dest.write_bytes(content)
        logger.info(
            "JSONL upload %s (%d conversations), proofs=%s",
            dest.name,
            line_count,
            proofs_path,
        )

    return UploadResult(
        jsonl_path=dest,
        proofs_storage_path=proofs_path,
        original_filename=file.filename,
        conversation_count=line_count,
    )


save_jsonl_upload = save_conversation_upload
