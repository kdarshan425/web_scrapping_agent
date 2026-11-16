"""Database access for chat sessions and messages."""
from sqlalchemy import delete, select

from app.models.chat import ChatMessage, ChatSession
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def create_session(self, session_id: str, page_url: str, page_title: str) -> ChatSession:
        return await self.add(
            ChatSession(id=session_id, page_url=page_url[:2048], page_title=page_title[:512])
        )

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cached: bool = False,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id, role=role, content=content, model_used=model_used,
            tokens_in=tokens_in, tokens_out=tokens_out, cached=cached,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def recent_messages(self, session_id: str, limit: int) -> list[ChatMessage]:
        """Last `limit` messages in chronological order (cheap context for the LLM)."""
        stmt = (
            select(ChatMessage).where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc()).limit(limit)
        )
        rows = list((await self.session.execute(stmt)).scalars())
        return rows[::-1]

    async def delete_session(self, session_id: str) -> bool:
        await self.session.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        chat = await self.get(session_id)
        if chat is None:
            return False
        await self.delete(chat)
        return True
