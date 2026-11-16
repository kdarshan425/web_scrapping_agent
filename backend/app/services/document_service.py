"""Ingest company-policy files into the RAG system (Postgres metadata + Qdrant vectors)."""
import io
import logging
import uuid

from app.core.utils import sha256
from app.models.document import PolicyDocument
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import PolicyVectorRepository
from app.services.chunking import chunk_text
from app.services.embedding_service import EmbeddingService

log = logging.getLogger(__name__)
SUPPORTED = (".pdf", ".docx", ".txt", ".md")


def extract_text(filename: str, data: bytes) -> str:
    """Convert an uploaded file to plain text."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        return "\n\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages)
    if name.endswith(".docx"):
        from docx import Document

        return "\n\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type. Use one of: {', '.join(SUPPORTED)}")


class DocumentService:
    def __init__(self, repo: DocumentRepository, vectors: PolicyVectorRepository, embeddings: EmbeddingService):
        self.repo, self.vectors, self.embeddings = repo, vectors, embeddings

    async def ingest(self, filename: str, data: bytes) -> tuple[PolicyDocument, bool]:
        """Returns (document, already_existed). Same content is never stored twice."""
        text = extract_text(filename, data).strip()
        if not text:
            raise ValueError("No readable text found in the file.")

        content_hash = sha256(text)
        existing = await self.repo.get_by_hash(content_hash)
        if existing:
            return existing, True

        chunks = chunk_text(text)
        vectors = await self.embeddings.embed_documents(chunks)
        doc = await self.repo.add(
            PolicyDocument(id=str(uuid.uuid4()), filename=filename, content_hash=content_hash, chunk_count=len(chunks))
        )
        await self.vectors.upsert_chunks(doc.id, filename, chunks, vectors)
        log.info("Ingested %s (%s chunks)", filename, len(chunks))
        return doc, False

    async def delete(self, document_id: str) -> bool:
        doc = await self.repo.get(document_id)
        if doc is None:
            return False
        await self.vectors.delete_document(document_id)
        await self.repo.delete(doc)
        return True

    async def list(self) -> list[PolicyDocument]:
        return await self.repo.list_all()
