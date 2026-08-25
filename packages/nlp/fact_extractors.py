from datetime import UTC, datetime
from uuid import uuid4

from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    IssueStatus,
    UtteranceClass,
)
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedIssue,
    NormalizedTemporal,
    TranscriptSegment,
)


class FactExtractors:
    """Extracts high-level organizational facts (Decisions, Commitments/Actions, Issues, Topics)."""

    @staticmethod
    def extract_decisions(
        segments: list[TranscriptSegment],
        classes_map: dict[str, list[UtteranceClass]],
        meeting_id: str,
    ) -> list[ExtractedDecision]:
        decisions: list[ExtractedDecision] = []
        for seg in segments:
            seg_classes = classes_map.get(seg.segment_id or "", [])
            text = seg.text
            lowered = text.lower()

            if UtteranceClass.DECISION in seg_classes or any(
                w in lowered
                for w in [
                    "we decided",
                    "decision is",
                    "officially adopt",
                    "agreed to",
                    "settled on",
                    "consensus is",
                ]
            ):
                status = DecisionStatus.APPROVED
                if "reverse" in lowered or "cancel" in lowered:
                    status = DecisionStatus.REVERSED
                elif "modify" in lowered or "update" in lowered:
                    status = DecisionStatus.MODIFIED
                elif "propose" in lowered or "suggest" in lowered:
                    status = DecisionStatus.PROPOSED

                # Extract subject from text
                subject = text
                if ":" in text:
                    subject = text.split(":", 1)[1].strip()

                decisions.append(
                    ExtractedDecision(
                        decision_id=f"dec-{uuid4()}",
                        subject=subject,
                        status=status,
                        rationale=f"Agreed during discussion by {seg.speaker_id}",
                        meeting_id=meeting_id,
                        evidence_segment_id=seg.segment_id,
                        created_at=datetime.now(UTC),
                    )
                )

        return decisions

    @staticmethod
    def extract_commitments_and_actions(
        segments: list[TranscriptSegment],
        classes_map: dict[str, list[UtteranceClass]],
        temporals_map: dict[str, list[NormalizedTemporal]],
        meeting_id: str,
    ) -> list[ExtractedCommitment]:
        commitments: list[ExtractedCommitment] = []
        for seg in segments:
            seg_classes = classes_map.get(seg.segment_id or "", [])
            text = seg.text
            lowered = text.lower()

            is_action_or_commit = (
                UtteranceClass.COMMITMENT in seg_classes
                or UtteranceClass.ACTION in seg_classes
                or any(
                    w in lowered
                    for w in [
                        "i will",
                        "i'll",
                        "action item",
                        "assigned to",
                        "please finish",
                        "will deliver",
                        "take ownership",
                    ]
                )
            )

            if is_action_or_commit:
                # Find deadline from temporals if present
                deadlines = temporals_map.get(seg.segment_id or "", [])
                deadline_dt = deadlines[0].normalized_date if deadlines else None

                owner = seg.speaker_id
                if "assigned to" in lowered:
                    parts = lowered.split("assigned to", 1)
                    if len(parts) > 1:
                        cand = parts[1].strip().split()[0]
                        owner = f"spk_{cand}"

                commitments.append(
                    ExtractedCommitment(
                        commitment_id=f"com-{uuid4()}",
                        description=text,
                        owner_id=owner,
                        status=CommitmentStatus.ASSIGNED
                        if "assigned" in lowered
                        else CommitmentStatus.IN_PROGRESS,
                        original_deadline=deadline_dt,
                        current_deadline=deadline_dt,
                        meeting_id=meeting_id,
                        evidence_segment_id=seg.segment_id,
                    )
                )

        return commitments

    @staticmethod
    def extract_issues(
        segments: list[TranscriptSegment],
        classes_map: dict[str, list[UtteranceClass]],
        meeting_date: datetime | None,
        meeting_id: str,
    ) -> list[ExtractedIssue]:
        issues: list[ExtractedIssue] = []
        dt = meeting_date or datetime.now(UTC)

        for seg in segments:
            seg_classes = classes_map.get(seg.segment_id or "", [])
            text = seg.text
            lowered = text.lower()

            if UtteranceClass.PROBLEM in seg_classes or any(
                w in lowered
                for w in [
                    "issue",
                    "problem",
                    "bug",
                    "timeout",
                    "blocker",
                    "failure",
                    "failing",
                    "risk",
                    "degraded",
                ]
            ):
                status = IssueStatus.DETECTED
                if "resolved" in lowered or "fixed" in lowered:
                    status = IssueStatus.RESOLVED
                elif "investigat" in lowered:
                    status = IssueStatus.UNDER_INVESTIGATION

                issues.append(
                    ExtractedIssue(
                        issue_id=f"iss-{uuid4()}",
                        description=text,
                        owner_id=seg.speaker_id,
                        status=status,
                        first_detected_at=dt,
                        last_mentioned_at=dt,
                        resolution_meeting_id=meeting_id
                        if status == IssueStatus.RESOLVED
                        else None,
                        evidence_segment_id=seg.segment_id,
                    )
                )

        return issues

    @staticmethod
    def extract_topics(
        segments: list[TranscriptSegment],
        entities: list[ExtractedEntity],
    ) -> list[str]:
        """Extract high-level key discussion topics from segments and entities."""
        topics = set()
        for ent in entities:
            if ent.entity_type.value in {"TECHNOLOGY", "PROJECT", "ORGANIZATION"}:
                topics.add(ent.name)

        # Keyword heuristics
        full_text = " ".join(s.text.lower() for s in segments)
        candidate_keywords = [
            ("database migration", "Database Migration"),
            ("authentication", "Authentication & Security"),
            ("api design", "API Design"),
            ("infrastructure", "Infrastructure & Deployment"),
            ("performance", "Performance Optimization"),
            ("vector search", "Vector Search & Retrieval"),
            ("speech recognition", "Speech & Diarization"),
        ]
        for trigger, label in candidate_keywords:
            if trigger in full_text:
                topics.add(label)

        return sorted(topics)
