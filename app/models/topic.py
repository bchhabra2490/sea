"""Pydantic models for clustering and topic labeling."""

from typing import Literal

from pydantic import BaseModel, Field


SeverityLevel = Literal["low", "medium", "high", "critical"]


class ClusterAssignment(BaseModel):
    """Cluster membership for a single conversation."""

    conversation_id: str
    cluster_id: int = Field(description="HDBSCAN cluster label; -1 indicates noise")
    text: str | None = None


class TopicLabel(BaseModel):
    """GPT-generated label for a conversation cluster."""

    cluster_id: int
    topic: str
    summary: str
    severity: SeverityLevel
