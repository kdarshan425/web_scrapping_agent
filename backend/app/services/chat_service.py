"""Orchestrates one chat turn: load history -> run the agent -> save messages -> build response."""
import uuid

from app.agents.graph import ChatAgent
from app.core.container import Container
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.chat import ChatRequest, ChatResponse, HistoryItem, Source, Usage
from app.services.cache_service import CacheService


class ChatService:
    def __init__(self, container: Container, chat_repo: ChatRepository, doc_repo: DocumentRepository, cache: CacheService):
        self.c = container
        self.chat_repo = chat_repo
        self.doc_repo = doc_repo
        self.cache = cache

    async def handle(self, req: ChatRequest) -> ChatResponse:
        s = self.c.settings
        session_id = req.session_id or str(uuid.uuid4())
        if await self.chat_repo.get(session_id) is None:
            await self.chat_repo.create_session(session_id, req.page.url, req.page.title)

        # Short history (token saver): last N turns, each message truncated.
        rows = await self.chat_repo.recent_messages(session_id, s.history_turns * 2)
        history = [{"role": r.role, "content": r.content[: s.history_message_max_chars]} for r in rows]

        agent = ChatAgent(self.c, self.cache, self.doc_repo.policy_version)
        state = await agent.run({
            "question": req.question.strip(), "page_url": req.page.url,
            "page_title": req.page.title, "page_text": req.page.text, "history": history,
        })

        tokens_in, tokens_out = state.get("tokens_in", 0), state.get("tokens_out", 0)
        cached = bool(state.get("cached"))
        await self.chat_repo.add_message(session_id, "user", req.question)
        await self.chat_repo.add_message(
            session_id, "assistant", state["answer"], state.get("model_used"), tokens_in, tokens_out, cached
        )

        sources = [
            Source(label=f"P{i}", filename=c["filename"], score=c["score"], snippet=c["text"][:200])
            for i, c in enumerate(state.get("policy_chunks", []), 1)
        ] if state.get("guard_ok") or cached else []

        return ChatResponse(
            session_id=session_id, answer=state["answer"], model_used=state.get("model_used", ""),
            tier=state.get("tier", "none"), cached=cached, sources=sources,
            guardrail_flags=state.get("flags", []), usage=Usage(tokens_in=tokens_in, tokens_out=tokens_out),
        )

    async def history(self, session_id: str, limit: int = 50) -> list[HistoryItem]:
        rows = await self.chat_repo.recent_messages(session_id, limit)
        return [HistoryItem(role=r.role, content=r.content, created_at=r.created_at) for r in rows]

    async def delete(self, session_id: str) -> bool:
        return await self.chat_repo.delete_session(session_id)
