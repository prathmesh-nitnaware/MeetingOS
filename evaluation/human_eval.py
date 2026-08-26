import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class HumanEvaluationItem(BaseModel):
    """Standardized human evaluation rubric item."""

    question_id: str
    category: str
    question: str
    expected_answer: str
    system_answer: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)

    # Evaluator Fields (1 to 5 Likert scale, 0 = unannotated)
    correctness: int = Field(default=0, ge=0, le=5)
    evidence_quality: int = Field(default=0, ge=0, le=5)
    citation_correctness: int = Field(default=0, ge=0, le=5)
    completeness: int = Field(default=0, ge=0, le=5)
    hallucination: bool = False
    comments: str = ""


class HumanEvaluationSummary(BaseModel):
    """Aggregate summary of human evaluation results."""

    total_evaluated: int
    mean_correctness: float
    mean_evidence_quality: float
    mean_citation_correctness: float
    mean_completeness: float
    hallucination_rate: float
    score_distribution: dict[str, dict[int, int]]


def generate_human_eval_template(
    evaluation_runs: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    """Generate blank standardized human evaluation template from system answers."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    items = []
    for run in evaluation_runs:
        item = HumanEvaluationItem(
            question_id=run.get("question_id", ""),
            category=run.get("category", ""),
            question=run.get("question", ""),
            expected_answer=run.get("expected_answer", ""),
            system_answer=run.get("system_answer", ""),
            confidence=run.get("confidence", 0.0),
            citations=run.get("citations", []),
            evidence_snippets=run.get("evidence_snippets", []),
        )
        items.append(item.model_dump())

    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    return path


def aggregate_human_evaluations(eval_file_path: Path | str) -> HumanEvaluationSummary:
    """Parse and calculate metrics across human annotations."""
    path = Path(eval_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_items = json.load(f)

    items = [HumanEvaluationItem.model_validate(x) for x in raw_items]
    annotated = [i for i in items if i.correctness > 0]

    if not annotated:
        return HumanEvaluationSummary(
            total_evaluated=0,
            mean_correctness=0.0,
            mean_evidence_quality=0.0,
            mean_citation_correctness=0.0,
            mean_completeness=0.0,
            hallucination_rate=0.0,
            score_distribution={},
        )

    n = len(annotated)
    mean_corr = sum(i.correctness for i in annotated) / n
    mean_ev = sum(i.evidence_quality for i in annotated) / n
    mean_cite = sum(i.citation_correctness for i in annotated) / n
    mean_comp = sum(i.completeness for i in annotated) / n
    hallucinations = sum(1 for i in annotated if i.hallucination)

    dist = {
        "correctness": dict.fromkeys(range(1, 6), 0),
        "evidence_quality": dict.fromkeys(range(1, 6), 0),
    }
    for i in annotated:
        dist["correctness"][i.correctness] += 1
        if 1 <= i.evidence_quality <= 5:
            dist["evidence_quality"][i.evidence_quality] += 1

    return HumanEvaluationSummary(
        total_evaluated=n,
        mean_correctness=round(mean_corr, 2),
        mean_evidence_quality=round(mean_ev, 2),
        mean_citation_correctness=round(mean_cite, 2),
        mean_completeness=round(mean_comp, 2),
        hallucination_rate=round(hallucinations / n, 4),
        score_distribution=dist,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Human Evaluation Aggregator")
    parser.add_argument("file", help="Path to completed human evaluation JSON file")
    args = parser.parse_args()

    summary = aggregate_human_evaluations(args.file)
    print(json.dumps(summary.model_dump(), indent=2))
    sys.exit(0)
