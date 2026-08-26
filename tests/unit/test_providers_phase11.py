import math

import pytest
from packages.common.models import EvidenceItem
from packages.nlp.mock import MockEmbedder
from packages.providers.embeddings import LocalSemanticEmbedder, get_embedder
from packages.providers.reasoning import LocalEvidenceReasoner, get_reasoner
from packages.reasoning.mock import MockReasoner


def cosine_sim(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0


@pytest.mark.asyncio
async def test_local_embedder_dimension():
    embedder = LocalSemanticEmbedder(dimension=384)
    vecs = await embedder.embed(["PostgreSQL database migration"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 384
    # Verify unit length
    norm = math.sqrt(sum(x * x for x in vecs[0]))
    assert abs(norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_local_embedder_deterministic():
    embedder = LocalSemanticEmbedder(dimension=384)
    v1 = await embedder.embed(["Redis connection timeout issue"])
    v2 = await embedder.embed(["Redis connection timeout issue"])
    assert v1 == v2


@pytest.mark.asyncio
async def test_local_embedder_cosine_similarity():
    embedder = LocalSemanticEmbedder(dimension=384)
    texts = [
        "PostgreSQL database with pgvector support",
        "Postgres database with vector search",
        "Recipe for chocolate chip cookies with butter",
    ]
    vecs = await embedder.embed(texts)
    sim_related = cosine_sim(vecs[0], vecs[1])
    sim_unrelated = cosine_sim(vecs[0], vecs[2])
    assert sim_related > sim_unrelated, (
        f"Expected related sim ({sim_related:.3f}) > unrelated sim ({sim_unrelated:.3f})"
    )


@pytest.mark.asyncio
async def test_local_embedder_batch():
    embedder = LocalSemanticEmbedder(dimension=256)
    texts = ["First query", "Second query", "Third query", "Fourth query"]
    vecs = await embedder.embed(texts)
    assert len(vecs) == 4
    for v in vecs:
        assert len(v) == 256


@pytest.mark.asyncio
async def test_local_reasoner_evidence_grounding():
    reasoner = LocalEvidenceReasoner()
    evidence = [
        EvidenceItem(
            meeting_id="m1",
            segment_id="s1",
            start_time=0.0,
            end_time=15.0,
            text_snapshot="Priya Sharma completed the database schema migration on August 29th.",
        )
    ]
    res = await reasoner.reason("When was schema migration completed?", evidence)
    assert res.confidence > 0.0
    assert (
        "Priya Sharma" in res.answer
        or "August 29th" in res.answer
        or "schema migration" in res.answer
    )
    assert len(res.evidence) == 1
    assert len(res.reasoning_path) > 0


@pytest.mark.asyncio
async def test_local_reasoner_insufficient_evidence_gate():
    reasoner = LocalEvidenceReasoner()
    res = await reasoner.reason("What is our quantum computing budget?", [])
    assert res.confidence == 0.0
    assert "does not establish an answer" in res.answer.lower()
    assert len(res.evidence) == 0


def test_provider_factories():
    mock_emb = get_embedder("mock")
    assert isinstance(mock_emb, MockEmbedder)

    real_emb = get_embedder("real")
    assert isinstance(real_emb, LocalSemanticEmbedder)

    local_emb = get_embedder("local")
    assert isinstance(local_emb, LocalSemanticEmbedder)

    mock_reas = get_reasoner("mock")
    assert isinstance(mock_reas, MockReasoner)

    real_reas = get_reasoner("real")
    assert isinstance(real_reas, LocalEvidenceReasoner)
