import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.providers.anthropic import AnthropicReasoner
from packages.providers.gemini import GeminiEmbedder, GeminiReasoner
from packages.providers.registry import ProviderCapabilityRegistry


@pytest.fixture
def sample_evidence():
    return [
        EvidenceItem(
            meeting_id="meet-001",
            segment_id="seg-001",
            start_time=10.0,
            end_time=20.0,
            text_snapshot="We decided to adopt PostgreSQL with pgvector for the memory layer.",
            source_type=SourceType.AUDIO_WAV,
        )
    ]


@pytest.mark.asyncio
async def test_anthropic_reasoner_success(sample_evidence):
    mock_payload = {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "answer": "PostgreSQL with pgvector was officially adopted.",
                        "confidence": 0.95,
                        "citations": ["seg-001"],
                        "reasoning_summary": "Direct factual extraction from meeting decision.",
                        "insufficient_evidence": False,
                    }
                ),
            }
        ],
        "usage": {"input_tokens": 120, "output_tokens": 45},
    }

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    mock_resp = httpx.Response(200, json=mock_payload, request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        reasoner = AnthropicReasoner(
            api_key="test-anthropic-key",
            base_url="https://api.anthropic.com/v1",
            max_retries=1,
        )
        res = await reasoner.reason("What database was chosen?", sample_evidence)

        assert "PostgreSQL" in res.answer
        assert res.confidence == 0.95
        assert len(res.evidence) == 1
        assert mock_post.called


@pytest.mark.asyncio
async def test_anthropic_reasoner_fallback_on_unconfigured(sample_evidence):
    reasoner = AnthropicReasoner(api_key=None)
    res = await reasoner.reason("What database was chosen?", sample_evidence)
    assert res.answer is not None
    assert len(res.evidence) >= 1


@pytest.mark.asyncio
async def test_gemini_reasoner_success(sample_evidence):
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "answer": "PostgreSQL with pgvector was adopted.",
                                    "confidence": 0.98,
                                    "citations": ["seg-001"],
                                    "reasoning_summary": "Extracted from decision segment.",
                                    "insufficient_evidence": False,
                                }
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 110, "candidatesTokenCount": 35},
    }

    req = httpx.Request(
        "POST",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    )
    mock_resp = httpx.Response(200, json=mock_payload, request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        reasoner = GeminiReasoner(
            api_key="test-gemini-key",
            base_url="https://generativelanguage.googleapis.com",
            max_retries=1,
        )
        res = await reasoner.reason("What database was chosen?", sample_evidence)

        assert "PostgreSQL" in res.answer
        assert res.confidence == 0.98
        assert mock_post.called


@pytest.mark.asyncio
async def test_gemini_embedder_caching():
    mock_payload = {
        "embeddings": [
            {"values": [0.1] * 768},
            {"values": [0.2] * 768},
        ]
    }
    req = httpx.Request(
        "POST",
        "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents",
    )
    mock_resp = httpx.Response(200, json=mock_payload, request=req)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        embedder = GeminiEmbedder(
            api_key="test-gemini-key",
            base_url="https://generativelanguage.googleapis.com",
            dimension=768,
        )
        texts = ["First meeting sentence", "Second meeting sentence"]
        vecs1 = await embedder.embed(texts)
        assert len(vecs1) == 2
        assert len(vecs1[0]) == 768
        assert mock_post.call_count == 1

        # Second invocation should hit cache without additional HTTP post
        vecs2 = await embedder.embed(texts)
        assert len(vecs2) == 2
        assert mock_post.call_count == 1  # No additional remote call


def test_provider_capability_registry():
    summary = ProviderCapabilityRegistry.get_registered_capabilities(
        openai_key_present=True,
        anthropic_key_present=True,
        gemini_key_present=False,
        active_reasoner="anthropic",
        active_embedder="openai",
    )
    assert summary.active_reasoner == "anthropic"
    assert summary.active_embedder == "openai"
    assert len(summary.providers) == 6

    names = {p.name for p in summary.providers}
    assert "mock" in names
    assert "local" in names
    assert "anthropic" in names
    assert "gemini" in names
    assert "openai" in names
