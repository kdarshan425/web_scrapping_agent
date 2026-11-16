"""The LangGraph workflow. Read it top to bottom - it IS the request lifecycle:

 input_guard -> cache_lookup -> retrieve -> route -> generate -> output_guard -> finalize
      |              |                                              |
   (blocked)      (cache hit)                          (small model failed? -> back to route as LARGE)
      +--------------+--> END
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.core.utils import sha256
from app.services.cache_service import CacheService
from app.services.prompts import SAFE_FALLBACK, build_messages

log = logging.getLogger(__name__)


class ChatAgent:
    def __init__(self, container, cache: CacheService, get_policy_version: Callable[[], Awaitable[str]]):
        self.c = container                  # shared singletons (LLM, guards, router...)
        self.s = container.settings
        self.cache = cache                  # per-request cache service
        self.get_policy_version = get_policy_version
        self.graph = self._build()

    async def run(self, state: AgentState) -> AgentState:
        return await self.graph.ainvoke(state)

    # ------------------------------------------------------------------ graph wiring
    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("input_guard", self.input_guard)
        g.add_node("cache_lookup", self.cache_lookup)
        g.add_node("retrieve", self.retrieve)
        g.add_node("route", self.route)
        g.add_node("generate", self.generate)
        g.add_node("output_guard", self.output_guard)
        g.add_node("finalize", self.finalize)

        g.set_entry_point("input_guard")
        g.add_conditional_edges("input_guard", lambda s: "end" if s.get("blocked") else "next",
                                {"end": END, "next": "cache_lookup"})
        g.add_conditional_edges("cache_lookup", lambda s: "end" if s.get("cached") else "next",
                                {"end": END, "next": "retrieve"})
        g.add_edge("retrieve", "route")
        g.add_edge("route", "generate")
        g.add_edge("generate", "output_guard")
        g.add_conditional_edges("output_guard", lambda s: "retry" if s.get("needs_escalation") else "next",
                                {"retry": "route", "next": "finalize"})
        g.add_edge("finalize", END)
        return g.compile()

    # ------------------------------------------------------------------ nodes
    async def input_guard(self, state: AgentState) -> dict:
        """Block empty / too long / injection questions. Clean injected lines out of the page."""
        check = self.c.input_guard.check(state["question"])
        if not check.ok:
            return {"blocked": True, "answer": check.message, "tier": "none", "model_used": "guardrail",
                    "flags": [f"input_blocked:{check.reason}"], "cached": False}

        page_text, flags = self.c.input_guard.sanitize_page(state.get("page_text", "")[: self.s.max_page_chars])
        return {"page_text": page_text, "page_hash": sha256(page_text), "flags": flags, "attempt": 0,
                "tokens_in": 0, "tokens_out": 0, "blocked": False, "cached": False}

    async def cache_lookup(self, state: AgentState) -> dict:
        """Same question + same page + same policies + same last turn => free answer."""
        history = state.get("history", [])
        last_turn = history[-1]["content"] if history else ""
        key = self.cache.make_key(state["question"], state["page_hash"], await self.get_policy_version(), last_turn)
        hit = await self.cache.get(key)
        if hit:
            log.info("cache hit")
            return {"cached": True, "answer": hit.answer, "model_used": hit.model_used, "tier": "cache",
                    "policy_chunks": hit.sources, "cache_key": key}
        return {"cache_key": key}

    async def retrieve(self, state: AgentState) -> dict:
        """RAG: relevant slice of the page + relevant company-policy excerpts (one embedding, two uses)."""
        query_vec = await self.c.embeddings.embed_query(state["question"])
        page_context, hits = await asyncio.gather(
            self.c.page_service.select(state.get("page_text", ""), state["page_hash"], query_vec),
            self.c.vectors.search(query_vec, self.s.policy_top_k, self.s.policy_min_score),
        )
        policy = [{"filename": h.filename, "text": h.text, "score": round(h.score, 3)} for h in hits]
        return {"page_context": page_context, "policy_chunks": policy}

    async def route(self, state: AgentState) -> dict:
        """Pick small vs large model (forced large on an escalated retry)."""
        decision = self.c.router.decide(
            state["question"], len(state.get("page_context", "")), len(state.get("policy_chunks", [])),
            force_large=state.get("attempt", 0) > 0,
        )
        log.info("route -> %s (score=%s, %s)", decision.tier, decision.score, ", ".join(decision.reasons))
        return {"tier": decision.tier, "model_used": decision.model, "needs_escalation": False}

    async def generate(self, state: AgentState) -> dict:
        messages = build_messages(
            state["question"], state.get("page_title", ""), state.get("page_context", ""),
            state.get("policy_chunks", []), state.get("history", []),
        )
        max_tokens = self.s.small_max_output_tokens if state["tier"] == "small" else self.s.large_max_output_tokens
        res = await self.c.llm.complete(state["model_used"], messages, max_tokens)
        return {"answer": res.text, "tokens_in": state.get("tokens_in", 0) + res.tokens_in,
                "tokens_out": state.get("tokens_out", 0) + res.tokens_out}

    async def output_guard(self, state: AgentState) -> dict:
        """Rule checks, then (optional) policy-consistency check. Escalate once if the small model failed."""
        check = self.c.output_guard.check(state["answer"])
        flags = list(state.get("flags", [])) + check.flags
        ok, escalate = check.ok, check.escalate
        tin, tout = state.get("tokens_in", 0), state.get("tokens_out", 0)

        policy = state.get("policy_chunks", [])
        if ok and policy and self.s.enable_verifier:
            consistent, vin, vout = await self.c.verifier.is_consistent(check.text, policy)
            tin, tout = tin + vin, tout + vout
            if not consistent:
                ok, escalate = False, True
                flags.append("policy_conflict")

        can_retry = state["tier"] == "small" and state.get("attempt", 0) == 0
        if not ok and escalate and can_retry:
            return {"needs_escalation": True, "attempt": 1, "flags": flags, "tokens_in": tin, "tokens_out": tout}

        return {"answer": check.text if ok else SAFE_FALLBACK, "guard_ok": ok, "needs_escalation": False,
                "flags": flags, "tokens_in": tin, "tokens_out": tout}

    async def finalize(self, state: AgentState) -> dict:
        """Store good answers in the cache so the next identical question costs 0 tokens."""
        if state.get("guard_ok"):
            await self.cache.set(state["cache_key"], state["answer"], state["model_used"], state.get("policy_chunks", []))
        return {}
