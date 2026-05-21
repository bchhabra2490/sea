"""API models for real-time bot message classification."""

from typing import Literal

from pydantic import BaseModel, Field

SeverityLevel = Literal["low", "medium", "high", "critical"]


class BotClassifyRequest(BaseModel):
    """Classify a single user message against existing clusters."""

    message: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=3, ge=1, le=10)


class ClusterMatch(BaseModel):
    """Nearest (or alternative) cluster match for a message."""

    cluster_id: int
    similarity: float = Field(description="Cosine similarity to cluster centroid (0–1)")
    topic: str | None = None
    summary: str | None = None
    severity: SeverityLevel | None = None


class BotClassifyResponse(BaseModel):
    """Result of classifying one message in real time."""

    message: str
    processed_text: str
    nearest: ClusterMatch
    alternatives: list[ClusterMatch] = Field(default_factory=list)
    is_noise: bool = Field(description="True when similarity is below confidence threshold")
    min_similarity: float


class BotStatusResponse(BaseModel):
    """Whether the bot can classify messages (pipeline artifacts present)."""

    ready: bool
    cluster_count: int = 0
    message: str


class BotChatRequest(BaseModel):
    """Send a user message in the support chatbot."""

    message: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=3, ge=1, le=10)


class BotChatResponse(BaseModel):
    """Agent reply plus classification and persistence metadata."""

    conversation_id: str
    user_message: str
    agent_message: str
    processed_text: str
    classification: ClusterMatch
    alternatives: list[ClusterMatch] = Field(default_factory=list)
    is_noise: bool = False
    cluster_id: int
    appended_to: str


class BotHistoryItem(BaseModel):
    """A past bot conversation turn from JSONL."""

    conversation_id: str
    timestamp: str | None = None
    user_message: str
    agent_message: str


class BotHistoryResponse(BaseModel):
    """Chat history loaded from sample JSONL."""

    messages: list[BotHistoryItem]
