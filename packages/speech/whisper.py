"""Real speech-to-text using faster-whisper (optional dependency: `uv sync --extra asr`)."""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

from packages.common.models import SpeakerInfo, TranscriptSegment
from packages.speech.interfaces import BaseASR, BaseDiarizer

logger = logging.getLogger(__name__)


class SpeechProviderUnavailableError(RuntimeError):
    """Raised when the configured speech provider cannot be used on this machine."""


class AudioDecodeError(ValueError):
    """Raised when an uploaded file cannot be decoded as audio/video."""


WHISPER_SAMPLE_RATE = 16000


def decode_audio(audio_path: Path, sample_rate: int = WHISPER_SAMPLE_RATE) -> Any:
    """Decode any audio/video file to mono float32 samples with PyAV.

    faster-whisper 1.2.1's own decoder passes ``metadata_errors`` to ``av.open``, which
    newer PyAV releases no longer accept, so decoding happens here instead.
    """
    try:
        import av  # pyright: ignore[reportMissingImports]
        import numpy as np
        from av.error import InvalidDataError  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        raise SpeechProviderUnavailableError(
            "Audio decoding is not installed. Install it with `uv sync --extra asr`."
        ) from exc

    resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
    chunks: list[Any] = []
    try:
        with av.open(str(audio_path), mode="r") as container:
            if not container.streams.audio:
                raise AudioDecodeError("The uploaded file has no audio track.")
            frames = container.decode(audio=0)
            while True:
                try:
                    frame = next(frames)
                except StopIteration:
                    break
                except InvalidDataError:
                    continue  # skip corrupt frames, as faster-whisper does
                for resampled in resampler.resample(frame):
                    chunks.append(resampled.to_ndarray().reshape(-1))
            for resampled in resampler.resample(None):  # flush buffered samples
                chunks.append(resampled.to_ndarray().reshape(-1))
    except AudioDecodeError:
        raise
    except Exception as exc:
        # The decoder's message includes the server-side file path, so it is only logged
        logger.warning("Could not decode %s: %s", audio_path, exc)
        raise AudioDecodeError(
            "The uploaded file could not be read as audio or video. "
            "It may be corrupt or in an unsupported format."
        ) from exc

    if not chunks:
        raise AudioDecodeError("The uploaded file contains no audio.")
    return np.concatenate(chunks).astype(np.float32) / 32768.0


class WhisperASR(BaseASR):
    """faster-whisper (CTranslate2) transcription. Audio is decoded with the bundled PyAV/FFmpeg,
    so WAV, MP3, M4A and MP4 uploads work without a system FFmpeg install.

    The model is downloaded on first use and cached per process.
    """

    _models: dict[tuple[str, str, str], Any] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language

    def _load_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise SpeechProviderUnavailableError(
                "Speech-to-text is not installed. Install it with `uv sync --extra asr` "
                "(or `pip install faster-whisper`), or set ASR_PROVIDER=mock to use canned demo "
                "transcripts. Text (.txt) and subtitle (.srt) uploads work without it."
            ) from exc

        key = (self.model_size, self.device, self.compute_type)
        with self._lock:
            if key not in self._models:
                logger.info(
                    "Loading faster-whisper model '%s' on %s (%s)...",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                self._models[key] = WhisperModel(
                    self.model_size, device=self.device, compute_type=self.compute_type
                )
            return self._models[key]

    def _transcribe_sync(self, audio_path: Path, language: str | None) -> list[TranscriptSegment]:
        model = self._load_model()
        audio = decode_audio(audio_path)
        segments_iter, info = model.transcribe(
            audio, language=language, vad_filter=True, beam_size=5
        )
        segments: list[TranscriptSegment] = []
        for seg in segments_iter:
            text = seg.text.strip()
            if not text:
                continue
            start = max(0.0, round(float(seg.start), 2))
            end = max(start, round(float(seg.end), 2))
            segments.append(
                TranscriptSegment(
                    segment_id=f"seg-{len(segments) + 1:04d}",
                    sequence=len(segments),
                    speaker_id="spk_0",
                    start_time=start,
                    end_time=end,
                    text=text,
                )
            )

        logger.info(
            "Transcribed %s: %d segments, detected language=%s, audio duration=%.1fs",
            audio_path.name,
            len(segments),
            getattr(info, "language", "?"),
            getattr(info, "duration", 0.0) or 0.0,
        )
        return segments

    async def transcribe(
        self,
        audio_path: Path | str,
        language: str = "en",
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        _ = (language, kwargs)
        # MEETINGOS_WHISPER_LANGUAGE wins; otherwise let Whisper auto-detect the language
        lang = self.language or None
        return await asyncio.to_thread(self._transcribe_sync, Path(audio_path), lang)


class SingleSpeakerDiarizer(BaseDiarizer):
    """No speaker separation: the whole recording is attributed to one speaker.

    Used by default because real diarization (pyannote) needs large extra models and a
    Hugging Face token. Better than inventing speaker names.
    """

    async def diarize(
        self,
        audio_path: Path | str,
        num_speakers: int | None = None,
        **kwargs: Any,
    ) -> list[SpeakerInfo]:
        _ = (audio_path, num_speakers, kwargs)
        return [SpeakerInfo(speaker_id="spk_0", name="Speaker 1")]
