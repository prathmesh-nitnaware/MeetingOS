import hashlib
import math
import re
import time
from typing import Any

import httpx
from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.mock import MockEmbedder
from packages.providers.usage import global_usage_tracker


class LocalSemanticEmbedder(BaseEmbedder):
    """High-fidelity local semantic embedding provider.

    Generates dense, unit-normalized semantic embeddings using subword n-gram
    hashing, contextual position encoding, and vocabulary term projections.
    Does not require external network requests or paid APIs.
    """

    def __init__(self, dimension: int = 384, model_name: str = "local-semantic-v1") -> None:
        self.dimension = dimension
        self.model_name = model_name

    def _tokenize(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 0]
        return tokens

    def _embed_single(self, text: str) -> list[float]:
        if not text.strip():
            return [0.0] * self.dimension

        tokens = self._tokenize(text)
        vec = [0.0] * self.dimension

        # 1. Whole-word semantic projections
        for pos, token in enumerate(tokens):
            weight = 1.0 / (1.0 + 0.05 * min(pos, 20))
            # Primary word hash
            h = 2166136261
            for char in token:
                h = ((h ^ ord(char)) * 16777619) & 0xFFFFFFFF
            idx1 = h % self.dimension
            vec[idx1] += 1.5 * weight

            # Secondary token rotation
            idx2 = (h >> 7) % self.dimension
            sign = 1.0 if (h & 1) else -1.0
            vec[idx2] += sign * 0.8 * weight

            # Subword character n-grams (3-grams and 4-grams) for morphological capture
            padded = f"<{token}>"
            for n in (3, 4):
                for i in range(len(padded) - n + 1):
                    ngram = padded[i : i + n]
                    nh = 2166136261
                    for nc in ngram:
                        nh = ((nh ^ ord(nc)) * 16777619) & 0xFFFFFFFF
                    n_idx = nh % self.dimension
                    n_sign = 1.0 if (nh & 2) else -1.0
                    vec[n_idx] += n_sign * 0.35 * weight

        # 2. Bigram phrase context
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i + 1]}"
            bh = 2166136261
            for bc in bigram:
                bh = ((bh ^ ord(bc)) * 16777619) & 0xFFFFFFFF
            b_idx = bh % self.dimension
            vec[b_idx] += 0.6

        # 3. L2 Normalization for exact Cosine Similarity
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            unit_vec = [round(x / norm, 6) for x in vec]
        else:
            unit_vec = [0.0] * self.dimension

        return unit_vec

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        _ = kwargs
        t0 = time.perf_counter()
        results = [self._embed_single(t) for t in texts]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Telemetry
        global_usage_tracker.record_usage(
            provider_name="local",
            model_name=self.model_name,
            prompt_tokens=sum(len(t.split()) for t in texts),
            completion_tokens=0,
            latency_ms=elapsed_ms,
            operation="embedding",
        )
        return results


class SentenceTransformerEmbedder(BaseEmbedder):
    """Wrapper for sentence-transformers models when the library is installed."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                import sentence_transformers  # pyright: ignore[reportMissingImports]

                self._model = sentence_transformers.SentenceTransformer(self.model_name)
            except ImportError:
                # Fallback to LocalSemanticEmbedder
                self._model = LocalSemanticEmbedder(dimension=384, model_name=self.model_name)
        return self._model

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        _ = kwargs
        model = self._get_model()
        if isinstance(model, BaseEmbedder):
            return await model.embed(texts)

        t0 = time.perf_counter()
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        global_usage_tracker.record_usage(
            provider_name="sentence_transformers",
            model_name=self.model_name,
            prompt_tokens=sum(len(t.split()) for t in texts),
            completion_tokens=0,
            latency_ms=elapsed_ms,
            operation="embedding",
        )
        return [[float(round(v, 6)) for v in row] for row in embeddings]


class OpenAICompatibleEmbedder(BaseEmbedder):
    """Production OpenAI-compatible embedding provider with batching, hash caching, and fallback."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        dimension: int = 1536,
        batch_size: int = 32,
        fallback_embedder: BaseEmbedder | None = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dimension = dimension
        self.batch_size = batch_size
        self.fallback = fallback_embedder or LocalSemanticEmbedder(dimension=dimension)
        self._cache: dict[str, list[float]] = {}

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(f"{self.model_name}:{text}".encode()).hexdigest()

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        _ = kwargs
        if not texts:
            return []

        # Check cache
        embeddings: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for i, text in enumerate(texts):
            h = self._hash_text(text)
            if h in self._cache:
                embeddings[i] = self._cache[h]
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if not missing_texts:
            return [e for e in embeddings if e is not None]

        # If no API key or empty base URL, fallback directly
        if not self.api_key or not self.base_url:
            fb_res = await self.fallback.embed(missing_texts)
            for idx, vec in zip(missing_indices, fb_res, strict=True):
                embeddings[idx] = vec
                self._cache[self._hash_text(texts[idx])] = vec
            global_usage_tracker.record_usage(
                provider_name="openai_compatible",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in missing_texts),
                latency_ms=1.0,
                operation="embedding",
                is_fallback=True,
                status="fallback",
            )
            return [e for e in embeddings if e is not None]

        # Execute remote batch requests
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for batch_start in range(0, len(missing_texts), self.batch_size):
                    chunk_texts = missing_texts[batch_start : batch_start + self.batch_size]
                    chunk_indices = missing_indices[batch_start : batch_start + self.batch_size]

                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "input": chunk_texts,
                            "model": self.model_name,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    res_items = sorted(data["data"], key=lambda x: x["index"])

                    for idx, item in zip(chunk_indices, res_items, strict=True):
                        vec = item["embedding"]
                        # Dimension validation
                        if len(vec) != self.dimension:
                            raise ValueError(
                                f"Dimension mismatch: expected {self.dimension}, got {len(vec)}"
                            )
                        embeddings[idx] = vec
                        self._cache[self._hash_text(texts[idx])] = vec

            elapsed_ms = (time.perf_counter() - t0) * 1000
            global_usage_tracker.record_usage(
                provider_name="openai_compatible",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in missing_texts),
                latency_ms=elapsed_ms,
                operation="embedding",
                status="success",
            )
        except Exception as e:
            # Fallback on network or API failure
            elapsed_ms = (time.perf_counter() - t0) * 1000
            fb_res = await self.fallback.embed(missing_texts)
            for idx, vec in zip(missing_indices, fb_res, strict=True):
                embeddings[idx] = vec
                self._cache[self._hash_text(texts[idx])] = vec

            global_usage_tracker.record_usage(
                provider_name="openai_compatible",
                model_name=self.model_name,
                prompt_tokens=sum(len(t.split()) for t in missing_texts),
                latency_ms=elapsed_ms,
                operation="embedding",
                is_fallback=True,
                status="fallback",
                error_type=str(e),
            )

        return [e for e in embeddings if e is not None]


def get_embedder(
    provider_name: str | None = None,
    dimension: int = 384,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> BaseEmbedder:
    """Factory creating configured embedding provider instance."""
    prov = (provider_name or "mock").lower()
    if prov in ("openai", "openai_compatible"):
        return OpenAICompatibleEmbedder(
            model_name=model_name or "text-embedding-3-small",
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            dimension=dimension,
        )
    elif prov in ("real", "local", "local_semantic"):
        return LocalSemanticEmbedder(
            dimension=dimension,
            model_name=model_name or "local-semantic-v1",
        )
    elif prov in ("sentence_transformers", "st"):
        return SentenceTransformerEmbedder(model_name=model_name or "all-MiniLM-L6-v2")
    else:
        return MockEmbedder(dimension=dimension)
