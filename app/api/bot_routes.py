"""Real-time bot endpoints: chat, classify, and history."""

from fastapi import APIRouter, HTTPException

from app.api.bot_service import get_bot_service
from app.clustering.nearest_cluster import NearestClusterFinder
from app.models.bot import (
    BotChatRequest,
    BotChatResponse,
    BotClassifyRequest,
    BotClassifyResponse,
    BotHistoryResponse,
    BotStatusResponse,
    ClusterMatch,
)
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/bot", tags=["bot"])

_finder: NearestClusterFinder | None = None


def get_finder() -> NearestClusterFinder:
    global _finder  # noqa: PLW0603
    if _finder is None:
        _finder = NearestClusterFinder(get_settings())
    return _finder


def _require_api_key() -> None:
    if not get_settings().openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is not configured. Set it in .env or environment.",
        )


@router.get("/status", response_model=BotStatusResponse)
def bot_status() -> BotStatusResponse:
    """Check if cluster centroids are available for the chatbot."""
    service = get_bot_service()
    count = service._finder.cluster_count()  # noqa: SLF001
    ready = count > 0
    return BotStatusResponse(
        ready=ready,
        cluster_count=count,
        message=(
            "Ready to chat"
            if ready
            else "Run analysis first to build topic clusters"
        ),
    )


@router.get("/history", response_model=BotHistoryResponse)
def bot_history(limit: int = 50) -> BotHistoryResponse:
    """Load recent bot conversation turns from Supabase."""
    service = get_bot_service()
    items = service.get_history(limit=min(limit, 200))
    from app.models.bot import BotHistoryItem

    return BotHistoryResponse(
        messages=[BotHistoryItem(**item) for item in items],
    )


@router.post("/chat", response_model=BotChatResponse)
def bot_chat(request: BotChatRequest) -> BotChatResponse:
    """Classify, generate agent reply, and persist the turn to Supabase."""
    _require_api_key()
    service = get_bot_service()
    if not service.is_ready():
        raise HTTPException(
            status_code=404,
            detail="No clusters available. Run POST /analyze and wait for completion.",
        )
    try:
        result = service.handle_message(request.message.strip(), top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Bot chat failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BotChatResponse(**result)


@router.post("/classify", response_model=BotClassifyResponse)
def classify_message(request: BotClassifyRequest) -> BotClassifyResponse:
    """
    Embed a user message and assign it to the nearest topic cluster (no chat persistence).
    """
    _require_api_key()
    finder = get_finder()
    if not finder.is_ready():
        raise HTTPException(
            status_code=404,
            detail="No clusters available. Run POST /analyze and wait for completion.",
        )
    try:
        result = finder.classify(request.message.strip(), top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Bot classification failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BotClassifyResponse(
        message=result["message"],
        processed_text=result["processed_text"],
        nearest=ClusterMatch(**result["nearest"]),
        alternatives=[ClusterMatch(**a) for a in result["alternatives"]],
        is_noise=result["is_noise"],
        min_similarity=result["min_similarity"],
    )
