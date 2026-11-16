"""Token cache: identical question + same page + same policies => reuse the stored answer (0 tokens)."""
import json
import re
from dataclasses import dataclass

from app.core.utils import sha256
from app.repositories.cache_repository import CacheRepository


@dataclass
class CachedAnswer:
    answer: str
    model_used: str
    sources: list[dict]


class CacheService:
    def __init__(self, repo: CacheRepository, ttl_seconds: int) -> None:
        self.repo = repo
        self.ttl = ttl_seconds

    @staticmethod
    def make_key(question: str, page_hash: str, policy_version: str, last_turn: str) -> str:
        """The key changes when: question, page content, policy set, or the previous turn changes.
        (`last_turn` matters because follow-ups like 'and the second one?' depend on it.)"""
        normalized = re.sub(r"\s+", " ", question.strip().lower())
        return sha256(f"{normalized}|{page_hash}|{policy_version}|{sha256(last_turn)}")

    async def get(self, key: str) -> CachedAnswer | None:
        row = await self.repo.get_valid(key)
        if row is None:
            return None
        return CachedAnswer(row.answer, row.model_used, json.loads(row.sources_json or "[]"))

    async def set(self, key: str, answer: str, model_used: str, sources: list[dict]) -> None:
        await self.repo.upsert(key, answer, json.dumps(sources), model_used, self.ttl)
