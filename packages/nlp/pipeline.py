import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.common.enums import UtteranceClass
from packages.common.models import (
    EvidenceItem,
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIssue,
    ExtractedRelation,
    NormalizedTemporal,
    TranscriptSegment,
)
from packages.nlp.classifier import RuleBasedClassifier
from packages.nlp.coref import RuleBasedCoreferenceResolver
from packages.nlp.entity_resolution import EntityResolver
from packages.nlp.events import RuleBasedEventExtractor
from packages.nlp.fact_extractors import FactExtractors
from packages.nlp.interfaces import (
    BaseClassifier,
    BaseCoreferenceResolver,
    BaseEventExtractor,
    BaseNER,
    BaseRelationExtractor,
    BaseTemporalExtractor,
)
from packages.nlp.ner import RuleBasedNER
from packages.nlp.relations import RuleBasedRelationExtractor
from packages.nlp.temporal import RuleBasedTemporalExtractor
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UtteranceClassificationItem(BaseModel):
    segment_id: str
    classes: list[UtteranceClass]
    confidence: float = 0.95


class NLPExtractionResult(BaseModel):
    """Canonical aggregated output of the NLP extraction pipeline."""

    meeting_id: str
    entities: list[ExtractedEntity] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    actions: list[ExtractedCommitment] = Field(default_factory=list)
    commitments: list[ExtractedCommitment] = Field(default_factory=list)
    issues: list[ExtractedIssue] = Field(default_factory=list)
    events: list[ExtractedEvent] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    temporal_expressions: list[NormalizedTemporal] = Field(default_factory=list)
    classifications: list[UtteranceClassificationItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    model_metadata: dict[str, str] = Field(
        default_factory=lambda: {
            "model_name": "meetingos-nlp-suite",
            "model_version": "1.0.0",
            "pipeline_version": "2.0.0",
            "extracted_at": datetime.now(UTC).isoformat(),
        }
    )


class NLPExtractionPipeline:
    """Orchestrates modular deep learning and NLP extractors across meeting transcript segments."""

    def __init__(
        self,
        ner_provider: BaseNER | None = None,
        classifier_provider: BaseClassifier | None = None,
        temporal_provider: BaseTemporalExtractor | None = None,
        relation_provider: BaseRelationExtractor | None = None,
        event_provider: BaseEventExtractor | None = None,
        coref_provider: BaseCoreferenceResolver | None = None,
        entity_resolver: EntityResolver | None = None,
    ) -> None:
        self.ner = ner_provider or RuleBasedNER()
        self.classifier = classifier_provider or RuleBasedClassifier()
        self.temporal = temporal_provider or RuleBasedTemporalExtractor()
        self.relation_extractor = relation_provider or RuleBasedRelationExtractor()
        self.event_extractor = event_provider or RuleBasedEventExtractor()
        self.coref = coref_provider or RuleBasedCoreferenceResolver()
        self.entity_resolver = entity_resolver or EntityResolver()

    async def process_transcript(
        self,
        meeting_id: str,
        segments: list[TranscriptSegment],
        meeting_date: datetime | None = None,
    ) -> NLPExtractionResult:
        """Run full NLP extraction pipeline on a list of transcript segments."""
        logger.info(
            "Executing NLP extraction pipeline for meeting %s (%d segments)",
            meeting_id,
            len(segments),
        )
        ref_date = meeting_date or datetime.now(UTC)

        all_raw_entities: list[ExtractedEntity] = []
        classes_map: dict[str, list[UtteranceClass]] = {}
        temporals_map: dict[str, list[NormalizedTemporal]] = {}
        classifications_list: list[UtteranceClassificationItem] = []
        all_relations: list[ExtractedRelation] = []
        all_temporals: list[NormalizedTemporal] = []
        evidence_items: list[EvidenceItem] = []
        entities_by_segment: dict[str, list[ExtractedEntity]] = {}

        # 1. Segment-level extraction (NER, Classification, Temporal, Relations)
        for seg in segments:
            seg_id = seg.segment_id or f"seg-{uuid4()}"
            text = seg.text

            # NER
            seg_entities = await self.ner.extract_entities(text, segment_id=seg_id)
            all_raw_entities.extend(seg_entities)
            entities_by_segment[seg_id] = seg_entities

            # Utterance Classification
            classes = await self.classifier.classify_utterance(text, segment_id=seg_id)
            classes_map[seg_id] = classes
            classifications_list.append(
                UtteranceClassificationItem(segment_id=seg_id, classes=classes)
            )

            # Temporal Extraction
            temporals = await self.temporal.normalize_time(
                text, reference_date=ref_date, segment_id=seg_id
            )
            temporals_map[seg_id] = temporals
            all_temporals.extend(temporals)

            # Relation Extraction
            relations = await self.relation_extractor.extract_relations(
                segment=seg,
                entities=seg_entities,
                meeting_id=meeting_id,
            )
            all_relations.extend(relations)

            # Build evidence item
            evidence_items.append(
                EvidenceItem(
                    meeting_id=meeting_id,
                    segment_id=seg_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text_snapshot=text,
                )
            )

        # 2. Event Extraction across segments
        all_events = await self.event_extractor.extract_events(
            segments=segments,
            meeting_id=meeting_id,
            meeting_date=ref_date,
            entities_by_segment=entities_by_segment,
        )

        # 3. Coreference resolution across segments
        _resolved_segments = await self.coref.resolve(segments)

        # 4. Entity Resolution & Canonicalization
        resolved_entities = self.entity_resolver.resolve_entities_in_list(all_raw_entities)
        unique_entities: list[ExtractedEntity] = []
        seen_entity_ids = set()
        for ent in resolved_entities:
            if ent.entity_id not in seen_entity_ids:
                seen_entity_ids.add(ent.entity_id)
                unique_entities.append(ent)

        # 5. Fact Extraction (Decisions, Commitments/Actions, Issues, Topics)
        decisions = FactExtractors.extract_decisions(segments, classes_map, meeting_id=meeting_id)
        commitments = FactExtractors.extract_commitments_and_actions(
            segments, classes_map, temporals_map, meeting_id=meeting_id
        )
        issues = FactExtractors.extract_issues(
            segments, classes_map, meeting_date=ref_date, meeting_id=meeting_id
        )
        topics = FactExtractors.extract_topics(segments, unique_entities)

        result = NLPExtractionResult(
            meeting_id=meeting_id,
            entities=unique_entities,
            topics=topics,
            decisions=decisions,
            actions=commitments,
            commitments=commitments,
            issues=issues,
            events=all_events,
            relations=all_relations,
            temporal_expressions=all_temporals,
            classifications=classifications_list,
            evidence=evidence_items,
        )

        logger.info(
            "NLP extraction complete for %s: %d entities, %d topics, %d decisions, %d commitments, %d issues, %d events, %d relations",
            meeting_id,
            len(unique_entities),
            len(topics),
            len(decisions),
            len(commitments),
            len(issues),
            len(all_events),
            len(all_relations),
        )
        return result
