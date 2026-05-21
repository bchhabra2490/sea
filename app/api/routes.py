"""FastAPI route definitions."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.job_runner import get_job_runner, reset_job_runner_state
from app.db.repository import get_repository
from app.api.pipeline import AnalysisPipeline
from app.api.upload import save_conversation_upload
from app.models.api import (
    AnalyzeRequest,
    ClustersResponse,
    InsightsResponse,
    InsightsSummary,
    ResetDataResponse,
    TopicsResponse,
)
from app.models.pipeline_job import JobStartResponse, PipelineStatusResponse
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_pipeline: AnalysisPipeline | None = None


def get_pipeline() -> AnalysisPipeline:
    global _pipeline  # noqa: PLW0603
    if _pipeline is None:
        _pipeline = AnalysisPipeline(get_settings())
    return _pipeline


def _require_api_key() -> None:
    if not get_settings().openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is not configured. Set it in .env or environment.",
        )


def _start_background(
    input_path: Path | None,
    force_recompute: bool,
    storage_path: str | None = None,
) -> JobStartResponse:
    _require_api_key()
    try:
        return get_job_runner().start(
            get_pipeline(),
            input_path=input_path,
            force_recompute=force_recompute,
            storage_path=storage_path,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
def get_pipeline_status() -> PipelineStatusResponse:
    return get_job_runner().get_status()


@router.post("/analyze", response_model=JobStartResponse)
def analyze(request: AnalyzeRequest) -> JobStartResponse:
    """
    Start the analysis pipeline in the background.

    Omit input_path to analyze all conversations stored in Supabase.
    """
    input_path: Path | None = None
    if request.input_path:
        input_path = Path(request.input_path)
        if not input_path.is_absolute():
            input_path = get_settings().project_root / input_path
        if not input_path.exists():
            raise HTTPException(status_code=404, detail=f"Input file not found: {input_path}")
    return _start_background(input_path, request.force_recompute)


@router.post("/analyze/upload", response_model=JobStartResponse)
async def analyze_upload(
    file: UploadFile = File(
        ...,
        description="JSONL or CSV file (CSV: user column + bot column)",
    ),
    force_recompute: bool = Form(True, description="Re-run pipeline on uploaded file"),
) -> JobStartResponse:
    _require_api_key()
    try:
        settings = get_settings()
        upload = await save_conversation_upload(file, settings.data_dir)
        logger.info("Upload stored in Supabase proofs: %s", upload.proofs_storage_path)
        return _start_background(
            upload.jsonl_path,
            force_recompute,
            storage_path=upload.proofs_storage_path,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/data/reset", response_model=ResetDataResponse)
def reset_all_data() -> ResetDataResponse:
    """
    Delete all conversations, messages, clusters, embeddings, and analysis runs.

    Destructive: cannot be undone. Blocked while a pipeline job is running.
    """
    try:
        reset_job_runner_state()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    deleted = get_repository().reset_all_data()
    total = sum(deleted.values())
    logger.warning("Data reset completed: %d rows deleted", total)
    return ResetDataResponse(
        message=f"Removed {total} rows across all tables",
        deleted=deleted,
    )


@router.get("/insights", response_model=InsightsResponse)
def get_insights() -> InsightsResponse:
    pipeline = get_pipeline()
    topics = pipeline.get_topics()
    assignments, counts = pipeline.get_clusters()

    if not topics and not assignments:
        return InsightsResponse(ready=False)

    n_noise = counts.get("-1", 0)
    cluster_ids = {int(k) for k in counts if k != "-1"}
    return InsightsResponse(
        ready=True,
        summary=InsightsSummary(
            conversations_processed=sum(counts.values()),
            clusters_found=len(cluster_ids),
            noise_points=n_noise,
            topics_labeled=len(topics),
            status="ready",
        ),
        topics=topics,
        assignments=assignments,
        cluster_counts=counts,
    )


@router.get("/topics", response_model=TopicsResponse)
def get_topics() -> TopicsResponse:
    return TopicsResponse(topics=get_pipeline().get_topics())


@router.get("/clusters", response_model=ClustersResponse)
def get_clusters() -> ClustersResponse:
    assignments, counts = get_pipeline().get_clusters()
    return ClustersResponse(assignments=assignments, cluster_counts=counts)
