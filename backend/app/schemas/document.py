"""Pydantic contracts for policy-document endpoints."""
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    chunk_count: int
    created_at: datetime | None = None


class UploadResult(BaseModel):
    document: DocumentOut
    already_existed: bool = False
