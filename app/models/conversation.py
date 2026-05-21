"""Pydantic models for conversation data."""

from datetime import date

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in a conversation."""

    role: str
    content: str


class Conversation(BaseModel):
    """Raw conversation record from JSONL input."""

    conversation_id: str
    messages: list[Message]
    timestamp: str | None = None


class ProcessedConversation(BaseModel):
    """Conversation after preprocessing, ready for embedding."""

    conversation_id: str
    text: str = Field(description="Concatenated, cleaned user message text")
    timestamp: str | None = None
