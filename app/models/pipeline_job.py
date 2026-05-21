"""Models for background pipeline job state."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.api import AnalyzeResponse

PipelineStage = Literal[
    "idle",
    "queued",
    "ingesting",
    "preprocessing",
    "embedding",
    "clustering",
    "labeling",
    "completed",
    "failed",
]

STAGE_PROGRESS: dict[PipelineStage, int] = {
    "idle": 0,
    "queued": 5,
    "ingesting": 15,
    "preprocessing": 30,
    "embedding": 50,
    "clustering": 75,
    "labeling": 90,
    "completed": 100,
    "failed": 0,
}

STAGE_LABELS: dict[PipelineStage, str] = {
    "idle": "Idle",
    "queued": "Queued",
    "ingesting": "Ingesting conversations",
    "preprocessing": "Preprocessing user messages",
    "embedding": "Generating embeddings",
    "clustering": "Clustering topics",
    "labeling": "Labeling clusters",
    "completed": "Completed",
    "failed": "Failed",
}


class PipelineJobState(BaseModel):
    """Persisted pipeline execution state."""

    job_id: str | None = None
    stage: PipelineStage = "idle"
    message: str = "No pipeline run in progress"
    progress_percent: int = 0
    input_path: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    result: AnalyzeResponse | None = None

    @property
    def is_running(self) -> bool:
        return self.stage in {
            "queued",
            "ingesting",
            "preprocessing",
            "embedding",
            "clustering",
            "labeling",
        }


class PipelineStatusResponse(BaseModel):
    """API response for pipeline job status."""

    job_id: str | None = None
    stage: PipelineStage
    stage_label: str
    message: str
    progress_percent: int = 0
    is_running: bool = False
    input_path: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    result: AnalyzeResponse | None = None
    steps: list[dict[str, str | bool]] = Field(default_factory=list)


class JobStartResponse(BaseModel):
    """Response when a background pipeline job is enqueued."""

    job_id: str
    status: str = "queued"
    message: str = "Pipeline started in background"
