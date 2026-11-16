"""Small helpers shared across the project."""
import asyncio
import hashlib
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


def sha256(text: str) -> str:
    """Hex SHA-256 of a string (used for cache keys and content hashes)."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


async def retry_async(fn: Callable[[], Awaitable[T]], tries: int = 10, delay: float = 2.0) -> T:
    """Retry a startup call (DB / Qdrant may still be booting inside docker-compose)."""
    for attempt in range(1, tries + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            if attempt == tries:
                raise
            log.warning("Startup dependency not ready (%s/%s): %s", attempt, tries, exc)
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")
