"""Prints the model IDs your LLM key can actually use. Run:  python list_models.py"""
import asyncio
import sys

from openai import AsyncOpenAI

from app.core.config import get_settings


async def main() -> None:
    s = get_settings()
    print("Provider URL :", s.llm_base_url)
    print("SMALL_MODEL  :", s.small_model)
    print("LARGE_MODEL  :", s.large_model, "\n")
    client = AsyncOpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key or "none")
    try:
        models = await client.models.list()
    except Exception as exc:  # noqa: BLE001
        print("Could not list models:", exc)
        return
    ids = sorted(m.id for m in models.data)
    for mid in ids:
        mark = "  <-- in use" if mid in (s.small_model, s.large_model) else ""
        print(" ", mid, mark)
    for name, mid in (("SMALL_MODEL", s.small_model), ("LARGE_MODEL", s.large_model)):
        if mid not in ids:
            print(f"\nWARNING: {name}={mid} is NOT available to your key. Pick an ID from the list above.")
    await client.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
