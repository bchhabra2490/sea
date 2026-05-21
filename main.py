"""Application entry point for the conversational intelligence engine."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.bot_routes import router as bot_router
from app.api.routes import router
from app.api.static import mount_frontend
from app.utils.config import validate_supabase_config
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize logging and validate Supabase on startup."""
    import logging

    setup_logging()
    validate_supabase_config()
    logging.getLogger(__name__).info(
        "Frontend: %s",
        "mounted at /" if _frontend_mounted else "not built — run scripts/build_frontend.sh",
    )
    yield


app = FastAPI(
    title="Sentiment Engine",
    description="Conversational intelligence engine for PM analytics",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


app.include_router(router)
app.include_router(bot_router)

_frontend_mounted = mount_frontend(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
