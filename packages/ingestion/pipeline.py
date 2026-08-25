import logging
from pathlib import Path

from packages.common.enums import SourceType
from packages.common.models import SpeakerInfo, TranscriptSegment
from packages.ingestion.normalizer import (
    merge_speech_results,
    normalize_plain_text,
    normalize_srt_content,
)
from packages.ingestion.validator import inspect_media_file, validate_file_extension
from packages.speech.interfaces import BaseASR, BaseDiarizer

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates ingestion, speech transcription, diarization, and CMF normalization."""

    def __init__(
        self,
        asr_provider: BaseASR,
        diarizer_provider: BaseDiarizer,
    ) -> None:
        self.asr = asr_provider
        self.diarizer = diarizer_provider

    async def process_file(
        self,
        file_path: Path,
        source_type: SourceType | None = None,
    ) -> tuple[list[TranscriptSegment], list[SpeakerInfo], float]:
        """Process an uploaded media or text file into CMF segments and speaker metadata.

        Returns:
            tuple of (segments, speakers, duration_seconds)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found at path: {file_path}")

        detected_type = source_type or validate_file_extension(file_path.name)
        logger.info("Processing file %s as %s", file_path.name, detected_type)

        if detected_type == SourceType.SRT_SUBTITLE:
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            segments, speakers = normalize_srt_content(content)

        elif detected_type == SourceType.TEXT_TRANSCRIPT:
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            segments, speakers = normalize_plain_text(content)

        else:
            # Audio or Video processing via ASR and Diarization providers
            _ = inspect_media_file(file_path)
            raw_segments = await self.asr.transcribe(file_path)
            raw_speakers = await self.diarizer.diarize(file_path)
            segments, speakers = merge_speech_results(raw_segments, raw_speakers)

        duration = max((s.end_time for s in segments), default=0.0)
        logger.info(
            "Processed %d segments, %d speakers. Total duration: %.2fs",
            len(segments),
            len(speakers),
            duration,
        )
        return segments, speakers, duration
