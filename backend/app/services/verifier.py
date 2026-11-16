"""Optional policy-consistency check. Uses the SMALL model and answers with ONE word
(~5 output tokens), so it is cheap. It only runs when policy excerpts were used."""
import logging

from app.services.llm_client import LLMClient
from app.services.prompts import VERIFIER_PROMPT

log = logging.getLogger(__name__)


class PolicyVerifier:
    def __init__(self, llm: LLMClient, model: str) -> None:
        self.llm = llm
        self.model = model

    async def is_consistent(self, answer: str, policy_chunks: list[dict]) -> tuple[bool, int, int]:
        """Returns (consistent?, tokens_in, tokens_out). Fails OPEN on provider errors."""
        policy = "\n".join(c["text"] for c in policy_chunks)
        messages = [
            {"role": "system", "content": VERIFIER_PROMPT},
            {"role": "user", "content": f"COMPANY POLICY:\n{policy}\n\nANSWER:\n{answer}"},
        ]
        try:
            res = await self.llm.complete(self.model, messages, max_tokens=5, temperature=0)
        except Exception as exc:  # noqa: BLE001
            log.warning("Verifier failed, skipping: %s", exc)
            return True, 0, 0
        return "CONTRADICTED" not in res.text.upper(), res.tokens_in, res.tokens_out
