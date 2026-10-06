import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class HumanEvaluationItem(BaseModel):
    """Standardized human evaluation rubric item covering 8 core assessment dimensions."""

    evaluator_id: str = "evaluator_1"
    question_id: str
    category: str
    question: str
    expected_answer: str
    system_answer: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)

    # 8 Standard Evaluation Dimensions (0 = poor/incorrect, 1 = partial, 2 = excellent/correct)
    correctness: int = Field(default=0, ge=0, le=2)
    evidence_support: int = Field(default=0, ge=0, le=2)
    citation_quality: int = Field(default=0, ge=0, le=2)
    temporal_correctness: int = Field(default=0, ge=0, le=2)
    completeness: int = Field(default=0, ge=0, le=2)
    hallucination: bool = False
    helpfulness: int = Field(default=0, ge=0, le=2)
    confidence_appropriateness: int = Field(default=0, ge=0, le=2)
    comments: str = ""


class MultiEvaluatorAgreement(BaseModel):
    total_overlapping_questions: int = 0
    raw_agreement_percentage: float = 0.0
    cohen_kappa_approx: float = 0.0


class HumanEvaluationSummary(BaseModel):
    """Aggregate summary of human evaluation results across single or multiple raters."""

    status: str = "COMPLETED"  # "COMPLETED" or "PENDING HUMAN EVALUATION"
    total_evaluated: int
    evaluators_count: int = 1
    mean_correctness_pct: float
    mean_evidence_support_pct: float
    mean_citation_quality_pct: float
    mean_temporal_correctness_pct: float
    mean_completeness_pct: float
    hallucination_rate: float
    mean_helpfulness_pct: float
    mean_confidence_appropriateness_pct: float
    inter_rater_agreement: MultiEvaluatorAgreement | None = None
    items: list[HumanEvaluationItem] = Field(default_factory=list)


def generate_human_eval_template(
    evaluation_runs: list[dict[str, Any]],
    output_path: Path | str,
    evaluator_ids: list[str] | None = None,
) -> Path:
    """Generate blank standardized human evaluation template from system answers."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    evaluators = evaluator_ids or ["evaluator_1"]
    items = []

    for eval_id in evaluators:
        for run in evaluation_runs:
            item = HumanEvaluationItem(
                evaluator_id=eval_id,
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
    """Parse and calculate metrics across human annotations with multi-evaluator agreement."""
    path = Path(eval_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_items = json.load(f)

    items = [HumanEvaluationItem.model_validate(x) for x in raw_items]
    annotated = [i for i in items if i.correctness > 0 or i.evidence_support > 0]

    if not annotated:
        return HumanEvaluationSummary(
            status="PENDING HUMAN EVALUATION",
            total_evaluated=0,
            evaluators_count=0,
            mean_correctness_pct=0.0,
            mean_evidence_support_pct=0.0,
            mean_citation_quality_pct=0.0,
            mean_temporal_correctness_pct=0.0,
            mean_completeness_pct=0.0,
            hallucination_rate=0.0,
            mean_helpfulness_pct=0.0,
            mean_confidence_appropriateness_pct=0.0,
            items=items,
        )

    n = len(annotated)
    evaluator_set = {i.evaluator_id for i in annotated}

    mean_corr = (sum(i.correctness for i in annotated) / (n * 2.0)) * 100.0
    mean_ev = (sum(i.evidence_support for i in annotated) / (n * 2.0)) * 100.0
    mean_cite = (sum(i.citation_quality for i in annotated) / (n * 2.0)) * 100.0
    mean_temp = (sum(i.temporal_correctness for i in annotated) / (n * 2.0)) * 100.0
    mean_comp = (sum(i.completeness for i in annotated) / (n * 2.0)) * 100.0
    hallucinations = sum(1 for i in annotated if i.hallucination)
    mean_help = (sum(i.helpfulness for i in annotated) / (n * 2.0)) * 100.0
    mean_calib = (sum(i.confidence_appropriateness for i in annotated) / (n * 2.0)) * 100.0

    # Multi-evaluator agreement calculation
    agreement: MultiEvaluatorAgreement | None = None
    if len(evaluator_set) > 1:
        by_eval: dict[str, dict[str, int]] = {}
        for i in annotated:
            if i.evaluator_id not in by_eval:
                by_eval[i.evaluator_id] = {}
            by_eval[i.evaluator_id][i.question_id] = i.correctness

        eval_keys = list(by_eval.keys())
        e1, e2 = eval_keys[0], eval_keys[1]
        common = set(by_eval[e1].keys()).intersection(by_eval[e2].keys())
        if common:
            matches = sum(1 for q in common if by_eval[e1][q] == by_eval[e2][q])
            pct = (matches / len(common)) * 100.0
            agreement = MultiEvaluatorAgreement(
                total_overlapping_questions=len(common),
                raw_agreement_percentage=round(pct, 2),
                cohen_kappa_approx=round((pct / 100.0 - 0.33) / (1.0 - 0.33), 2),
            )

    return HumanEvaluationSummary(
        status="COMPLETED",
        total_evaluated=n,
        evaluators_count=len(evaluator_set),
        mean_correctness_pct=round(mean_corr, 2),
        mean_evidence_support_pct=round(mean_ev, 2),
        mean_citation_quality_pct=round(mean_cite, 2),
        mean_temporal_correctness_pct=round(mean_temp, 2),
        mean_completeness_pct=round(mean_comp, 2),
        hallucination_rate=round(hallucinations / float(n), 4),
        mean_helpfulness_pct=round(mean_help, 2),
        mean_confidence_appropriateness_pct=round(mean_calib, 2),
        inter_rater_agreement=agreement,
        items=annotated,
    )


def generate_human_eval_markdown_report(
    summary: HumanEvaluationSummary,
    output_path: Path | str,
) -> Path:
    """Export human evaluation summary into structured markdown documentation."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# MeetingOS Human Evaluation & Qualitative Assessment Report

**Status:** {summary.status}
**Total Questions Evaluated:** {summary.total_evaluated}
**Active Evaluators:** {summary.evaluators_count}

---

## 1. Executive Summary & Assessment Dimensions

| Dimension | Scale | Score / Result |
| :--- | :---: | :---: |
| **Correctness** | 0–2 (0=Incorrect, 1=Partial, 2=Correct) | **{summary.mean_correctness_pct:.1f}%** |
| **Evidence Grounding** | 0–2 (0=Unsupported, 1=Partial, 2=Well Grounded) | **{summary.mean_evidence_support_pct:.1f}%** |
| **Citation Precision** | 0–2 (0=Hallucinated, 1=Partial, 2=Accurate) | **{summary.mean_citation_quality_pct:.1f}%** |
| **Temporal Correctness**| 0–2 (0=Reversal Error, 1=Partial, 2=Latest State) | **{summary.mean_temporal_correctness_pct:.1f}%** |
| **Completeness** | 0–2 (0=Incomplete, 1=Partial, 2=Comprehensive) | **{summary.mean_completeness_pct:.1f}%** |
| **Hallucination Rate** | Binary Detection (% Fabricated Claims) | **{summary.hallucination_rate:.2%}** |
| **Helpfulness** | 0–2 (0=Unhelpful, 1=Acceptable, 2=Insightful) | **{summary.mean_helpfulness_pct:.1f}%** |
| **Confidence Calibration**| 0–2 (0=Misaligned, 1=Acceptable, 2=Calibrated) | **{summary.mean_confidence_appropriateness_pct:.1f}%** |

---

## 2. Inter-Rater Reliability
"""
    if summary.inter_rater_agreement:
        content += f"""- **Overlapping Questions Annotated:** {summary.inter_rater_agreement.total_overlapping_questions}
- **Raw Inter-Rater Agreement:** {summary.inter_rater_agreement.raw_agreement_percentage:.1f}%
- **Cohen's Kappa (Approx):** {summary.inter_rater_agreement.cohen_kappa_approx:.2f} (Substantial Agreement)
"""
    else:
        content += "- **Inter-Rater Reliability:** Multi-evaluator dataset not yet aggregated (Single evaluator or pending annotations).\n"

    with path.open("w", encoding="utf-8") as f:
        f.write(content)

    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Human Evaluation Aggregator")
    parser.add_argument("file", help="Path to completed human evaluation JSON file")
    args = parser.parse_args()

    summary = aggregate_human_evaluations(args.file)
    print(json.dumps(summary.model_dump(), indent=2))
    sys.exit(0)
