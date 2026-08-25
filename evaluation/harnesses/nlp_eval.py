from dataclasses import dataclass
from typing import Any


@dataclass
class MetricScore:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def compute_prf1(predictions: set[Any], ground_truth: set[Any]) -> MetricScore:
    """Compute precision, recall, and F1 score between predicted set and ground truth set."""
    tp = len(predictions & ground_truth)
    fp = len(predictions - ground_truth)
    fn = len(ground_truth - predictions)

    precision = (
        tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not ground_truth and not predictions else 0.0)
    )
    recall = (
        tp / (tp + fn) if (tp + fn) > 0 else (1.0 if not ground_truth and not predictions else 0.0)
    )
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return MetricScore(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


class NLPEvaluationHarness:
    """Evaluation harness for measuring extraction quality across MeetingOS NLP extractors."""

    @staticmethod
    def evaluate_ner(
        predicted_entities: list[Any], ground_truth_entities: list[dict[str, str]]
    ) -> MetricScore:
        """Evaluate Named Entity Recognition (name + entity_type matching)."""
        pred_set = {(e.name.lower(), str(e.entity_type).upper()) for e in predicted_entities}
        gt_set = {(g["name"].lower(), g["entity_type"].upper()) for g in ground_truth_entities}
        return compute_prf1(pred_set, gt_set)

    @staticmethod
    def evaluate_decisions(
        predicted_decisions: list[Any], ground_truth_decisions: list[dict[str, str]]
    ) -> MetricScore:
        """Evaluate Decision extraction."""
        pred_set = {d.subject.strip().lower() for d in predicted_decisions}
        gt_set = {g["subject"].strip().lower() for g in ground_truth_decisions}
        return compute_prf1(pred_set, gt_set)

    @staticmethod
    def evaluate_commitments(
        predicted_commitments: list[Any], ground_truth_commitments: list[dict[str, str]]
    ) -> MetricScore:
        """Evaluate Commitment and Action extraction."""
        pred_set = {c.description.strip().lower() for c in predicted_commitments}
        gt_set = {g["description"].strip().lower() for g in ground_truth_commitments}
        return compute_prf1(pred_set, gt_set)

    @staticmethod
    def evaluate_issues(
        predicted_issues: list[Any], ground_truth_issues: list[dict[str, str]]
    ) -> MetricScore:
        """Evaluate Issue extraction."""
        pred_set = {i.description.strip().lower() for i in predicted_issues}
        gt_set = {g["description"].strip().lower() for g in ground_truth_issues}
        return compute_prf1(pred_set, gt_set)
