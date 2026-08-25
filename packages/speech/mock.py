from pathlib import Path
from typing import Any

from packages.common.models import SpeakerInfo, TranscriptSegment
from packages.speech.interfaces import BaseASR, BaseDiarizer


class MockASR(BaseASR):
    """Deterministic mock ASR provider for testing without GPU or network access."""

    def __init__(self, predefined_segments: list[TranscriptSegment] | None = None) -> None:
        self.predefined_segments = predefined_segments or [
            TranscriptSegment(
                segment_id="seg-001",
                sequence=0,
                speaker_id="spk_0",
                start_time=0.0,
                end_time=5.5,
                text="Welcome everyone. Today we are deciding on the database architecture for MeetingOS.",
            ),
            TranscriptSegment(
                segment_id="seg-002",
                sequence=1,
                speaker_id="spk_1",
                start_time=6.0,
                end_time=12.2,
                text="Rahul and I evaluated MongoDB and PostgreSQL. We propose adopting PostgreSQL with pgvector.",
            ),
            TranscriptSegment(
                segment_id="seg-003",
                sequence=2,
                speaker_id="spk_0",
                start_time=13.0,
                end_time=18.0,
                text="Agreed. Let's make PostgreSQL the official choice. Rahul, please finish the schema by Friday.",
            ),
        ]

    async def transcribe(
        self,
        audio_path: Path | str,
        language: str = "en",
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        _ = (audio_path, language, kwargs)
        return list(self.predefined_segments)


class MockDiarizer(BaseDiarizer):
    """Deterministic mock speaker diarization provider."""

    def __init__(self, predefined_speakers: list[SpeakerInfo] | None = None) -> None:
        self.predefined_speakers = predefined_speakers or [
            SpeakerInfo(speaker_id="spk_0", name="Priya Sharma"),
            SpeakerInfo(speaker_id="spk_1", name="Rahul Verma"),
        ]

    async def diarize(
        self,
        audio_path: Path | str,
        num_speakers: int | None = None,
        **kwargs: Any,
    ) -> list[SpeakerInfo]:
        _ = (audio_path, num_speakers, kwargs)
        return list(self.predefined_speakers)
