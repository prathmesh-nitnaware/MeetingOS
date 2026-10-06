import io
from pathlib import Path

import pytest
from packages.common.enums import SourceType
from packages.ingestion.validator import (
    FileValidationError,
    inspect_media_file,
    save_upload_file,
    validate_file_extension,
    validate_file_size,
)


def test_validate_file_extension_supported():
    assert validate_file_extension("meeting.wav") == SourceType.AUDIO_WAV
    assert validate_file_extension("AUDIO.MP3") == SourceType.AUDIO_MP3
    assert validate_file_extension("call.m4a") == SourceType.AUDIO_M4A
    assert validate_file_extension("session.mp4") == SourceType.VIDEO_MP4
    assert validate_file_extension("transcript.txt") == SourceType.TEXT_TRANSCRIPT
    assert validate_file_extension("subtitles.srt") == SourceType.SRT_SUBTITLE


def test_validate_file_extension_unsupported():
    with pytest.raises(FileValidationError) as exc:
        validate_file_extension("malware.exe")
    assert "Unsupported file extension" in str(exc.value)

    with pytest.raises(FileValidationError):
        validate_file_extension("no_extension")


def test_validate_file_size():
    # Valid sizes
    validate_file_size(1024, max_size_mb=10)
    validate_file_size(5 * 1024 * 1024, max_size_mb=10)

    # Empty file
    with pytest.raises(FileValidationError) as exc:
        validate_file_size(0)
    assert "empty" in str(exc.value)

    # Exceeding size
    with pytest.raises(FileValidationError) as exc:
        validate_file_size(11 * 1024 * 1024, max_size_mb=10)
    assert "exceeds maximum permitted limit" in str(exc.value)


def test_save_upload_file(tmp_path: Path):
    dest = tmp_path / "saved.wav"
    data = b"RIFF....WAVEfmt ...."
    stream = io.BytesIO(data)

    saved_bytes = save_upload_file(stream, dest, max_size_mb=1)
    assert saved_bytes == len(data)
    assert dest.exists()
    assert dest.read_bytes() == data


def test_save_empty_upload_file_fails(tmp_path: Path):
    dest = tmp_path / "empty.wav"
    stream = io.BytesIO(b"")

    with pytest.raises(FileValidationError):
        save_upload_file(stream, dest, max_size_mb=1)
    assert not dest.exists()


def test_inspect_media_file(tmp_path: Path):
    file_path = tmp_path / "sample.mp3"
    file_path.write_bytes(b"1234567890" * 100)

    info = inspect_media_file(file_path)
    assert info["file_size_bytes"] == 1000
    assert info["audio_sample_rate_hz"] == 16000
