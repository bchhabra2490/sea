"""Background pipeline execution with persisted state in Supabase."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from app.db.repository import get_repository
from app.models.api import AnalyzeResponse
from app.models.pipeline_job import (
    STAGE_LABELS,
    STAGE_PROGRESS,
    JobStartResponse,
    PipelineJobState,
    PipelineStage,
    PipelineStatusResponse,
)
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from app.api.pipeline import AnalysisPipeline

logger = get_logger(__name__)

PIPELINE_STEPS: list[PipelineStage] = [
    "queued",
    "ingesting",
    "preprocessing",
    "embedding",
    "clustering",
    "labeling",
    "completed",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_state(row: dict) -> PipelineJobState:
    """Map se_analysis_runs row to PipelineJobState."""
    stage = row.get("stage") or "idle"
    if stage not in STAGE_PROGRESS:
        stage = "idle"
    status = row.get("status", "idle")
    result = None
    if status == "completed":
        result = AnalyzeResponse(
            status="completed",
            conversations_processed=row.get("conversations_processed") or 0,
            clusters_found=row.get("clusters_found") or 0,
            noise_points=row.get("noise_points") or 0,
            topics_labeled=row.get("topics_labeled") or 0,
            storage="supabase",
            analysis_run_id=row.get("id"),
        )
    return PipelineJobState(
        job_id=row.get("id"),
        stage=stage,
        message=row.get("message") or "",
        progress_percent=row.get("progress_percent") or 0,
        input_path=row.get("input_source"),
        started_at=row.get("started_at"),
        updated_at=row.get("updated_at"),
        completed_at=row.get("completed_at"),
        error=row.get("error"),
        result=result,
    )


class PipelineJobRunner:
    """Runs the analysis pipeline in a background thread; state in se_analysis_runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._state = self._load_state()
        self._recover_interrupted()

    def _recover_interrupted(self) -> None:
        if self._state.is_running and self._state.job_id:
            self._state.stage = "failed"
            self._state.error = "Pipeline interrupted (server restarted)"
            self._state.message = self._state.error
            self._state.progress_percent = 0
            get_repository().fail_run(self._state.job_id, self._state.error)

    def get_status(self) -> PipelineStatusResponse:
        with self._lock:
            row = get_repository().get_run_for_status(self._state.job_id)
            if row:
                self._state = _row_to_state(row)
            state = self._state.model_copy(deep=True)
        return self._to_response(state)

    def start(
        self,
        pipeline: AnalysisPipeline,
        input_path: Path | None,
        force_recompute: bool = True,
        storage_path: str | None = None,
    ) -> JobStartResponse:
        with self._lock:
            if self._state.is_running or (self._thread and self._thread.is_alive()):
                raise RuntimeError("A pipeline job is already running")

            run_id = get_repository().create_run(
                input_source=str(input_path) if input_path else "database",
                storage_path=storage_path,
                status="running",
                stage="queued",
            )

            self._state = PipelineJobState(
                job_id=run_id,
                stage="queued",
                message="Pipeline queued",
                progress_percent=STAGE_PROGRESS["queued"],
                input_path=str(input_path) if input_path else "database",
                started_at=_utc_now(),
                updated_at=_utc_now(),
                completed_at=None,
                error=None,
                result=None,
            )

            self._thread = threading.Thread(
                target=self._run_job,
                args=(pipeline, input_path, force_recompute, storage_path, run_id),
                name=f"pipeline-{run_id[:8]}",
                daemon=True,
            )
            self._thread.start()

        logger.info("Started background pipeline job %s", run_id)
        return JobStartResponse(job_id=run_id)

    def _run_job(
        self,
        pipeline: AnalysisPipeline,
        input_path: Path | None,
        force_recompute: bool,
        storage_path: str | None,
        run_id: str,
    ) -> None:
        try:

            def on_progress(stage: PipelineStage, message: str) -> None:
                self._update_stage(stage, message, run_id)

            result = pipeline.run(
                input_path=input_path,
                force_recompute=force_recompute,
                on_progress=on_progress,
                analysis_run_id=run_id,
                storage_path=storage_path,
            )
            with self._lock:
                self._state.stage = "completed"
                self._state.message = "Analysis completed successfully"
                self._state.progress_percent = 100
                self._state.completed_at = _utc_now()
                self._state.updated_at = self._state.completed_at
                self._state.result = result
                self._state.error = None
            logger.info("Pipeline job %s completed", self._state.job_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline job %s failed", self._state.job_id)
            with self._lock:
                self._state.stage = "failed"
                self._state.message = "Pipeline failed"
                self._state.error = str(exc)
                self._state.progress_percent = STAGE_PROGRESS["failed"]
                self._state.completed_at = _utc_now()
                self._state.updated_at = self._state.completed_at
                get_repository().fail_run(run_id, str(exc))

    def _update_stage(self, stage: PipelineStage, message: str, run_id: str) -> None:
        with self._lock:
            self._state.stage = stage
            self._state.message = message
            self._state.progress_percent = STAGE_PROGRESS.get(stage, 0)
            self._state.updated_at = _utc_now()
            get_repository().update_run_progress(
                run_id,
                stage=stage,
                message=message,
                progress_percent=STAGE_PROGRESS.get(stage, 0),
            )

    def _load_state(self) -> PipelineJobState:
        try:
            row = get_repository().get_run_for_status(None)
            if row:
                return _row_to_state(row)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load pipeline state from Supabase: %s", exc)
        return PipelineJobState()

    def _to_response(self, state: PipelineJobState) -> PipelineStatusResponse:
        current_idx = (
            PIPELINE_STEPS.index(state.stage)
            if state.stage in PIPELINE_STEPS
            else -1
        )
        steps = []
        for idx, step in enumerate(PIPELINE_STEPS):
            if step == "completed":
                continue
            steps.append(
                {
                    "key": step,
                    "label": STAGE_LABELS[step],
                    "status": (
                        "complete"
                        if current_idx > idx
                        else "active"
                        if state.stage == step
                        else "pending"
                    ),
                }
            )

        return PipelineStatusResponse(
            job_id=state.job_id,
            stage=state.stage,
            stage_label=STAGE_LABELS.get(state.stage, state.stage),
            message=state.message,
            progress_percent=state.progress_percent,
            is_running=state.is_running,
            input_path=state.input_path,
            started_at=state.started_at,
            updated_at=state.updated_at,
            completed_at=state.completed_at,
            error=state.error,
            result=state.result,
            steps=steps,
        )


_runner: PipelineJobRunner | None = None


def get_job_runner() -> PipelineJobRunner:
    global _runner  # noqa: PLW0603
    if _runner is None:
        _runner = PipelineJobRunner()
    return _runner


def reset_job_runner_state() -> None:
    """Clear in-memory pipeline status after a data reset."""
    global _runner  # noqa: PLW0603
    if _runner is None:
        return
    with _runner._lock:
        if _runner._state.is_running:
            raise RuntimeError("Cannot reset data while a pipeline job is running")
        _runner._state = PipelineJobState()
