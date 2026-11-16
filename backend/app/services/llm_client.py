"""Thin wrapper over any OpenAI-compatible endpoint (Groq, Gemini, Ollama, OpenRouter...)."""
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.services.chunking import estimate_tokens


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    model: str


class LLMClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        # max_retries handles transient 429/5xx errors automatically
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed", max_retries=2, timeout=60)

    async def complete(
        self, model: str, messages: list[dict], max_tokens: int, temperature: float = 0.2
    ) -> LLMResult:
        resp = await self._client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=temperature
        )
        text = (resp.choices[0].message.content or "").strip()
        usage = resp.usage
        # Some local providers omit usage -> fall back to an estimate
        tokens_in = usage.prompt_tokens if usage else estimate_tokens(" ".join(m["content"] for m in messages))
        tokens_out = usage.completion_tokens if usage else estimate_tokens(text)
        return LLMResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out, model=model)
