import io
from pathlib import Path

import pytest
from packages.common.enums import SourceType
from packages.ingestion.validator import (
    FileValidationError,
    sanitize_filename,
    save_upload_file,
    validate_file_extension,
    validate_file_size,
)


def test_sanitize_filename_traversal():
    assert sanitize_filename("../../etc/passwd.wav") == "passwd.wav"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe.mp3") == "cmd.exe.mp3"
    assert sanitize_filename("safe_recording.wav") == "safe_recording.wav"
    assert sanitize_filename("null\x00byte.wav") == "nullbyte.wav"


def test_validate_file_extension():
    assert validate_file_extension("meeting.wav") == SourceType.AUDIO_WAV
    assert validate_file_extension("recording.mp3") == SourceType.AUDIO_MP3
    assert validate_file_extension("transcript.txt") == SourceType.TEXT_TRANSCRIPT
    assert validate_file_extension("captions.srt") == SourceType.SRT_SUBTITLE

    with pytest.raises(FileValidationError):
        validate_file_extension("malicious.exe")

    with pytest.raises(FileValidationError):
        validate_file_extension("script.sh")


def test_validate_file_size():
    validate_file_size(1024, max_size_mb=10)

    with pytest.raises(FileValidationError):
        validate_file_size(0, max_size_mb=10)

    with pytest.raises(FileValidationError):
        validate_file_size(20 * 1024 * 1024, max_size_mb=10)


def test_save_upload_file_security(tmp_path: Path):
    dest = tmp_path / "test_upload.wav"
    data = b"RIFF" + b"\x00" * 100
    stream = io.BytesIO(data)

    saved_bytes = save_upload_file(stream, dest, max_size_mb=10)
    assert saved_bytes == len(data)
    assert dest.exists()


def test_save_upload_file_oversized_cleanup(tmp_path: Path):
    dest = tmp_path / "oversized.wav"
    data = b"x" * (2 * 1024 * 1024)  # 2MB
    stream = io.BytesIO(data)

    with pytest.raises(FileValidationError):
        save_upload_file(stream, dest, max_size_mb=1)  # 1MB limit

    # Destination file should be cleaned up on failure
    assert not dest.exists()
