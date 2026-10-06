import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class AudioCorpusItem(BaseModel):
    """Metadata schema representing an audio evaluation corpus item."""

    meeting_id: str
    audio_path: str
    duration_seconds: float = Field(..., gt=0)
    language: str = "en"
    expected_speakers: int = Field(default=1, ge=1)
    source_type: Literal["synthetic", "public", "user_provided"] = "synthetic"
    license: str = "MIT / Public Domain"
    license_url: str | None = None
    transcript_available: bool = True
    diarization_reference_available: bool = False
    reference_transcript: str | None = None
    reference_speakers: list[str] = Field(default_factory=list)


class AudioCorpusManifest(BaseModel):
    """Manifest inventory of evaluation audio recordings."""

    version: str = "1.0.0"
    description: str = "MeetingOS Real-World & Synthetic Audio Evaluation Corpus"
    items: list[AudioCorpusItem] = Field(default_factory=list)

    def get_item(self, meeting_id: str) -> AudioCorpusItem | None:
        for item in self.items:
            if item.meeting_id == meeting_id:
                return item
        return None

    def save_manifest(self, file_path: Path | str) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
        return path

    @classmethod
    def load_manifest(cls, file_path: Path | str) -> "AudioCorpusManifest":
        path = Path(file_path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)


def get_default_corpus_manifest() -> AudioCorpusManifest:
    """Generate default manifest containing synthetic and publicly referenceable audio records."""
    return AudioCorpusManifest(
        items=[
            AudioCorpusItem(
                meeting_id="audio-synth-001",
                audio_path="datasets/audio/fixtures/synth_arch_sync.wav",
                duration_seconds=18.0,
                language="en",
                expected_speakers=2,
                source_type="synthetic",
                license="CC0-1.0 / Public Domain",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                transcript_available=True,
                diarization_reference_available=True,
                reference_transcript="Welcome everyone. Today we are deciding on the database architecture for MeetingOS. Rahul and I evaluated MongoDB and PostgreSQL. We propose adopting PostgreSQL with pgvector. Agreed. Let's make PostgreSQL the official choice. Rahul, please finish the schema by Friday.",
                reference_speakers=["Priya Sharma", "Rahul Verma"],
            ),
            AudioCorpusItem(
                meeting_id="audio-synth-002",
                audio_path="datasets/audio/fixtures/synth_infra_scaling.wav",
                duration_seconds=24.0,
                language="en",
                expected_speakers=3,
                source_type="synthetic",
                license="CC0-1.0 / Public Domain",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                transcript_available=True,
                diarization_reference_available=True,
                reference_transcript="Let's review the container orchestration roadmap. We are reversing the Docker Compose decision and migrating to Kubernetes. Priya, can your team handle the Helm charts by next Tuesday?",
                reference_speakers=["Alex Mercer", "Priya Sharma", "Vikram Patel"],
            ),
            AudioCorpusItem(
                meeting_id="audio-public-001",
                audio_path="datasets/audio/fixtures/public_w3c_sync.wav",
                duration_seconds=45.0,
                language="en",
                expected_speakers=2,
                source_type="public",
                license="W3C Document License",
                license_url="https://www.w3.org/Consortium/Legal/2015/doc-license",
                transcript_available=True,
                diarization_reference_available=False,
                reference_transcript="The working group is discussing web application audio streaming and accessibility guidelines for real-time transcription systems.",
                reference_speakers=["Speaker A", "Speaker B"],
            ),
        ]
    )
