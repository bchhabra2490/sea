"""Chatbot service: classify, respond, and persist to Supabase."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.api.bot_agent import generate_agent_reply
from app.clustering.nearest_cluster import NearestClusterFinder
from app.db.repository import get_repository
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

    def _new_conversation_id(self) -> str:
        return (
            f"bot_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

    def _persist_classification(
        self,
        classification: dict,
        user_text: str,
        agent_text: str | None = None,
    ) -> tuple[str, int]:
        run_id = classification.get("run_id") or get_repository().get_current_run_id()
        if not run_id:
            raise ValueError("No current analysis run in database")

        nearest = classification["nearest"]
        cluster_id = -1 if classification["is_noise"] else int(nearest["cluster_id"])
        conversation_id = self._new_conversation_id()

        get_repository().register_classified_message(
            run_id=run_id,
            external_id=conversation_id,
            user_text=user_text,
            processed_text=classification["processed_text"],
            vector=classification["vector"],
            cluster_id=cluster_id,
            agent_text=agent_text,
            timestamp=date.today().isoformat(),
        )
        return conversation_id, cluster_id

    def classify_and_store(self, message: str, top_k: int = 3) -> dict:
        """Classify a user message and persist it to Supabase (no agent reply)."""
        if not self.is_ready():
            raise ValueError(
                "No cluster model available. Run POST /analyze first to build clusters."
            )

        text = message.strip()
        if not text:
            raise ValueError("Message cannot be empty")

        classification = self._finder.classify(text, top_k=top_k)
        conversation_id, cluster_id = self._persist_classification(classification, text)

        nearest = ClusterMatch(**classification["nearest"])
        logger.info(
            "Bot classify %s -> cluster %d (similarity %.3f)",
            conversation_id,
            cluster_id,
            nearest.similarity,
        )

        return {
            "conversation_id": conversation_id,
            "message": classification["message"],
            "processed_text": classification["processed_text"],
            "nearest": nearest,
            "alternatives": [ClusterMatch(**a) for a in classification["alternatives"]],
            "is_noise": classification["is_noise"],
            "min_similarity": classification["min_similarity"],
            "cluster_id": cluster_id,
            "stored": True,
            "appended_to": "supabase",
        }

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
        agent_message = generate_agent_reply(text, nearest, is_noise)

        conversation_id, cluster_id = self._persist_classification(
            classification, text, agent_text=agent_message
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
            "processed_text": classification["processed_text"],
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
