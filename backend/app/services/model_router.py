"""Automatic model switching. Pure Python heuristics => the routing decision costs ZERO tokens.

Score the question; low score -> small cheap model, high score -> large model.
(If the small model's answer fails a guardrail, the agent escalates to the large model.)
"""
import re
from dataclasses import dataclass, field

# Words that usually mean "needs reasoning / long output"
_COMPLEX_WORDS = re.compile(
    r"\b(analy[sz]e|compare|comparison|difference|evaluate|pros and cons|step[- ]by[- ]step|"
    r"explain why|why does|summari[sz]e|draft|write|calculate|legal|compliance|audit|"
    r"risk|recommend|strategy|reason|justify|implications?)\b",
    re.IGNORECASE,
)


@dataclass
class RouteDecision:
    tier: str  # "small" | "large"
    model: str
    score: int
    reasons: list[str] = field(default_factory=list)


class ModelRouter:
    def __init__(self, small_model: str, large_model: str, threshold: int) -> None:
        self.small_model = small_model
        self.large_model = large_model
        self.threshold = threshold

    def decide(self, question: str, context_chars: int, policy_chunks: int, force_large: bool = False) -> RouteDecision:
        if force_large:
            return RouteDecision("large", self.large_model, 99, ["escalated after guardrail failure"])

        score, reasons = 0, []
        if len(question.split()) > 40:
            score += 2
            reasons.append("long question")
        if _COMPLEX_WORDS.search(question):
            score += 2
            reasons.append("reasoning keywords")
        if question.count("?") > 1:
            score += 1
            reasons.append("multiple questions")
        if policy_chunks >= 3:
            score += 1
            reasons.append("many policy excerpts")
        if context_chars // 4 > 2500:  # ~tokens
            score += 1
            reasons.append("large context")

        if score >= self.threshold:
            return RouteDecision("large", self.large_model, score, reasons)
        return RouteDecision("small", self.small_model, score, reasons or ["simple query"])
