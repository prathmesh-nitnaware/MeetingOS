from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from packages.common.models import SpeakerInfo, TranscriptSegment


class BaseASR(ABC):
    """Abstract provider interface for Speech-to-Text Automatic Speech Recognition."""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path | str,
        language: str = "en",
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        """Transcribe an audio file into timestamped transcript segments."""
        ...


class BaseDiarizer(ABC):
    """Abstract provider interface for Speaker Diarization."""

    @abstractmethod
    async def diarize(
        self,
        audio_path: Path | str,
        num_speakers: int | None = None,
        **kwargs: Any,
    ) -> list[SpeakerInfo]:
        """Diarize an audio file and return identified speaker turns or profiles."""
        ...
