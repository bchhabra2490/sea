"""OpenAI embedding generation with batching and persistence."""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from openai import OpenAI

from app.models.conversation import ProcessedConversation
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIEmbedder:
    """
    Generate text embeddings via OpenAI API with batching and retries.

    Persists embeddings as parquet (metadata + vectors) and numpy (.npy).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        key = api_key or self.settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is required for embedding generation")
        self.client = OpenAI(api_key=key)
        self.model = self.settings.embedding_model
        self.batch_size = self.settings.embedding_batch_size
        self.max_retries = self.settings.embedding_max_retries

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of texts, returning a float32 matrix of shape (n, dim).

        Uses batched API calls with exponential backoff on transient failures.
        """
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors = self._embed_batch_with_retry(batch)
            all_vectors.extend(vectors)
            logger.debug(
                "Embedded batch %d–%d of %d",
                start + 1,
                min(start + self.batch_size, len(texts)),
                len(texts),
            )

        return np.array(all_vectors, dtype=np.float32)

    def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:  # noqa: BLE001 — retry on any API failure
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    "Embedding batch failed (attempt %d/%d): %s. Retrying in %ds.",
                    attempt,
                    self.max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)
        raise RuntimeError(f"Embedding batch failed after {self.max_retries} retries") from last_error

    def embed_conversations(
        self,
        conversations: list[ProcessedConversation],
    ) -> tuple[np.ndarray, list[str]]:
        """Embed processed conversations; returns (embeddings, conversation_ids)."""
        ids = [c.conversation_id for c in conversations]
        texts = [c.text for c in conversations]
        embeddings = self.embed_texts(texts)
        return embeddings, ids

    def save_embeddings(
        self,
        embeddings: np.ndarray,
        conversation_ids: list[str],
        output_dir: str | Path,
        prefix: str = "embeddings",
    ) -> tuple[Path, Path]:
        """
        Save embeddings to parquet and numpy files under output_dir.

        Returns:
            Tuple of (parquet_path, numpy_path).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = output_dir / f"{prefix}.parquet"
        numpy_path = output_dir / f"{prefix}.npy"
        ids_path = output_dir / f"{prefix}_ids.npy"

        df = pd.DataFrame(
            {
                "conversation_id": conversation_ids,
                "embedding": [row.tolist() for row in embeddings],
            }
        )
        df.to_parquet(parquet_path, index=False)
        np.save(numpy_path, embeddings)
        np.save(ids_path, np.array(conversation_ids, dtype=object))

        logger.info("Saved embeddings to %s and %s", parquet_path, numpy_path)
        return parquet_path, numpy_path

    @staticmethod
    def load_embeddings(
        output_dir: str | Path,
        prefix: str = "embeddings",
    ) -> tuple[np.ndarray, list[str]]:
        """Load embeddings and conversation IDs from disk."""
        output_dir = Path(output_dir)
        numpy_path = output_dir / f"{prefix}.npy"
        ids_path = output_dir / f"{prefix}_ids.npy"

        if not numpy_path.exists():
            raise FileNotFoundError(f"Embeddings file not found: {numpy_path}")

        embeddings = np.load(numpy_path)
        if ids_path.exists():
            ids = np.load(ids_path, allow_pickle=True).tolist()
        else:
            parquet_path = output_dir / f"{prefix}.parquet"
            df = pd.read_parquet(parquet_path)
            ids = df["conversation_id"].tolist()

        return embeddings, ids
