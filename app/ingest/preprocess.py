"""Preprocess raw conversations for embedding and clustering."""

import re

from app.models.conversation import Conversation, ProcessedConversation
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Common greetings and filler phrases (case-insensitive).
_GREETING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings)\b[!.?,]*\s*",
        r"^(thanks|thank\s+you|thx)\b[!.?,]*\s*",
        r"^(please|pls)\b[!.?,]*\s*",
        r"^(ok|okay|sure|yes|no)\b[!.?,]*\s*$",
        r"\b(just\s+)?(checking\s+in|following\s+up)\b[!.?,]*\s*",
    ]
]

_FILLER_PHRASES: list[str] = [
    "thanks in advance",
    "thank you in advance",
    "hope you are well",
    "hope you're well",
    "have a nice day",
    "have a great day",
]


def _is_user_message(role: str) -> bool:
    return role.strip().lower() == "user"


def _strip_greetings_and_filler(text: str) -> str:
    """Remove leading greetings and known filler phrases from user text."""
    cleaned = text.strip()
    for pattern in _GREETING_PATTERNS:
        cleaned = pattern.sub("", cleaned).strip()
    lowered = cleaned.lower()
    for phrase in _FILLER_PHRASES:
        lowered = lowered.replace(phrase, " ")
    # Collapse repeated whitespace after removals.
    return re.sub(r"\s+", " ", lowered).strip()


def preprocess_user_text(text: str) -> str | None:
    """
    Preprocess a single user-typed message (same rules as conversation user turns).

    Returns None if the message is empty after cleaning.
    """
    cleaned = _strip_greetings_and_filler(text.strip())
    if not cleaned:
        return None
    return re.sub(r"\s+", " ", cleaned).strip()


def preprocess_conversation(conversation: Conversation) -> ProcessedConversation | None:
    """
    Extract user messages, clean filler, and concatenate into one text block.

    Returns None if the conversation has no usable user content.
    """
    user_parts: list[str] = []
    for message in conversation.messages:
        if not _is_user_message(message.role):
            continue
        cleaned = _strip_greetings_and_filler(message.content)
        if cleaned:
            user_parts.append(cleaned)

    if not user_parts:
        return None

    combined = " ".join(user_parts)
    combined = re.sub(r"\s+", " ", combined).strip()
    if not combined:
        return None

    return ProcessedConversation(
        conversation_id=conversation.conversation_id,
        text=combined,
        timestamp=conversation.timestamp,
    )


def preprocess_conversations(
    conversations: list[Conversation],
) -> list[ProcessedConversation]:
    """
    Preprocess a batch of conversations, dropping empty results.

    Args:
        conversations: Raw conversations from ingestion.

    Returns:
        List of processed conversations with non-empty user text.
    """
    processed: list[ProcessedConversation] = []
    skipped = 0

    for conversation in conversations:
        result = preprocess_conversation(conversation)
        if result is None:
            skipped += 1
            continue
        processed.append(result)

    logger.info(
        "Preprocessed %d conversations (%d skipped as empty)",
        len(processed),
        skipped,
    )
    return processed
