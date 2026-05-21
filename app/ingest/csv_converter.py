"""Convert two-column CSV (user, bot) into conversation JSONL records."""

import csv
import io
import json
from datetime import date

import pandas as pd

from app.models.conversation import Conversation, Message

USER_COLUMN_ALIASES = frozenset(
    {"user", "customer", "client", "human", "question", "query", "message", "text", "input"}
)
BOT_COLUMN_ALIASES = frozenset(
    {"bot", "assistant", "agent", "support", "reply", "response", "answer", "output"}
)


def _normalize_header(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _resolve_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Resolve user and bot column names.

    Uses header aliases when present; otherwise treats the first two columns as user/bot.
    """
    columns = list(df.columns)
    if len(columns) < 2:
        raise ValueError("CSV must have at least two columns (user and bot)")

    normalized = {_normalize_header(col): col for col in columns}

    user_col: str | None = None
    bot_col: str | None = None

    for key, original in normalized.items():
        if key in USER_COLUMN_ALIASES and user_col is None:
            user_col = original
        if key in BOT_COLUMN_ALIASES and bot_col is None:
            bot_col = original

    if user_col is None:
        user_col = columns[0]
    if bot_col is None:
        bot_col = columns[1] if columns[1] != user_col else (columns[2] if len(columns) > 2 else columns[1])

    if user_col == bot_col:
        raise ValueError("Could not identify separate user and bot columns in CSV header")

    return user_col, bot_col


def _looks_like_header_cells(cells: list[str]) -> bool:
    """Heuristic: row values look like column titles, not conversation content."""
    if len(cells) < 2:
        return False
    values = [_normalize_header(c) for c in cells[:2]]
    return any(v in USER_COLUMN_ALIASES or v in BOT_COLUMN_ALIASES for v in values)


def csv_to_conversations(content: bytes, source_name: str = "upload") -> list[Conversation]:
    """
    Parse CSV bytes into Conversation models.

    Each non-empty row becomes one conversation with user then assistant messages.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded") from exc

    if not text.strip():
        raise ValueError("CSV file is empty")

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("CSV file is empty")

    first_cells = next(csv.reader([lines[0]]))
    has_header = _looks_like_header_cells(first_cells)

    if has_header:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(
            io.StringIO(text),
            header=None,
            names=["user", "bot"],
            dtype=str,
            keep_default_na=False,
        )

    df = df.fillna("")

    if df.empty or len(df.columns) < 2:
        raise ValueError("CSV must have at least two columns (user and bot)")

    user_col, bot_col = _resolve_columns(df)
    today = date.today().isoformat()
    conversations: list[Conversation] = []

    for idx, row in df.iterrows():
        user_text = str(row[user_col]).strip()
        bot_text = str(row[bot_col]).strip()
        if not user_text and not bot_text:
            continue

        messages: list[Message] = []
        if user_text:
            messages.append(Message(role="user", content=user_text))
        if bot_text:
            messages.append(Message(role="assistant", content=bot_text))

        if not messages:
            continue

        conversations.append(
            Conversation(
                conversation_id=f"{source_name}_{idx + 1}",
                messages=messages,
                timestamp=today,
            )
        )

    if not conversations:
        raise ValueError("CSV contains no rows with user or bot text")

    return conversations


def conversations_to_jsonl_bytes(conversations: list[Conversation]) -> bytes:
    """Serialize conversations to JSONL bytes."""
    lines = [json.dumps(c.model_dump(), ensure_ascii=False) for c in conversations]
    return ("\n".join(lines) + "\n").encode("utf-8")
