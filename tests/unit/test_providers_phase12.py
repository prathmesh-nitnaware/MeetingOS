import pytest
from packages.common.models import EvidenceItem
from packages.providers.embeddings import OpenAICompatibleEmbedder
from packages.providers.reasoning import OpenAICompatibleReasoner
from packages.providers.usage import UsageTracker


@pytest.mark.asyncio
async def test_openai_embedder_caching_and_fallback():
    # Embedder with unconfigured API key falls back to LocalSemanticEmbedder
    embedder = OpenAICompatibleEmbedder(api_key=None, dimension=384)
    texts = ["First test sentence", "Second test sentence", "First test sentence"]
    vecs = await embedder.embed(texts)

    assert len(vecs) == 3
    assert len(vecs[0]) == 384
    # Identical texts must produce identical cached embeddings
    assert vecs[0] == vecs[2]


@pytest.mark.asyncio
async def test_openai_reasoner_fallback_on_unconfigured():
    # Reasoner with unconfigured key falls back smoothly to LocalEvidenceReasoner
    reasoner = OpenAICompatibleReasoner(api_key=None)
    evidence = [
        EvidenceItem(
            meeting_id="m1",
            segment_id="s1",
            start_time=0.0,
            end_time=10.0,
            text_snapshot="Priya Sharma delivered the database schema on August 29th.",
        )
    ]
    res = await reasoner.reason("When was the schema delivered?", evidence)
    assert res.confidence > 0.0
    assert len(res.evidence) == 1
    assert "Priya Sharma" in res.answer or "August 29th" in res.answer


@pytest.mark.asyncio
async def test_openai_reasoner_empty_evidence_gate():
    reasoner = OpenAICompatibleReasoner(api_key=None)
    res = await reasoner.reason("What is our quantum compute budget?", [])
    assert res.confidence == 0.0
    assert "does not establish an answer" in res.answer.lower()
    assert len(res.evidence) == 0


def test_usage_tracker_cost_and_metrics():
    tracker = UsageTracker()
    tracker.record_usage(
        provider_name="openai",
        model_name="gpt-4o-mini",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=120.0,
    )
    tracker.record_usage(
        provider_name="local",
        model_name="local-semantic-v1",
        prompt_tokens=200,
        completion_tokens=0,
        latency_ms=15.0,
    )

    summary = tracker.get_summary()
    assert summary.total_requests == 2
    assert summary.total_tokens == 1700
    assert summary.total_cost_usd > 0.0
    assert summary.avg_latency_ms > 0.0


def test_latency_percentiles_include_slow_outliers():
    tracker = UsageTracker()
    for latency in (1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 140.0):
        tracker.record_usage("local", "local", latency_ms=latency)

    summary = tracker.get_summary()
    assert summary.p50_latency_ms == 2.0
    # A single slow request must show up in the tail, not only in the average
    assert summary.p99_latency_ms >= summary.p95_latency_ms >= summary.avg_latency_ms
    assert summary.p99_latency_ms > 130.0


def test_cost_uses_the_most_specific_model_price():
    tracker = UsageTracker()
    mini = tracker.estimate_cost("gpt-4o-mini-2024-07-18", 1_000_000, 0)
    full = tracker.estimate_cost("gpt-4o-2024-08-06", 1_000_000, 0)
    assert mini == 0.15
    assert full == 2.50
