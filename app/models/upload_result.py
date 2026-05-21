"""Upload result metadata."""

from pathlib import Path

from pydantic import BaseModel


class UploadResult(BaseModel):
    """Paths after validating and storing an uploaded conversation file."""

    jsonl_path: Path
    proofs_storage_path: str | None = None
    original_filename: str
    conversation_count: int = 0

    model_config = {"arbitrary_types_allowed": True}
