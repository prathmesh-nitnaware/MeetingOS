from pathlib import Path
from typing import BinaryIO

from packages.common.enums import SourceType

# Mapping supported extensions to canonical SourceType
EXTENSION_TO_SOURCE_TYPE: dict[str, SourceType] = {
    ".wav": SourceType.AUDIO_WAV,
    ".mp3": SourceType.AUDIO_MP3,
    ".m4a": SourceType.AUDIO_M4A,
    ".mp4": SourceType.VIDEO_MP4,
    ".txt": SourceType.TEXT_TRANSCRIPT,
    ".srt": SourceType.SRT_SUBTITLE,
}


class FileValidationError(ValueError):
    """Raised when an uploaded file fails validation checks."""

    pass


def validate_file_extension(filename: str) -> SourceType:
    """Validate file extension and return its SourceType."""
    ext = Path(filename).suffix.lower()
    if not ext or ext not in EXTENSION_TO_SOURCE_TYPE:
        supported = ", ".join(EXTENSION_TO_SOURCE_TYPE.keys())
        raise FileValidationError(
            f"Unsupported file extension '{ext}' for file '{filename}'. Supported extensions: {supported}"
        )
    return EXTENSION_TO_SOURCE_TYPE[ext]


def validate_file_size(file_size_bytes: int, max_size_mb: int = 500) -> None:
    """Ensure uploaded file size is within limits."""
    if file_size_bytes <= 0:
        raise FileValidationError("Uploaded file is empty (0 bytes).")
    max_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise FileValidationError(
            f"File size ({file_size_bytes / (1024 * 1024):.2f} MB) exceeds maximum permitted limit of {max_size_mb} MB."
        )


def inspect_media_file(file_path: Path) -> dict[str, int | float | None]:
    """Inspect basic metadata from audio/video file."""
    if not file_path.exists():
        raise FileValidationError(f"File not found at path: {file_path}")
    size = file_path.stat().st_size
    validate_file_size(size)
    return {
        "file_size_bytes": size,
        "audio_sample_rate_hz": 16000,
        "audio_channels": 1,
        "audio_duration_seconds": None,
    }


def save_upload_file(upload_file: BinaryIO, destination_path: Path, max_size_mb: int = 500) -> int:
    """Safely stream upload file to disk while validating size."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    max_bytes = max_size_mb * 1024 * 1024

    with destination_path.open("wb") as out_file:
        while chunk := upload_file.read(1024 * 1024):  # 1MB chunks
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise FileValidationError(f"Upload exceeded maximum size of {max_size_mb} MB.")
            out_file.write(chunk)

    if total_bytes == 0:
        if destination_path.exists():
            destination_path.unlink()
        raise FileValidationError("Uploaded file is empty.")

    return total_bytes
