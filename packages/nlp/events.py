import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from packages.common.enums import EventType
from packages.common.models import ExtractedEntity, ExtractedEvent, TranscriptSegment
from packages.nlp.interfaces import BaseEventExtractor


class RuleBasedEventExtractor(BaseEventExtractor):
    """Extracts lifecycle and state-change events from meeting segments."""

    async def extract_events(
        self,
        segments: list[TranscriptSegment],
        meeting_id: str,
        meeting_date: datetime,
        entities_by_segment: dict[str, list[ExtractedEntity]] | None = None,
        **kwargs: Any,
    ) -> list[ExtractedEvent]:
        _ = kwargs
        events: list[ExtractedEvent] = []
        dt = meeting_date if meeting_date.tzinfo is not None else meeting_date.replace(tzinfo=UTC)
        entities_map = entities_by_segment or {}

        for seg in segments:
            text = seg.text
            lowered = text.lower()
            seg_entities = entities_map.get(seg.segment_id, [])
            first_ent_id = seg_entities[0].entity_id if seg_entities else None

            # 1. Decision Approved / Modified / Reversed
            if re.search(
                r"\b(we decided|officially approved|settled on|the decision is|agreed to adopt)\b",
                lowered,
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.DECISION_APPROVED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )
            elif re.search(
                r"\b(reverse the decision|overturn|cancel the previous decision|reject)\b",
                lowered,
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.DECISION_REVERSED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )
            elif re.search(
                r"\b(modify the decision|update our plan|change the approach)\b", lowered
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.DECISION_MODIFIED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )

            # 2. Issue Detected / Resolved
            if re.search(
                r"\b(issue is resolved|bug fixed|problem resolved|fixed the timeout)\b", lowered
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.ISSUE_RESOLVED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )
            elif re.search(
                r"\b(found an issue|facing a problem|hit a blocker|error occurred|performance degraded)\b",
                lowered,
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.ISSUE_DETECTED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )

            # 3. Commitment Assigned / Deadline Changed
            if re.search(
                r"\b(new deadline|pushed the deadline|extended the date|rescheduled)\b", lowered
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.DEADLINE_CHANGED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )
            elif re.search(
                r"\b(i will deliver|i will finish|assigned to|takes ownership)\b", lowered
            ):
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{uuid4()}",
                        event_type=EventType.COMMITMENT_ASSIGNED,
                        occurred_at=dt,
                        meeting_id=meeting_id,
                        subject_entity_id=first_ent_id,
                        payload={"text": text},
                        evidence_segment_id=seg.segment_id,
                    )
                )

        return events
