"""Local, free embeddings using fastembed (ONNX, CPU).

This service creates vector representations for text without sending requests to
an external API or paying per-token costs. It uses a local ONNX model, which
keeps the setup self-contained and makes the app suitable for offline or
low-cost deployments.
"""

import asyncio


class EmbeddingService:
    """Thin wrapper around a local fastembed text embedding model.

    The class stores the configuration for a chosen model, loads it only when
    needed, and exposes both sync and async methods. This lets the rest of the
    app use a simple API while keeping CPU-heavy embedding work off the event
    loop.
    """

    def __init__(self, model_name: str, cache_dir: str) -> None:
        # Name of the pretrained embedding model to use, such as a sentence or
        # multilingual model supported by fastembed.
        self.model_name = model_name

        # Local folder used to cache downloaded model artifacts so they are not
        # re-downloaded every time the app starts.
        self.cache_dir = cache_dir

        # The model is loaded lazily so imports and tests stay fast and do not
        # pay the startup cost until the first real embedding request.
        self._model = None

    def _load(self):
        # Keep a single shared model instance for all calls. Reusing the same
        # model avoids repeated startup work and reduces latency.
        if self._model is None:
            # Import inside the method so the dependency is only required when
            # embeddings are actually used.
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)
        return self._model

    def _embed_docs(self, texts: list[str]) -> list[list[float]]:
        # fastembed returns embedding objects for each input string. Converting
        # them to Python lists makes the data easier to serialize, store, and
        # compare in downstream code.
        return [v.tolist() for v in self._load().embed(texts)]

    def _embed_query(self, text: str) -> list[float]:
        # query_embed yields one or more vectors, and for a single query we take
        # the first value and convert it to a plain list of floats.
        return next(iter(self._load().query_embed(text))).tolist()

    # CPU-heavy embedding work can take a noticeable amount of time, so the
    # async wrappers run the synchronous logic in a thread pool. This keeps the
    # API responsive without changing the underlying model code.
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed_docs, texts)

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_query, text)

    async def warm_up(self) -> None:
        # Prime the model on the first request to reduce the "cold start" delay
        # when the app receives its next real embedding task.
        await self.embed_query("warm up")
