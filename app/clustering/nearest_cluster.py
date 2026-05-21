"""Assign new messages to the nearest topic cluster via Supabase pgvector."""

from app.db.repository import get_repository
from app.embeddings.openai_embedder import OpenAIEmbedder
from app.ingest.preprocess import preprocess_user_text
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NearestClusterFinder:
    """Map a new user message to the nearest cluster centroid via se_match_cluster_centroids."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_ready(self) -> bool:
        return get_repository().has_current_analysis()

    def invalidate_cache(self) -> None:
        """No-op; centroids are read from Supabase on each classify."""

    def cluster_count(self) -> int:
        return get_repository().cluster_count()

    def classify(
        self,
        message: str,
        top_k: int = 3,
        min_similarity: float | None = None,
    ) -> dict:
        if not self.is_ready():
            raise ValueError(
                "No cluster model available. Run POST /analyze first to build clusters."
            )

        processed = preprocess_user_text(message)
        if not processed:
            raise ValueError("Message is empty after preprocessing")

        threshold = (
            min_similarity
            if min_similarity is not None
            else self.settings.min_cluster_similarity
        )

        embedder = OpenAIEmbedder(self.settings)
        vector = embedder.embed_texts([processed])[0]

        return get_repository().classify_message(
            message=message,
            processed_text=processed,
            vector=vector,
            top_k=top_k,
            min_similarity=threshold,
        )
