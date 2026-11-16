"""Central configuration. Every value can be overridden from the .env file / environment."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App / security ---
    app_name: str = "Page Chat Assistant"
    api_key: str = "ak_live_7x9Qz2mK8vP4wL1fR6tY3hB5nJ0dC9sX2gH8kF4mQ1wZ6yT3"  # extension must send this in the X-API-Key header
    # Browser extensions call us from chrome-extension:// / safari-web-extension:// origins
    cors_origin_regex: str = r"(chrome|moz|safari-web)-extension://.*|http://localhost(:\d+)?"

    # --- Infra ---
    # database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pagechat"db.tspfaxkyrwwdbqsnbtih.supabase.co
    # database_url: str = "postgresql+asyncpg://postgres:Bhalchandravihar@102@db.tspfaxkyrwwdbqsnbtih.supabase.co:5432/postgres?ssl=require"
    database_url: str = "postgresql+asyncpg://postgres:Bhalchandravihar%40102@db.tspfaxkyrwwdbqsnbtih.supabase.co:5432/postgres?ssl=require"
    # qdrant_url: str = "http://localhost:6333"
    qdrant_url: str = "https://99a8c1ce-8a91-42aa-b24d-317062b06eb4.sa-east-1-0.aws.cloud.qdrant.io:6333"
    qdrant_api_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6ODc3MmRlY2UtMDU0MC00MjMxLWE5MWMtYjU4MzIzMTIxZDQwIn0.vN9ferHzn9gMW6Ohs-tOulKYdRil7M84jRFmF--JkP4"
    qdrant_collection: str = "company_policies"
    

    # --- LLM (any OpenAI-compatible provider; default = Groq free tier) ---
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = "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"
    small_model: str = "llama-3.1-8b-instant"
    large_model: str = "llama-3.3-70b-versatile"
    small_max_output_tokens: int = 400
    large_max_output_tokens: int = 800

    # --- Embeddings (local, free, CPU only) ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_cache_dir: str = ".models"

    # --- Token optimisation ---
    cache_ttl_seconds: int = 86_400          # reuse identical answers for 24h
    max_page_chars: int = 120_000            # hard cap on page text we process
    page_full_context_tokens: int = 1_500    # pages smaller than this are sent whole
    page_top_k: int = 4                      # otherwise only top-K relevant chunks are sent
    policy_top_k: int = 3
    policy_min_score: float = 0.45           # ignore weak policy matches
    history_turns: int = 3                   # past Q/A pairs sent to the LLM
    history_message_max_chars: int = 600     # truncate each old message

    # --- Model routing ---
    complexity_threshold: int = 3            # score >= threshold -> large model

    # --- Guardrails ---
    max_question_chars: int = 2_000
    max_answer_chars: int = 4_000
    redact_pii: bool = True
    enable_verifier: bool = True             # small-model policy-consistency check


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed only once."""
    return Settings()
