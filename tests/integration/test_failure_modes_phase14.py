from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.ingestion.pipeline import IngestionPipeline
from packages.providers.anthropic import AnthropicReasoner
from packages.providers.gemini import GeminiReasoner
from packages.speech.mock import MockASR, MockDiarizer


@pytest.fixture
def dummy_evidence():
    return [
        EvidenceItem(
            meeting_id="meet-fail-001",
            segment_id="seg-fail-001",
            start_time=0.0,
            end_time=10.0,
            text_snapshot="Decision made.",
            source_type=SourceType.AUDIO_WAV,
        )
    ]


@pytest.mark.asyncio
async def test_ingestion_missing_file_raises_error():
    pipeline = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())
    non_existent = Path("data/uploads/non_existent_file.wav")
    with pytest.raises(FileNotFoundError):
        await pipeline.process_file(non_existent, source_type=SourceType.AUDIO_WAV)


@pytest.mark.asyncio
async def test_anthropic_provider_timeout_fallback(dummy_evidence):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Anthropic API Timeout")

        reasoner = AnthropicReasoner(
            api_key="test-key",
            base_url="https://api.anthropic.com/v1",
            max_retries=1,
        )
        res = await reasoner.reason("Question?", dummy_evidence)
        # Should gracefully fall back without unhandled exception
        assert res.answer is not None
        assert len(res.evidence) >= 1


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_fallback(dummy_evidence):
    mock_resp = httpx.Response(429, json={"error": {"message": "Resource exhausted"}})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        reasoner = GeminiReasoner(
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com",
            max_retries=1,
        )
        res = await reasoner.reason("Question?", dummy_evidence)
        # Should gracefully fall back to local evidence reasoner
        assert res.answer is not None
        assert len(res.evidence) >= 1
