"""Chat endpoints used by the browser extension."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse, HistoryItem
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, service: ChatService = Depends(get_chat_service)) -> ChatResponse:
    """Ask a question about the current page (+ company policies)."""
    return await service.handle(req)


@router.get("/{session_id}/history", response_model=list[HistoryItem])
async def history(session_id: str, service: ChatService = Depends(get_chat_service)) -> list[HistoryItem]:
    return await service.history(session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_chat(session_id: str, service: ChatService = Depends(get_chat_service)) -> None:
    if not await service.delete(session_id):
        raise HTTPException(404, "Session not found")
