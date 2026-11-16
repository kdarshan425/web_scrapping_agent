"""Application entry point:  uvicorn app.main:app"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.container import build_container
from app.core.database import SessionFactory, init_db
from app.core.logging import setup_logging
from app.core.utils import retry_async
from app.repositories.cache_repository import CacheRepository

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect DB + Qdrant, load the embedding model. Shutdown: nothing special."""
    setup_logging()
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container

    await retry_async(init_db)                            # create tables
    await retry_async(container.vectors.ensure_collection)  # create Qdrant collection
    await container.embeddings.warm_up()                  # download/load model once
    async with SessionFactory() as session:               # housekeeping
        await CacheRepository(session).delete_expired()
        await session.commit()
    log.info("Startup complete")
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Open endpoint (no API key) for docker / load-balancer health checks."""
    return {"status": "ok"}
