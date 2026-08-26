from typing import Any

from packages.common.models import EvidenceItem
from packages.reasoning.qa import QueryResponse

from evaluation.dataset import LabeledQuestion


def compute_metrics_extended(
    response: QueryResponse,
    target: LabeledQuestion,
    latency_seconds: float = 0.0,
    trace_items: list[Any] | None = None,
) -> dict[str, float]:
    """Compute comprehensive evaluation metrics for a single QA query execution.

    Measures:
    - answer_accuracy: whether expected answer substring is present
    - retrieval_recall: fraction of target evidence segments retrieved
    - evidence_recall: fraction of required ground-truth evidence items matched
    - entity_recall: fraction of required entities mentioned in answer
    - citation_precision: fraction of citations that contain relevant segment tokens
    - citation_recall: fraction of expected evidence items covered by citations
    - faithfulness: whether response is grounded without hallucinated unestablished facts
    - insufficient_evidence_accuracy: correct identification of insufficient evidence
    - avg_confidence: numerical confidence score
    - latency_seconds: response latency
    - answer_length: length of generated answer text
    - per-agent timing metrics from agent traces
    """
    answer_text = response.answer.lower()
    expected_answer = target.expected_answer.lower()
    is_insufficient_target = "does not establish" in expected_answer or not target.evidence_segments
    is_insufficient_predicted = (
        "does not establish" in answer_text
        or response.confidence == 0.0
        or bool(getattr(response, "insufficient_evidence", False))
    )

    # 1. Answer Accuracy
    if is_insufficient_target:
        answer_accuracy = 1.0 if is_insufficient_predicted else 0.0
    else:
        answer_accuracy = 1.0 if expected_answer in answer_text else 0.0

    # 2. Insufficient Evidence Accuracy
    if is_insufficient_target:
        insufficient_accuracy = 1.0 if is_insufficient_predicted else 0.0
    else:
        insufficient_accuracy = 1.0 if not is_insufficient_predicted else 0.0

    # 3. Retrieval Recall & Evidence Recall
    retrieved_texts: list[str] = []
    for ev in response.evidence:
        if isinstance(ev, EvidenceItem):
            retrieved_texts.append(ev.text_snapshot.lower())
        elif hasattr(ev, "content"):
            retrieved_texts.append(str(getattr(ev, "content", "")).lower())
        elif hasattr(ev, "text_snapshot"):
            retrieved_texts.append(str(getattr(ev, "text_snapshot", "")).lower())

    target_segments = [t.lower() for t in target.evidence_segments]
    hits = 0
    for target_seg in target_segments:
        if any(target_seg in ret_text for ret_text in retrieved_texts):
            hits += 1

    if target_segments:
        retrieval_recall = hits / len(target_segments)
        evidence_recall = hits / len(target_segments)
    else:
        # For ungrounded/insufficient questions
        retrieval_recall = (
            1.0 if is_insufficient_predicted else (1.0 if not retrieved_texts else 0.5)
        )
        evidence_recall = 1.0 if is_insufficient_predicted else 0.0

    # 4. Entity Recall
    if target.required_entities:
        entities_matched = sum(
            1
            for ent in target.required_entities
            if ent.lower() in answer_text or ent.lower() in " ".join(retrieved_texts)
        )
        entity_recall = entities_matched / len(target.required_entities)
    else:
        entity_recall = 1.0

    # 5. Citation Precision & Citation Recall
    citations_count = len(response.evidence)
    if citations_count > 0:
        valid_citations = (
            sum(1 for ret_text in retrieved_texts if any(t in ret_text for t in target_segments))
            if target_segments
            else (citations_count if is_insufficient_predicted else 0)
        )
        citation_precision = valid_citations / citations_count
    else:
        citation_precision = 1.0 if is_insufficient_target else 0.0

    citation_recall = retrieval_recall

    # 6. Faithfulness (Heuristic: answer facts are attested in retrieved text or standard refusal)
    if is_insufficient_predicted:
        faithfulness = 1.0 if is_insufficient_target else 0.5
    else:
        # If answering, check that entities mentioned in answer were in retrieved evidence
        mentioned_entities = [ent for ent in target.required_entities if ent.lower() in answer_text]
        if mentioned_entities:
            attested = sum(
                1
                for ent in mentioned_entities
                if any(ent.lower() in ret_text for ret_text in retrieved_texts)
            )
            faithfulness = attested / len(mentioned_entities)
        else:
            faithfulness = 1.0 if answer_accuracy == 1.0 else 0.5

    # 7. Confidence & Length
    confidence = float(response.confidence)
    answer_length = float(len(response.answer))

    # 8. Agent-specific latencies
    agent_latencies: dict[str, float] = {
        "planner_latency": 0.0,
        "retrieval_latency": 0.0,
        "temporal_latency": 0.0,
        "graph_latency": 0.0,
        "evidence_latency": 0.0,
        "answer_latency": 0.0,
        "orchestration_total_latency": latency_seconds,
    }

    if trace_items:
        for t in trace_items:
            agent_name = getattr(t, "agent", None) or (
                t.get("agent") if isinstance(t, dict) else None
            )
            dur = getattr(t, "duration_seconds", None) or (
                t.get("duration_seconds") if isinstance(t, dict) else None
            )
            if agent_name and dur is not None:
                key = f"{agent_name}_latency"
                if key in agent_latencies:
                    agent_latencies[key] = float(dur)

    metrics = {
        "answer_accuracy": round(answer_accuracy, 4),
        "retrieval_recall": round(retrieval_recall, 4),
        "evidence_recall": round(evidence_recall, 4),
        "entity_recall": round(entity_recall, 4),
        "citation_precision": round(citation_precision, 4),
        "citation_recall": round(citation_recall, 4),
        "faithfulness": round(faithfulness, 4),
        "insufficient_evidence_accuracy": round(insufficient_accuracy, 4),
        "avg_confidence": round(confidence, 4),
        "latency_seconds": round(latency_seconds, 4),
        "answer_length": round(answer_length, 1),
    }
    metrics.update(agent_latencies)
    return metrics
