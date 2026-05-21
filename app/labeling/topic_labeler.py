"""GPT-based topic labeling for conversation clusters."""

import json
import random
import time
from collections import defaultdict

from openai import OpenAI

from app.models.conversation import ProcessedConversation
from app.models.topic import TopicLabel
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a product analytics assistant analyzing user support conversations.
Given sample user messages from one cluster, produce a concise topic label for PM teams.

Respond with valid JSON only, using this schema:
{
  "topic": "short topic name (3-6 words)",
  "summary": "one sentence describing the user pain point",
  "severity": "low" | "medium" | "high" | "critical"
}

Severity guidance:
- critical: outages, data loss, security, blocked revenue
- high: refunds failed, account access blocked, repeated failures
- medium: confusion, delays, workaround needed
- low: general questions, minor UX friction
"""


class TopicLabeler:
    """Label conversation clusters using representative samples and GPT."""

    def __init__(
        self,
        settings: Settings | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        key = api_key or self.settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is required for topic labeling")
        self.client = OpenAI(api_key=key)
        self.model = self.settings.labeling_model
        self.samples_per_cluster = self.settings.samples_per_cluster

    def label_clusters(
        self,
        conversations: list[ProcessedConversation],
        cluster_labels: list[int],
    ) -> list[TopicLabel]:
        """
        Generate topic labels for each non-noise cluster.

        Args:
            conversations: Processed conversations aligned with cluster_labels.
            cluster_labels: Cluster ID per conversation (same order).

        Returns:
            TopicLabel for each distinct cluster (excluding -1 noise).
        """
        by_cluster: dict[int, list[ProcessedConversation]] = defaultdict(list)
        for conv, label in zip(conversations, cluster_labels, strict=True):
            if label == -1:
                continue
            by_cluster[int(label)].append(conv)

        labels: list[TopicLabel] = []
        for cluster_id in sorted(by_cluster.keys()):
            samples = self._select_representative(by_cluster[cluster_id])
            label = self._label_cluster(cluster_id, samples)
            labels.append(label)
            logger.info("Labeled cluster %d: %s", cluster_id, label.topic)

        return labels

    def _select_representative(
        self,
        conversations: list[ProcessedConversation],
    ) -> list[ProcessedConversation]:
        """Pick diverse representative conversations (longest + random mix)."""
        if len(conversations) <= self.samples_per_cluster:
            return conversations

        sorted_by_len = sorted(conversations, key=lambda c: len(c.text), reverse=True)
        # Take top longest half, random from remainder for diversity.
        n_long = max(1, self.samples_per_cluster // 2)
        long_samples = sorted_by_len[:n_long]
        remainder = [c for c in conversations if c not in long_samples]
        n_random = self.samples_per_cluster - len(long_samples)
        random_samples = random.sample(remainder, min(n_random, len(remainder)))
        return long_samples + random_samples

    def _label_cluster(
        self,
        cluster_id: int,
        samples: list[ProcessedConversation],
    ) -> TopicLabel:
        """Call GPT to produce topic name, summary, and severity for one cluster."""
        sample_text = "\n---\n".join(f"[{i + 1}] {s.text[:500]}" for i, s in enumerate(samples))
        user_prompt = (
            f"Cluster ID: {cluster_id}\n"
            f"Number of conversations in cluster: unknown to you; focus on themes.\n\n"
            f"Sample user messages:\n{sample_text}"
        )

        response = self._chat_with_retry(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        parsed = self._parse_label_response(response, cluster_id)
        return parsed

    def _chat_with_retry(self, messages: list[dict[str, str]], max_retries: int = 3) -> str:
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from labeling model")
                return content
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                wait = 2**attempt
                logger.warning("Labeling failed (attempt %d): %s", attempt, exc)
                time.sleep(wait)
        raise RuntimeError("Topic labeling failed after retries") from last_error

    def _parse_label_response(self, content: str, cluster_id: int) -> TopicLabel:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from labeler: {content}") from exc

        severity = str(data.get("severity", "medium")).lower()
        if severity not in ("low", "medium", "high", "critical"):
            severity = "medium"

        return TopicLabel(
            cluster_id=cluster_id,
            topic=str(data.get("topic", f"Cluster {cluster_id}")),
            summary=str(data.get("summary", "")),
            severity=severity,  # type: ignore[arg-type]
        )
