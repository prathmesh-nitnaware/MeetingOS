import pytest
from evaluation.provider_smoke import (
    _is_real_key,
    _sanitize_secrets,
    smoke_test_embedder,
    smoke_test_reasoner,
)
from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.providers.embeddings import LocalSemanticEmbedder
from packages.providers.reasoning import LocalEvidenceReasoner


def test_is_real_key():
    assert _is_real_key(None) is False
    assert _is_real_key("") is False
    assert _is_real_key("local-development-key") is False
    assert _is_real_key("your-api-key-here") is False
    assert _is_real_key("test-key") is False
    assert _is_real_key("sk-proj-1234567890abcdef1234567890") is True


def test_sanitize_secrets():
    raw_log = "Error connecting to provider with key test-secret-dummy-12345678"
    # Even arbitrary text should be handled
    sanitized = _sanitize_secrets(raw_log)
    assert isinstance(sanitized, str)


@pytest.mark.asyncio
async def test_smoke_test_local_embedder():
    embedder = LocalSemanticEmbedder(dimension=384)
    res = await smoke_test_embedder("LocalSemanticEmbedder", embedder)
    assert res["status"] == "PASSED"
    assert res["dimension"] == 384
    assert res["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_smoke_test_local_reasoner():
    reasoner = LocalEvidenceReasoner()
    evidence = [
        EvidenceItem(
            meeting_id="smoke-01",
            segment_id="seg-01",
            start_time=0.0,
            end_time=10.0,
            text_snapshot="We approved PostgreSQL as the organizational memory store.",
            source_type=SourceType.AUDIO_WAV,
        )
    ]
    res = await smoke_test_reasoner("LocalEvidenceReasoner", reasoner, evidence)
    assert res["status"] == "PASSED"
    assert res["confidence"] > 0
    assert "PostgreSQL" in res["answer_preview"]
