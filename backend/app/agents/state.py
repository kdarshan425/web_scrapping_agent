"""The shared 'notebook' that every LangGraph node reads from and writes to."""
from typing import TypedDict


class AgentState(TypedDict, total=False):
    # ---- input ----
    question: str
    page_url: str
    page_title: str
    page_text: str
    history: list[dict]          # [{"role": "user"|"assistant", "content": "..."}]

    # ---- working data ----
    page_hash: str
    cache_key: str
    page_context: str            # the small, relevant slice of the page
    policy_chunks: list[dict]    # [{"filename", "text", "score"}]

    # ---- routing ----
    tier: str                    # "small" | "large" | "cache" | "none"
    model_used: str
    attempt: int                 # 0 = first try, 1 = escalated retry

    # ---- output ----
    answer: str
    cached: bool
    blocked: bool
    guard_ok: bool
    needs_escalation: bool
    flags: list[str]
    tokens_in: int
    tokens_out: int
