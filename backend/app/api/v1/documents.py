"""Policy-document endpoints (RAG knowledge base management)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_document_service
from app.schemas.document import DocumentOut, UploadResult
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["policy documents"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _out(doc) -> DocumentOut:
    return DocumentOut(id=doc.id, filename=doc.filename, chunk_count=doc.chunk_count, created_at=doc.created_at)


@router.post("", response_model=UploadResult, status_code=201)
async def upload(file: UploadFile = File(...), service: DocumentService = Depends(get_document_service)):
    """Upload a .pdf / .docx / .txt / .md policy file. It is chunked, embedded and indexed in Qdrant."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 10 MB)")
    try:
        doc, existed = await service.ingest(file.filename or "unnamed", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return UploadResult(document=_out(doc), already_existed=existed)


@router.get("", response_model=list[DocumentOut])
async def list_documents(service: DocumentService = Depends(get_document_service)):
    return [_out(d) for d in await service.list()]


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    if not await service.delete(document_id):
        raise HTTPException(404, "Document not found")
