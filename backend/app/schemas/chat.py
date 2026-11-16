"""Pydantic request / response contracts for the chat API."""
from datetime import datetime

from pydantic import BaseModel, Field


class PageContext(BaseModel):
    """What the extension read from the browser tab."""

    url: str = Field(default="", max_length=2048)
    title: str = Field(default="", max_length=512)
    text: str = Field(default="", max_length=300_000)


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Omit to start a new chat")
    question: str = Field(min_length=1, max_length=4000)
    page: PageContext


class Source(BaseModel):
    """A company-policy excerpt that was used to ground the answer."""

    label: str  # e.g. "P1"
    filename: str
    score: float
    snippet: str


class Usage(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    model_used: str
    tier: str  # "small" | "large" | "cache" | "none"
    cached: bool = False
    sources: list[Source] = []
    guardrail_flags: list[str] = []
    usage: Usage = Usage()


class HistoryItem(BaseModel):
    role: str
    content: str
    created_at: datetime | None = None
