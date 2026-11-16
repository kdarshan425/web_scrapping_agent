"""Holds the long-lived (stateless / thread-safe) objects, created once at startup.
Per-request objects (DB session, repositories, services) are built in api/deps.py."""
from dataclasses import dataclass

from app.core.config import Settings
from app.repositories.vector_repository import PolicyVectorRepository
from app.services.embedding_service import EmbeddingService
from app.services.guardrails import InputGuard, OutputGuard
from app.services.llm_client import LLMClient
from app.services.model_router import ModelRouter
from app.services.page_context_service import PageContextService
from app.services.verifier import PolicyVerifier


@dataclass
class Container:
    settings: Settings
    embeddings: EmbeddingService
    vectors: PolicyVectorRepository
    llm: LLMClient
    router: ModelRouter
    input_guard: InputGuard
    output_guard: OutputGuard
    verifier: PolicyVerifier
    page_service: PageContextService


def build_container(s: Settings) -> Container:
    embeddings = EmbeddingService(s.embedding_model, s.embedding_cache_dir)
    llm = LLMClient(s.llm_base_url, s.llm_api_key)
    return Container(
        settings=s,
        embeddings=embeddings,
        # vectors=PolicyVectorRepository(s.qdrant_url, s.qdrant_collection, s.embedding_dim),
        vectors=PolicyVectorRepository(s.qdrant_url, s.qdrant_collection, s.embedding_dim, s.qdrant_api_key),
        llm=llm,
        router=ModelRouter(s.small_model, s.large_model, s.complexity_threshold),
        input_guard=InputGuard(s.max_question_chars),
        output_guard=OutputGuard(s.max_answer_chars, s.redact_pii),
        verifier=PolicyVerifier(llm, s.small_model),
        page_service=PageContextService(embeddings, s.page_full_context_tokens, s.page_top_k),
    )
