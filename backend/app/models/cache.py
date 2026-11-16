"""ORM model for the LLM response cache (saves tokens on repeated questions)."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResponseCache(Base):
    __tablename__ = "response_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    hits: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
