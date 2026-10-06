import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from evaluation.harnesses.nlp_eval import NLPEvaluationHarness, compute_prf1
from packages.common.models import TranscriptSegment
from packages.nlp.pipeline import NLPExtractionPipeline


def test_compute_prf1_perfect_match():
    pred = {"apple", "banana"}
    gt = {"apple", "banana"}
    score = compute_prf1(pred, gt)
    assert score.precision == 1.0
    assert score.recall == 1.0
    assert score.f1 == 1.0


def test_compute_prf1_partial_match():
    pred = {"apple", "orange"}
    gt = {"apple", "banana"}
    score = compute_prf1(pred, gt)
    assert score.precision == 0.5
    assert score.recall == 0.5
    assert score.f1 == 0.5


@pytest.mark.asyncio
async def test_evaluation_against_ground_truth_dataset():
    dataset_path = (
        Path(__file__).parent.parent.parent
        / "datasets"
        / "ground_truth"
        / "sample_labeled_meeting_001.json"
    )
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    segments = [TranscriptSegment(**s) for s in data["segments"]]
    gt = data["ground_truth"]

    pipeline = NLPExtractionPipeline()
    result = await pipeline.process_transcript(
        meeting_id=data["meeting_id"],
        segments=segments,
        meeting_date=datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC),
    )

    # Evaluate NER
    ner_score = NLPEvaluationHarness.evaluate_ner(result.entities, gt["entities"])
    assert ner_score.precision >= 0.70
    assert ner_score.recall >= 0.70
    assert ner_score.f1 >= 0.70

    # Evaluate Decisions
    dec_score = NLPEvaluationHarness.evaluate_decisions(result.decisions, gt["decisions"])
    assert dec_score.precision >= 0.80
    assert dec_score.recall >= 0.80
    assert dec_score.f1 >= 0.80

    # Evaluate Commitments
    com_score = NLPEvaluationHarness.evaluate_commitments(result.commitments, gt["commitments"])
    assert com_score.precision >= 0.80
    assert com_score.recall >= 0.80

    # Evaluate Issues
    iss_score = NLPEvaluationHarness.evaluate_issues(result.issues, gt["issues"])
    assert iss_score.precision >= 0.80
    assert iss_score.recall >= 0.80
