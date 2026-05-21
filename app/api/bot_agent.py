"""Generate support-agent replies for classified user messages."""

import time

from openai import OpenAI

from app.models.bot import ClusterMatch
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a helpful customer support agent for a product team.
You have classified the user's message into an internal topic cluster.
Reply in 2–4 sentences: acknowledge the issue, show understanding, and suggest a sensible next step.
Do not mention clusters, embeddings, or internal analytics. Be professional and concise."""


def generate_agent_reply(
    user_message: str,
    classification: ClusterMatch,
    is_noise: bool,
    settings: Settings | None = None,
) -> str:
    """Produce a short agent response grounded in the matched topic."""
    settings = settings or get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    topic = classification.topic or "General inquiry"
    summary = classification.summary or "No topic summary available."
    severity = classification.severity or "medium"

    user_prompt = (
        f"User message: {user_message}\n\n"
        f"Matched topic: {topic}\n"
        f"Topic summary: {summary}\n"
        f"Severity: {severity}\n"
        f"Low confidence match: {'yes' if is_noise else 'no'}\n"
    )

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            completion = client.chat.completions.create(
                model=settings.labeling_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=300,
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip()
            raise ValueError("Empty agent response")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2**attempt)
    raise RuntimeError("Agent reply generation failed") from last_error
