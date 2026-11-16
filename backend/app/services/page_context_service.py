"""Turns a (possibly huge) web page into a SMALL, relevant context for the LLM.

Short page  -> sent whole.
Long page   -> split in chunks, embedded once (cached by page hash), and only the
               top-K chunks most similar to the question are sent. This is the
               biggest token saver in the whole system.
"""
from collections import OrderedDict

import numpy as np

from app.services.chunking import chunk_text, estimate_tokens
from app.services.embedding_service import EmbeddingService


class PageContextService:
    def __init__(self, embeddings: EmbeddingService, full_tokens: int, top_k: int, max_cached_pages: int = 20):
        self.embeddings = embeddings
        self.full_tokens = full_tokens
        self.top_k = top_k
        self.max_cached_pages = max_cached_pages
        # page_hash -> (chunks, embedding matrix). Small in-memory LRU cache.
        self._index: OrderedDict[str, tuple[list[str], np.ndarray]] = OrderedDict()

    async def select(self, page_text: str, page_hash: str, query_vector: list[float]) -> str:
        if not page_text.strip():
            return ""
        if estimate_tokens(page_text) <= self.full_tokens:
            return page_text  # small page: no retrieval needed

        chunks, matrix = await self._get_index(page_text, page_hash)
        scores = matrix @ np.asarray(query_vector)  # cosine similarity (vectors are normalised)
        top = sorted(np.argsort(scores)[::-1][: self.top_k])  # keep original page order
        return "\n...\n".join(chunks[i] for i in top)

    async def _get_index(self, page_text: str, page_hash: str) -> tuple[list[str], np.ndarray]:
        if page_hash in self._index:
            self._index.move_to_end(page_hash)
            return self._index[page_hash]
        chunks = chunk_text(page_text, size=700, overlap=80)
        matrix = np.asarray(await self.embeddings.embed_documents(chunks))
        self._index[page_hash] = (chunks, matrix)
        if len(self._index) > self.max_cached_pages:
            self._index.popitem(last=False)  # drop least recently used page
        return chunks, matrix
