"""Database access for policy-document metadata."""
from sqlalchemy import select

from app.core.utils import sha256
from app.models.document import PolicyDocument
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[PolicyDocument]):
    model = PolicyDocument

    async def get_by_hash(self, content_hash: str) -> PolicyDocument | None:
        stmt = select(PolicyDocument).where(PolicyDocument.content_hash == content_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_all(self) -> list[PolicyDocument]:
        stmt = select(PolicyDocument).order_by(PolicyDocument.created_at.desc())
        return list((await self.session.execute(stmt)).scalars())

    async def policy_version(self) -> str:
        """Fingerprint of the current policy set. Cached answers are invalidated when it changes."""
        stmt = select(PolicyDocument.content_hash).order_by(PolicyDocument.content_hash)
        hashes = list((await self.session.execute(stmt)).scalars())
        return sha256("|".join(hashes))[:16]
