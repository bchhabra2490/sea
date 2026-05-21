"""Load conversations from JSONL files."""

import json
from pathlib import Path

from app.models.conversation import Conversation
from app.utils.logging import get_logger

logger = get_logger(__name__)


def load_conversations(path: str | Path) -> list[Conversation]:
    """
    Load conversations from a JSONL file.

    Each line must be a valid JSON object matching the Conversation schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    conversations: list[Conversation] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                conversations.append(Conversation.model_validate(payload))
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Skipping invalid line %d in %s: %s", line_no, path, exc)

    logger.info("Loaded %d conversations from %s", len(conversations), path)
    return conversations
