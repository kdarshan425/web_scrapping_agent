"""Bulk-load every policy file in a folder into the RAG system.

    python -m scripts.ingest_policies policies/
"""
import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.container import build_container
from app.core.database import SessionFactory, init_db
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import SUPPORTED, DocumentService


async def main(folder: str) -> None:
    container = build_container(get_settings())
    await init_db()
    await container.vectors.ensure_collection()

    async with SessionFactory() as session:
        service = DocumentService(DocumentRepository(session), container.vectors, container.embeddings)
        for path in sorted(Path(folder).iterdir()):
            if path.suffix.lower() not in SUPPORTED:
                continue
            doc, existed = await service.ingest(path.name, path.read_bytes())
            print(f"{'SKIPPED (already indexed)' if existed else 'INDEXED'}: {path.name} ({doc.chunk_count} chunks)")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "policies"))
