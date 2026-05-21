"""Bot integration API documentation for GET /bot/docs."""

from __future__ import annotations

from app import __version__
from app.utils.config import get_settings


def build_bot_docs() -> dict:
    """Machine-readable catalog of bot endpoints for external integrations."""
    settings = get_settings()
    threshold = settings.min_cluster_similarity
    threshold_pct = int(threshold * 100)

    return {
        "title": "Bot Integration API",
        "version": __version__,
        "description": (
            "Send user messages to the platform in real time: classify against topic "
            "clusters, optionally get an agent reply, and persist turns to Supabase."
        ),
        "integration_guide_url": "/integrate",
        "prerequisites": [
            "Platform must have completed at least one analysis run (topic clusters in Supabase).",
            "Server must have OPENAI_API_KEY configured (embeddings + optional agent reply).",
            "Poll GET /bot/status until ready=true before sending user messages.",
        ],
        "realtime_flow": [
            {
                "step": 1,
                "title": "Check readiness",
                "detail": "GET /bot/status — confirm cluster_count > 0.",
            },
            {
                "step": 2,
                "title": "Send user message",
                "detail": (
                    "POST /bot/classify to classify and store the user message, or "
                    "POST /bot/chat to also generate an agent reply."
                ),
            },
            {
                "step": 3,
                "title": "Use classification",
                "detail": (
                    "Read nearest.cluster_id, nearest.topic, nearest.similarity, and is_noise "
                    "to route tickets, trigger workflows, or tag CRM records."
                ),
            },
        ],
        "classification": {
            "threshold": {
                "min_cluster_similarity": threshold,
                "description": (
                    f"If best-match similarity is below {threshold_pct}%, is_noise is true "
                    "and cluster_id is -1 (unclustered)."
                ),
            },
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/bot/status",
                    "description": "Check whether real-time classification is available.",
                    "auth": "None",
                    "request_body": None,
                    "response_fields": ["ready", "cluster_count", "message"],
                },
                {
                    "method": "POST",
                    "path": "/bot/classify",
                    "description": (
                        "Classify one message in real time and persist the user message, "
                        "embedding, and cluster assignment to Supabase. No agent reply. "
                        "Best for external bots sending traffic to the platform."
                    ),
                    "auth": "OPENAI_API_KEY on server",
                    "request_body": {
                        "message": "string (required, 1–8000 chars)",
                        "top_k": "integer (optional, default 3, max 10)",
                    },
                    "response_fields": [
                        "conversation_id",
                        "message",
                        "processed_text",
                        "nearest { cluster_id, similarity, topic, summary, severity }",
                        "alternatives[]",
                        "is_noise",
                        "min_similarity",
                        "cluster_id",
                        "stored",
                        "appended_to",
                    ],
                },
                {
                    "method": "POST",
                    "path": "/bot/chat",
                    "description": (
                        "Classify, generate a GPT agent reply, and persist the turn "
                        "(conversation, messages, embedding, cluster assignment) to Supabase."
                    ),
                    "auth": "OPENAI_API_KEY on server",
                    "request_body": {
                        "message": "string (required, 1–8000 chars)",
                        "top_k": "integer (optional, default 3, max 10)",
                    },
                    "response_fields": [
                        "conversation_id",
                        "user_message",
                        "agent_message",
                        "classification",
                        "alternatives[]",
                        "is_noise",
                        "cluster_id",
                        "appended_to",
                    ],
                },
                {
                    "method": "GET",
                    "path": "/bot/history",
                    "description": "List recent bot turns stored on the platform (source=bot).",
                    "query_params": {"limit": "integer (default 50, max 200)"},
                },
            ],
            "examples": _bot_examples(threshold, threshold_pct),
        },
        "errors": [
            {"status": 404, "meaning": "No clusters yet — analysis not run on the platform"},
            {"status": 422, "meaning": "Empty or invalid message"},
            {"status": 400, "meaning": "OPENAI_API_KEY not configured on server"},
            {"status": 500, "meaning": "Embedding or database error"},
        ],
    }


def _bot_examples(threshold: float, threshold_pct: int) -> list[dict]:
    base = "https://your-deployment.example.com"
    return [
        {
            "title": "Check bot is ready",
            "curl": f'curl -s "{base}/bot/status"',
        },
        {
            "title": "Classify only (integrate with your bot)",
            "curl": (
                f'curl -s -X POST "{base}/bot/classify" \\\n'
                '  -H "Content-Type: application/json" \\\n'
                '  -d \'{"message": "I need a refund for order #4421", "top_k": 3}\''
            ),
        },
        {
            "title": "Classify + agent reply + persist",
            "curl": (
                f'curl -s -X POST "{base}/bot/chat" \\\n'
                '  -H "Content-Type: application/json" \\\n'
                '  -d \'{"message": "How do I cancel my subscription?"}\''
            ),
        },
        {
            "title": "Interpret is_noise",
            "note": (
                f"When nearest.similarity < {threshold:.2f}, is_noise is true and cluster_id "
                f"is -1. Otherwise use nearest.cluster_id and nearest.topic."
            ),
        },
        {
            "title": "Example classify response",
            "json": {
                "conversation_id": "bot_20250521120000_a1b2c3d4",
                "message": "I need a refund for order #4421",
                "processed_text": "need refund order 4421",
                "nearest": {
                    "cluster_id": 0,
                    "similarity": 0.78,
                    "topic": "Refund delays",
                    "summary": "Users waiting on refunds",
                    "severity": "high",
                },
                "alternatives": [],
                "is_noise": False,
                "min_similarity": threshold,
                "cluster_id": 0,
                "stored": True,
                "appended_to": "supabase",
            },
        },
    ]
