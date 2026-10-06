from pathlib import Path

import pytest
from evaluation.baselines import KeywordSearchEngine, VectorSearchEngine
from evaluation.dataset import load_evaluation_dataset, load_mock_meetings
from evaluation.run import LabeledQuestion, compute_metrics, setup_evaluation_database
from packages.reasoning.qa import QueryPlan
from packages.reasoning.qa import QueryResponse as QAQueryResponse
from sqlalchemy.ext.asyncio import AsyncSession


def test_load_evaluation_dataset():
    dataset = load_evaluation_dataset()
    assert len(dataset) > 0
    for q in dataset:
        assert q.id is not None
        assert q.question is not None
        assert q.expected_answer is not None
        assert q.category is not None


def test_load_mock_meetings():
    meetings = load_mock_meetings()
    assert len(meetings) == 3
    for m in meetings:
        assert m["meeting_id"] is not None
        assert m["title"] is not None
        assert m["source_type"] == "audio/wav"
        assert len(m["segments"]) > 0


@pytest.mark.asyncio
async def test_baseline_search_engines(test_db_session: AsyncSession):
    # Setup eval DB tables and mock meetings in in-memory session
    await setup_evaluation_database(test_db_session)

    keyword_engine = KeywordSearchEngine(test_db_session)
    vector_engine = VectorSearchEngine(test_db_session)

    # Test keyword search
    kw_res = await keyword_engine.search("PostgreSQL")
    assert kw_res.total_results > 0
    assert "postgres" in kw_res.results[0].text.lower()

    # Test vector search
    vec_res = await vector_engine.search("PostgreSQL")
    assert vec_res.total_results > 0


def test_compute_metrics_calculation():
    q = LabeledQuestion(
        id="q-test",
        question="Which database?",
        expected_answer="PostgreSQL",
        category="factual",
        evidence_segments=["adopt PostgreSQL"],
        required_entities=["PostgreSQL"],
    )

    # Perfect response match
    from packages.common.enums import SourceType
    from packages.common.models import EvidenceItem

    evidence = [
        EvidenceItem(
            meeting_id="m1",
            segment_id="s1",
            start_time=0.0,
            end_time=5.0,
            text_snapshot="We decided to adopt PostgreSQL.",
            source_type=SourceType.AUDIO_WAV,
        )
    ]
    resp = QAQueryResponse(
        question="Which database?",
        answer="We adopted PostgreSQL.",
        evidence=evidence,
        query_plan=QueryPlan(intent="qa"),
        confidence=1.0,
    )

    m = compute_metrics(resp, q)
    assert m["answer_accuracy"] == 1.0
    assert m["retrieval_recall"] == 1.0
    assert m["entity_recall"] == 1.0

    # Mismatch response
    resp_bad = QAQueryResponse(
        question="Which database?",
        answer="We adopted MongoDB.",
        evidence=[],
        query_plan=QueryPlan(intent="qa"),
        confidence=1.0,
    )
    m_bad = compute_metrics(resp_bad, q)
    assert m_bad["answer_accuracy"] == 0.0
    assert m_bad["retrieval_recall"] == 0.0
    assert m_bad["entity_recall"] == 0.0


def test_experiment_reports_generation():
    reports_dir = Path(__file__).parent.parent.parent / "evaluation" / "reports"
    assert (reports_dir / "raw_results.json").exists()
    assert (reports_dir / "experiment_report.md").exists()
