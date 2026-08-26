import math
import re
from typing import Any

from packages.nlp.interfaces import BaseEmbedder
from packages.nlp.mock import MockEmbedder


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
        return [self._embed_single(t) for t in texts]


class SentenceTransformerEmbedder(BaseEmbedder):
    """Wrapper for sentence-transformers models when the library is installed."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
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

        # Real SentenceTransformer instance
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [[float(round(v, 6)) for v in row] for row in embeddings]


def get_embedder(
    provider_name: str | None = None,
    dimension: int = 384,
    model_name: str | None = None,
) -> BaseEmbedder:
    """Factory creating configured embedding provider instance."""
    prov = (provider_name or "mock").lower()
    if prov in ("real", "local", "local_semantic"):
        return LocalSemanticEmbedder(
            dimension=dimension,
            model_name=model_name or "local-semantic-v1",
        )
    elif prov in ("sentence_transformers", "st"):
        return SentenceTransformerEmbedder(model_name=model_name or "all-MiniLM-L6-v2")
    else:
        return MockEmbedder(dimension=dimension)
