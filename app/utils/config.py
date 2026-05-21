"""Application configuration from environment variables."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value is not None else default


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    return float(value) if value is not None else default


def _env_optional_int(key: str) -> int | None:
    value = os.getenv(key)
    return int(value) if value is not None else None


class Settings(BaseModel):
    """Central configuration loaded from environment and .env file."""

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    labeling_model: str = "gpt-4o-mini"
    embedding_batch_size: int = 64
    embedding_max_retries: int = 3

    umap_n_neighbors: int = 15
    umap_n_components: int = 10
    umap_min_dist: float = 0.0
    umap_metric: str = "cosine"

    hdbscan_min_cluster_size: int = 5
    hdbscan_min_samples: int | None = None

    samples_per_cluster: int = 5

    # Bot / real-time classify: cosine similarity to nearest centroid (0–1)
    min_cluster_similarity: float = 0.55

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""
    storage_bucket: str = "proofs"
    embedding_dimension: int = 1536

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")

    @property
    def sample_conversations_path(self) -> Path:
        """Bundled demo JSONL at project_root/data (not DATA_DIR uploads volume)."""
        override = os.getenv("SAMPLE_CONVERSATIONS_PATH")
        if override:
            p = Path(override)
            return p if p.is_absolute() else self.project_root / p
        return self.project_root / "data" / "sample_conversations.jsonl"

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "Settings":
        """Load settings from environment variables and optional .env file."""
        load_dotenv(env_file)

        default_root = Path(__file__).resolve().parents[2]
        project_root = Path(os.getenv("APP_ROOT", str(default_root)))
        data_dir = Path(os.getenv("DATA_DIR", str(project_root / "data")))
        data_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            labeling_model=os.getenv("LABELING_MODEL", "gpt-4o-mini"),
            embedding_batch_size=_env_int("EMBEDDING_BATCH_SIZE", 64),
            embedding_max_retries=_env_int("EMBEDDING_MAX_RETRIES", 3),
            umap_n_neighbors=_env_int("UMAP_N_NEIGHBORS", 15),
            umap_n_components=_env_int("UMAP_N_COMPONENTS", 10),
            umap_min_dist=_env_float("UMAP_MIN_DIST", 0.0),
            umap_metric=os.getenv("UMAP_METRIC", "cosine"),
            hdbscan_min_cluster_size=_env_int("HDBSCAN_MIN_CLUSTER_SIZE", 5),
            hdbscan_min_samples=_env_optional_int("HDBSCAN_MIN_SAMPLES"),
            samples_per_cluster=_env_int("SAMPLES_PER_CLUSTER", 5),
            min_cluster_similarity=_env_float("MIN_CLUSTER_SIMILARITY", 0.55),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            storage_bucket=os.getenv("STORAGE_BUCKET", "proofs"),
            embedding_dimension=_env_int("EMBEDDING_DIMENSION", 1536),
            project_root=project_root,
            data_dir=data_dir,
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings.from_env()


def validate_supabase_config(settings: Settings | None = None) -> None:
    """Raise if required Supabase environment variables are missing."""
    s = settings or get_settings()
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", s.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", s.supabase_service_role_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Supabase is required. Set in .env: " + ", ".join(missing)
        )
