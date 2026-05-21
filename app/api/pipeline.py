"""End-to-end Phase 1 analysis pipeline (Supabase-backed)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.clustering.topic_clusterer import TopicClusterer
from app.db.repository import get_repository
from app.embeddings.openai_embedder import OpenAIEmbedder
from app.ingest.loader import load_conversations
from app.ingest.preprocess import preprocess_conversations
from app.labeling.topic_labeler import TopicLabeler
from app.models.api import AnalyzeResponse
from app.models.pipeline_job import STAGE_PROGRESS, PipelineStage
from app.models.topic import ClusterAssignment, TopicLabel
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[PipelineStage, str], None]


class AnalysisPipeline:
    """Orchestrates ingestion → preprocessing → embeddings → clustering → labeling in Supabase."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(
        self,
        input_path: str | Path | None = None,
        force_recompute: bool = False,
        on_progress: ProgressCallback | None = None,
        analysis_run_id: str | None = None,
        storage_path: str | None = None,
    ) -> AnalyzeResponse:
        """Execute the full pipeline. Loads from JSONL/CSV path or all rows in Supabase when path is omitted."""
        path = Path(input_path) if input_path else None

        def progress(stage: PipelineStage, message: str) -> None:
            if on_progress:
                on_progress(stage, message)

        repo = get_repository()

        if not force_recompute and repo.has_current_analysis():
            logger.info("Loading existing analysis from Supabase")
            progress("completed", "Loaded results from database")
            return self._build_response_from_db(repo)

        input_label = str(path) if path else "database"
        run_id = analysis_run_id or repo.create_run(
            input_source=input_label,
            storage_path=storage_path,
        )

        def db_progress(stage: PipelineStage, message: str) -> None:
            progress(stage, message)
            if stage in STAGE_PROGRESS:
                repo.update_run_progress(
                    run_id,
                    stage=stage,
                    message=message,
                    progress_percent=STAGE_PROGRESS[stage],
                    status="running",
                )

        try:
            if path:
                logger.info("Starting pipeline for file %s (run %s)", path, run_id)
                db_progress("ingesting", f"Loading conversations from {path.name}")
                raw = load_conversations(path)
                resolved = path.resolve()
                if resolved == self.settings.sample_conversations_path.resolve():
                    source = "sample"
                elif "uploads" in path.parts:
                    source = "upload"
                else:
                    source = "jsonl"
            else:
                logger.info("Starting pipeline from database (run %s)", run_id)
                db_progress("ingesting", "Loading conversations from Supabase")
                raw = repo.load_all_conversations()
                source = "jsonl"
                if not raw:
                    raise ValueError(
                        "No conversations in database. Upload a file or ingest sample data first."
                    )

            id_map = repo.upsert_conversations(raw, source=source)

            db_progress("preprocessing", "Extracting and cleaning user messages")
            processed = preprocess_conversations(raw)
            if not processed:
                raise ValueError("No valid conversations after preprocessing")
            repo.save_processed_texts(run_id, processed, id_map)

            db_progress("embedding", f"Generating embeddings for {len(processed)} conversations")
            embedder = OpenAIEmbedder(self.settings)
            embeddings, _ids = embedder.embed_conversations(processed)
            repo.save_embeddings(run_id, embeddings, processed, id_map)

            db_progress("clustering", "Running UMAP and HDBSCAN clustering")
            clusterer = TopicClusterer(self.settings)
            result = clusterer.fit_predict(embeddings)
            labels = result.cluster_labels.tolist()
            repo.save_cluster_assignments(run_id, processed, labels, id_map)
            repo.save_cluster_centroids(run_id, embeddings, processed, labels, id_map)

            db_progress("labeling", "Generating topic labels with GPT")
            labeler = TopicLabeler(self.settings)
            topics = labeler.label_clusters(processed, labels)
            repo.save_topic_labels(run_id, topics)

            label_arr = np.array(labels)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = int(np.sum(label_arr == -1))

            repo.complete_run(
                run_id,
                conversations_processed=len(processed),
                clusters_found=n_clusters,
                noise_points=n_noise,
                topics_labeled=len(topics),
            )

            db_progress("completed", "Pipeline finished successfully")
            return AnalyzeResponse(
                status="completed",
                conversations_processed=len(processed),
                clusters_found=n_clusters,
                noise_points=n_noise,
                topics_labeled=len(topics),
                storage="supabase",
                analysis_run_id=run_id,
            )
        except Exception:
            repo.fail_run(run_id, "Pipeline failed")
            raise

    def get_topics(self) -> list[TopicLabel]:
        return get_repository().get_topics()

    def get_clusters(self) -> tuple[list[ClusterAssignment], dict[str, int]]:
        return get_repository().get_cluster_assignments()

    def has_results(self) -> bool:
        repo = get_repository()
        if not repo.resolve_run_id():
            return False
        topics = repo.get_topics()
        assignments, _ = repo.get_cluster_assignments()
        return bool(topics or assignments)

    def _build_response_from_db(self, repo) -> AnalyzeResponse:
        summary = repo.get_insights_summary()
        if not summary:
            raise ValueError("No completed analysis in database")
        run_id = repo.get_current_run_id()
        return AnalyzeResponse(
            status="loaded_from_cache",
            conversations_processed=summary["conversations_processed"],
            clusters_found=summary["clusters_found"],
            noise_points=summary["noise_points"],
            topics_labeled=summary["topics_labeled"],
            storage="supabase",
            analysis_run_id=run_id,
        )
