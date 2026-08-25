import math
from datetime import datetime, timedelta
from typing import Any

from packages.common.enums import (
    EntityType,
    EventType,
    RelationType,
    UtteranceClass,
)
from packages.common.models import (
    ExtractedEntity,
    ExtractedEvent,
    ExtractedRelation,
    NormalizedTemporal,
    TranscriptSegment,
)
from packages.nlp.interfaces import (
    BaseClassifier,
    BaseCoreferenceResolver,
    BaseEmbedder,
    BaseEventExtractor,
    BaseNER,
    BaseRelationExtractor,
    BaseTemporalExtractor,
)


class MockNER(BaseNER):
    """Deterministic Mock NER provider."""

    async def extract_entities(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[ExtractedEntity]:
        _ = kwargs
        entities: list[ExtractedEntity] = []
        lowered = text.lower()

        known_entities = [
            ("rahul", "Rahul Verma", EntityType.PERSON),
            ("priya", "Priya Sharma", EntityType.PERSON),
            ("meetingos", "MeetingOS", EntityType.PROJECT),
            ("postgresql", "PostgreSQL", EntityType.TECHNOLOGY),
            ("postgres", "PostgreSQL", EntityType.TECHNOLOGY),
            ("mongodb", "MongoDB", EntityType.TECHNOLOGY),
            ("friday", "Friday", EntityType.DATE),
            ("august 25", "August 25", EntityType.DATE),
        ]

        for trigger, canonical, ent_type in known_entities:
            idx = lowered.find(trigger)
            if idx != -1:
                entities.append(
                    ExtractedEntity(
                        entity_id=f"ent-{trigger}",
                        name=canonical,
                        entity_type=ent_type,
                        start_char=idx,
                        end_char=idx + len(trigger),
                        segment_id=segment_id,
                        confidence=0.95,
                    )
                )
        return entities


class MockClassifier(BaseClassifier):
    """Deterministic Mock Utterance Classifier."""

    async def classify_utterance(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[UtteranceClass]:
        _ = (segment_id, kwargs)
        lowered = text.lower()
        classes: list[UtteranceClass] = []

        if (
            "decid" in lowered
            or "propose" in lowered
            or "adopting" in lowered
            or "agreed" in lowered
        ):
            classes.append(UtteranceClass.DECISION)
        if "will" in lowered or "please finish" in lowered or "action" in lowered:
            classes.append(UtteranceClass.ACTION)
        if "commit" in lowered or "i will" in lowered:
            classes.append(UtteranceClass.COMMITMENT)
        if "?" in text or "what" in lowered or "why" in lowered:
            classes.append(UtteranceClass.QUESTION)
        if "problem" in lowered or "issue" in lowered or "failure" in lowered:
            classes.append(UtteranceClass.PROBLEM)

        if not classes:
            classes.append(UtteranceClass.INFORMATION)
        return classes


class MockRelationExtractor(BaseRelationExtractor):
    """Deterministic Mock Relation Extractor."""

    async def extract_relations(
        self,
        segment: TranscriptSegment,
        entities: list[ExtractedEntity],
        meeting_id: str,
        **kwargs: Any,
    ) -> list[ExtractedRelation]:
        _ = kwargs
        relations: list[ExtractedRelation] = []
        entity_names = {e.name.lower(): e.entity_id for e in entities}

        if "rahul verma" in entity_names and "meetingos" in entity_names:
            relations.append(
                ExtractedRelation(
                    relation_id="rel-001",
                    source_entity_id=entity_names["rahul verma"],
                    target_entity_id=entity_names["meetingos"],
                    relationship_type=RelationType.WORKS_ON,
                    meeting_id=meeting_id,
                    segment_id=segment.segment_id,
                    confidence=0.92,
                )
            )

        if "rahul verma" in entity_names and "postgresql" in entity_names:
            relations.append(
                ExtractedRelation(
                    relation_id="rel-002",
                    source_entity_id=entity_names["rahul verma"],
                    target_entity_id=entity_names["postgresql"],
                    relationship_type=RelationType.ASSIGNED_TO,
                    meeting_id=meeting_id,
                    segment_id=segment.segment_id,
                    confidence=0.90,
                )
            )

        return relations


class MockEventExtractor(BaseEventExtractor):
    """Deterministic Mock Event Extractor."""

    async def extract_events(
        self,
        segments: list[TranscriptSegment],
        meeting_id: str,
        meeting_date: datetime,
        **kwargs: Any,
    ) -> list[ExtractedEvent]:
        _ = kwargs
        events: list[ExtractedEvent] = []

        for seg in segments:
            lowered = seg.text.lower()
            if "agreed" in lowered or "official choice" in lowered:
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{seg.segment_id}-decision",
                        event_type=EventType.DECISION_APPROVED,
                        occurred_at=meeting_date,
                        meeting_id=meeting_id,
                        subject_entity_id="ent-postgresql",
                        payload={"summary": "PostgreSQL approved as official database"},
                        evidence_segment_id=seg.segment_id,
                    )
                )
            if "deadline" in lowered or "by friday" in lowered:
                events.append(
                    ExtractedEvent(
                        event_id=f"evt-{seg.segment_id}-deadline",
                        event_type=EventType.COMMITMENT_ASSIGNED,
                        occurred_at=meeting_date,
                        meeting_id=meeting_id,
                        subject_entity_id="ent-rahul",
                        payload={"deadline_phrase": "by Friday"},
                        evidence_segment_id=seg.segment_id,
                    )
                )

        return events


class MockTemporalExtractor(BaseTemporalExtractor):
    """Deterministic Mock Temporal Extractor."""

    async def normalize_time(
        self,
        text: str,
        reference_date: datetime,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedTemporal]:
        _ = kwargs
        results: list[NormalizedTemporal] = []
        lowered = text.lower()

        if "tomorrow" in lowered:
            results.append(
                NormalizedTemporal(
                    text="tomorrow",
                    normalized_date=reference_date + timedelta(days=1),
                    segment_id=segment_id,
                )
            )
        if "friday" in lowered:
            # Normalize to 4 days after reference date for determinism
            results.append(
                NormalizedTemporal(
                    text="Friday",
                    normalized_date=reference_date + timedelta(days=4),
                    segment_id=segment_id,
                )
            )

        return results


class MockCoreferenceResolver(BaseCoreferenceResolver):
    """Deterministic Mock Coreference Resolver."""

    async def resolve(
        self,
        segments: list[TranscriptSegment],
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        _ = kwargs
        # Returns segments with pronouns deterministically resolved for known patterns
        resolved_segments: list[TranscriptSegment] = []
        for s in segments:
            new_text = s.text.replace("He will finish it", "Rahul Verma will finish the schema")
            resolved_segments.append(
                TranscriptSegment(
                    segment_id=s.segment_id,
                    sequence=s.sequence,
                    speaker_id=s.speaker_id,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    text=new_text,
                )
            )
        return resolved_segments


class MockEmbedder(BaseEmbedder):
    """Deterministic Mock Vector Embedder producing fixed-dimension unit vectors."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        _ = kwargs
        vectors: list[list[float]] = []
        for text in texts:
            # Deterministic pseudo-embedding based on text hash
            seed = sum(ord(c) for c in text)
            raw = [math.sin(seed + i) for i in range(self.dimension)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            unit_vec = [round(x / norm, 6) for x in raw]
            vectors.append(unit_vec)
        return vectors
