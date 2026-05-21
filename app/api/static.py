"""Serve the built React frontend from FastAPI."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
BOT_HTML = FRONTEND_DIST / "bot.html"

# First path segments reserved for JSON API (not SPA HTML).
_API_PREFIXES = (
    "analyze",
    "pipeline",
    "topics",
    "clusters",
    "insights",
    "data",
    "bot",
    "api",
    "health",
    "openapi.json",
    "docs",
    "redoc",
)


def mount_frontend(app) -> bool:
    """
    Mount static assets and SPA routes when frontend/dist exists.

    Returns True if the frontend was mounted.
    """
    if not FRONTEND_DIST.exists():
        return False

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    spa_router = APIRouter(include_in_schema=False)

    @spa_router.get("/")
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")

    @spa_router.get("/bot")
    async def bot_ui() -> FileResponse:
        """Standalone Topic Bot UI."""
        if not BOT_HTML.exists():
            raise HTTPException(
                status_code=404,
                detail="Bot UI not built. Run scripts/build_frontend.sh",
            )
        return FileResponse(BOT_HTML)

    @spa_router.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.split("/")[0] in _API_PREFIXES:
            raise HTTPException(status_code=404, detail="Not found")

        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    app.include_router(spa_router)
    return True
