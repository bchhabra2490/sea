"""Chatbot service: classify, respond, and persist to Supabase."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.api.bot_agent import generate_agent_reply
from app.clustering.nearest_cluster import NearestClusterFinder
from app.db.repository import get_repository
from app.embeddings.openai_embedder import OpenAIEmbedder
from app.models.bot import ClusterMatch
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BotChatService:
    """Handle chat turns: classify, agent reply, persist to Supabase."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._finder = NearestClusterFinder(self.settings)

    def is_ready(self) -> bool:
        return self._finder.is_ready()

    def get_history(self, limit: int = 50) -> list[dict]:
        return get_repository().get_bot_history(limit=limit)

    def handle_message(self, message: str, top_k: int = 3) -> dict:
        if not self.is_ready():
            raise ValueError(
                "No cluster model available. Run POST /analyze first to build clusters."
            )

        text = message.strip()
        if not text:
            raise ValueError("Message cannot be empty")

        classification = self._finder.classify(text, top_k=top_k)
        nearest = ClusterMatch(**classification["nearest"])
        is_noise = classification["is_noise"]
        processed_text = classification["processed_text"]

        agent_message = generate_agent_reply(text, nearest, is_noise)

        conversation_id = (
            f"bot_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        today = date.today().isoformat()

        embedder = OpenAIEmbedder(self.settings)
        vector = embedder.embed_texts([processed_text])[0]
        cluster_id = nearest.cluster_id if not is_noise else -1

        repo = get_repository()
        run_id = classification.get("run_id") or repo.get_current_run_id()
        if not run_id:
            raise ValueError("No current analysis run in database")

        repo.register_bot_message(
            run_id=run_id,
            external_id=conversation_id,
            user_text=text,
            agent_text=agent_message,
            processed_text=processed_text,
            vector=vector,
            cluster_id=cluster_id,
            timestamp=today,
        )

        logger.info(
            "Bot chat %s -> cluster %d (similarity %.3f)",
            conversation_id,
            cluster_id,
            nearest.similarity,
        )

        return {
            "conversation_id": conversation_id,
            "user_message": text,
            "agent_message": agent_message,
            "processed_text": processed_text,
            "classification": nearest,
            "alternatives": [ClusterMatch(**a) for a in classification["alternatives"]],
            "is_noise": is_noise,
            "appended_to": "supabase",
            "cluster_id": cluster_id,
        }


_service: BotChatService | None = None


def get_bot_service() -> BotChatService:
    global _service  # noqa: PLW0603
    if _service is None:
        _service = BotChatService(get_settings())
    return _service
