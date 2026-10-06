import math
import struct
import wave
from pathlib import Path


def generate_synthetic_meeting_wav(
    output_path: Path | str,
    duration_seconds: float = 3.0,
    sample_rate: int = 16000,
) -> Path:
    """Generate a clean synthetic PCM WAV audio file simulating speech tones without external dependencies."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    num_samples = int(duration_seconds * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)

        # Generate harmonic speech-like formant tones (300Hz fundamental + 900Hz harmonic)
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Modulate amplitude smoothly
            envelope = math.sin(math.pi * t / duration_seconds)
            sample_val = 0.6 * math.sin(2 * math.pi * 300 * t) + 0.4 * math.sin(
                2 * math.pi * 900 * t
            )
            scaled = int(sample_val * envelope * 16384.0)
            clamped = max(-32768, min(32767, scaled))
            frames.extend(struct.pack("<h", clamped))

        wav_file.writeframes(frames)

    return path
