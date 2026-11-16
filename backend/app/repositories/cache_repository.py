"""Database access for the response cache."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.models.cache import ResponseCache
from app.repositories.base import BaseRepository


class CacheRepository(BaseRepository[ResponseCache]):
    model = ResponseCache

    async def get_valid(self, key: str) -> ResponseCache | None:
        """Return the entry only if it has not expired; count the hit."""
        row = await self.get(key)
        if row is None or row.expires_at < datetime.now(timezone.utc):
            return None
        row.hits += 1
        await self.session.flush()
        return row

    async def upsert(self, key: str, answer: str, sources_json: str, model_used: str, ttl_seconds: int) -> None:
        await self.session.merge(
            ResponseCache(
                cache_key=key, answer=answer, sources_json=sources_json, model_used=model_used,
                hits=0, expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            )
        )
        await self.session.flush()

    async def delete_expired(self) -> None:
        await self.session.execute(
            delete(ResponseCache).where(ResponseCache.expires_at < datetime.now(timezone.utc))
        )
