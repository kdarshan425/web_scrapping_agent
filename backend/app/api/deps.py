"""FastAPI dependencies: auth + wiring repositories into services for each request."""
import secrets

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import Container
from app.core.database import get_session
from app.repositories.cache_repository import CacheRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.services.cache_service import CacheService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService


def get_container(request: Request) -> Container:
    return request.app.state.container


def require_api_key(request: Request, x_api_key: str = Header(default="")) -> None:
    """Very simple shared-secret auth. Replace with OAuth/SSO for company-wide rollout."""
    expected = request.app.state.container.settings.api_key
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def get_chat_service(
    container: Container = Depends(get_container), session: AsyncSession = Depends(get_session)
) -> ChatService:
    cache = CacheService(CacheRepository(session), container.settings.cache_ttl_seconds)
    return ChatService(container, ChatRepository(session), DocumentRepository(session), cache)


def get_document_service(
    container: Container = Depends(get_container), session: AsyncSession = Depends(get_session)
) -> DocumentService:
    return DocumentService(DocumentRepository(session), container.vectors, container.embeddings)
