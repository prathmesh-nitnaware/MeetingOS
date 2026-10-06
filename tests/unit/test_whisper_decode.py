import math
import struct
import wave
from pathlib import Path

import pytest
from packages.speech.whisper import WHISPER_SAMPLE_RATE, AudioDecodeError, decode_audio

pytest.importorskip("av", reason="speech extra not installed (uv sync --extra asr)")


def _write_tone(path: Path, seconds: float = 1.0, rate: int = 44100) -> None:
    frames = b"".join(
        struct.pack("<hh", int(8000 * math.sin(2 * math.pi * 440 * i / rate)), 0)
        for i in range(int(seconds * rate))
    )
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(frames)


def test_decode_audio_resamples_to_16k_mono_float(tmp_path: Path):
    wav = tmp_path / "tone.wav"
    _write_tone(wav)

    audio = decode_audio(wav)

    assert audio.dtype.name == "float32"
    assert audio.ndim == 1
    assert abs(len(audio) - WHISPER_SAMPLE_RATE) <= 32
    assert 0.1 < float(abs(audio).max()) <= 1.0


def test_decode_audio_rejects_non_audio_files(tmp_path: Path):
    bogus = tmp_path / "meeting.mp3"
    bogus.write_bytes(b"this is not audio" * 64)

    with pytest.raises(AudioDecodeError, match="could not be read as audio") as excinfo:
        decode_audio(bogus)
    # The message reaches API clients, so it must not reveal server file paths
    assert str(tmp_path) not in str(excinfo.value)
