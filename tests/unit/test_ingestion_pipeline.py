from pathlib import Path

import pytest
from packages.common.enums import SourceType
from packages.ingestion.pipeline import IngestionPipeline
from packages.speech.mock import MockASR, MockDiarizer


@pytest.mark.asyncio
async def test_ingestion_pipeline_with_audio(tmp_path: Path):
    audio_file = tmp_path / "meeting.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 1000)

    pipeline = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())
    segments, speakers, duration = await pipeline.process_file(
        audio_file, source_type=SourceType.AUDIO_WAV
    )

    assert len(segments) == 3
    assert len(speakers) == 2
    assert duration == 18.0
    assert segments[0].speaker_id == "spk_0"


@pytest.mark.asyncio
async def test_ingestion_pipeline_with_srt(tmp_path: Path):
    srt_file = tmp_path / "meeting.srt"
    srt_content = """1
00:00:00,000 --> 00:00:05,000
Alice: Welcome to the project sync.

2
00:00:05,500 --> 00:00:10,000
Bob: Let us review the action items.
"""
    srt_file.write_text(srt_content, encoding="utf-8")

    pipeline = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())
    segments, speakers, duration = await pipeline.process_file(
        srt_file, source_type=SourceType.SRT_SUBTITLE
    )

    assert len(segments) == 2
    assert len(speakers) == 2
    assert duration == 10.0


@pytest.mark.asyncio
async def test_ingestion_pipeline_with_text(tmp_path: Path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("Alice: First point.\nBob: Second point.\n", encoding="utf-8")

    pipeline = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())
    segments, speakers, duration = await pipeline.process_file(
        text_file, source_type=SourceType.TEXT_TRANSCRIPT
    )

    assert len(segments) == 2
    assert len(speakers) == 2
    assert duration > 0.0


@pytest.mark.asyncio
async def test_ingestion_pipeline_nonexistent_file(tmp_path: Path):
    missing_file = tmp_path / "missing.wav"
    pipeline = IngestionPipeline(asr_provider=MockASR(), diarizer_provider=MockDiarizer())

    with pytest.raises(FileNotFoundError):
        await pipeline.process_file(missing_file)
