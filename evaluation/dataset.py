import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LabeledQuestion(BaseModel):
    id: str
    question: str
    expected_answer: str
    category: str
    evidence_segments: list[str] = Field(default_factory=list)
    required_entities: list[str] = Field(default_factory=list)
    type_filter: str | None = None


def get_datasets_dir() -> Path:
    return Path(__file__).parent.parent / "datasets" / "evaluation"


def load_evaluation_dataset() -> list[LabeledQuestion]:
    dataset_path = get_datasets_dir() / "labeled_dataset.json"
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")
    with dataset_path.open("r", encoding="utf-8") as f:
        items = json.load(f)
    return [LabeledQuestion(**item) for item in items]


def load_mock_meetings() -> list[dict[str, Any]]:
    meetings = []
    datasets_dir = get_datasets_dir()
    for filename in ["meeting_001.json", "meeting_002.json", "meeting_003.json"]:
        filepath = datasets_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Mock meeting file not found at {filepath}")
        with filepath.open("r", encoding="utf-8") as f:
            meetings.append(json.load(f))
    return meetings
