"""Generic repository: the ONLY layer allowed to talk to SQLAlchemy.
Services never write SQL; they call repository methods."""
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]  # set by each subclass

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: str | int) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()  # assigns ids, keeps the transaction open
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def list_all(self) -> list[ModelT]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars())
