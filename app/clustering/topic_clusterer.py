"""UMAP + HDBSCAN clustering pipeline for conversation embeddings."""

from dataclasses import dataclass

import hdbscan
import numpy as np
import umap

from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ClusteringResult:
    """Output of the clustering pipeline."""

    cluster_labels: np.ndarray
    reduced_embeddings: np.ndarray
    umap_embeddings: np.ndarray | None = None


class TopicClusterer:
    """
    Cluster conversation embeddings using UMAP reduction and HDBSCAN.

    Pipeline: high-dimensional embeddings → UMAP (cosine) → HDBSCAN (euclidean).

    Noise points receive cluster_id -1 per HDBSCAN convention.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def fit_predict(self, embeddings: np.ndarray) -> ClusteringResult:
        """
        Reduce embeddings with UMAP and assign cluster labels with HDBSCAN.

        Args:
            embeddings: Matrix of shape (n_samples, n_features).

        Returns:
            ClusteringResult with labels and reduced coordinates.
        """
        n_samples = embeddings.shape[0]
        if n_samples < 2:
            logger.warning("Fewer than 2 samples; assigning single cluster or noise")
            labels = np.array([-1] if n_samples == 1 else [], dtype=int)
            reduced = embeddings if n_samples else np.empty((0, 0))
            return ClusteringResult(cluster_labels=labels, reduced_embeddings=reduced)

        n_neighbors = min(self.settings.umap_n_neighbors, n_samples - 1)
        n_components = min(self.settings.umap_n_components, n_samples - 1)

        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            min_dist=self.settings.umap_min_dist,
            metric=self.settings.umap_metric,
            random_state=42,
        )
        reduced = reducer.fit_transform(embeddings)
        logger.info(
            "UMAP reduced %d samples to %d dimensions (metric=%s)",
            n_samples,
            n_components,
            self.settings.umap_metric,
        )

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min(self.settings.hdbscan_min_cluster_size, n_samples),
            min_samples=self.settings.hdbscan_min_samples,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(reduced)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = int(np.sum(labels == -1))
        logger.info(
            "HDBSCAN found %d clusters (%d noise points)",
            n_clusters,
            n_noise,
        )

        return ClusteringResult(
            cluster_labels=labels.astype(int),
            reduced_embeddings=reduced,
            umap_embeddings=reduced,
        )
