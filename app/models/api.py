"""API request and response models."""

from pydantic import BaseModel, Field

from app.models.topic import ClusterAssignment, TopicLabel


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    input_path: str | None = Field(
        default=None,
        description="Optional path to JSONL/CSV; omit to analyze all conversations in Supabase",
    )
    force_recompute: bool = Field(
        default=False,
        description="Re-run full pipeline even if a completed run exists",
    )


class AnalyzeResponse(BaseModel):
    """Response after running the analysis pipeline."""

    status: str
    conversations_processed: int
    clusters_found: int
    noise_points: int
    topics_labeled: int
    storage: str = "supabase"
    analysis_run_id: str | None = None


class TopicsResponse(BaseModel):
    """Response for GET /topics."""

    topics: list[TopicLabel]


class ClustersResponse(BaseModel):
    """Response for GET /clusters."""

    assignments: list[ClusterAssignment]
    cluster_counts: dict[str, int]


class InsightsSummary(BaseModel):
    """High-level stats for the insights dashboard."""

    conversations_processed: int = 0
    clusters_found: int = 0
    noise_points: int = 0
    topics_labeled: int = 0
    status: str | None = None


class ResetDataResponse(BaseModel):
    """Response after clearing all analysis data from Supabase."""

    message: str
    deleted: dict[str, int] = Field(default_factory=dict)


class InsightsResponse(BaseModel):
    """Aggregated payload for the insights UI."""

    ready: bool = Field(
        description="True when analysis artifacts exist in Supabase"
    )
    summary: InsightsSummary | None = None
    topics: list[TopicLabel] = Field(default_factory=list)
    assignments: list[ClusterAssignment] = Field(default_factory=list)
    cluster_counts: dict[str, int] = Field(default_factory=dict)
