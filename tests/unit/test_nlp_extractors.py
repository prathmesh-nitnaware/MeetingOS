from datetime import UTC, datetime

import pytest
from packages.common.enums import EntityType, EventType, RelationType, UtteranceClass
from packages.common.models import TranscriptSegment
from packages.nlp.classifier import RuleBasedClassifier
from packages.nlp.coref import RuleBasedCoreferenceResolver
from packages.nlp.entity_resolution import EntityResolver
from packages.nlp.events import RuleBasedEventExtractor
from packages.nlp.ner import RuleBasedNER
from packages.nlp.relations import RuleBasedRelationExtractor
from packages.nlp.temporal import RuleBasedTemporalExtractor


@pytest.mark.asyncio
async def test_rule_based_ner():
    ner = RuleBasedNER()
    text = "Rahul Verma and Priya Sharma decided to use PostgreSQL and pgvector by Friday."
    entities = await ner.extract_entities(text, segment_id="seg-1")

    names = {e.name for e in entities}
    assert "Rahul Verma" in names
    assert "Priya Sharma" in names
    assert "PostgreSQL" in names
    assert "pgvector" in names
    assert "Friday" in names

    types = {e.entity_type for e in entities}
    assert EntityType.PERSON in types
    assert EntityType.TECHNOLOGY in types
    assert EntityType.DATE in types


@pytest.mark.asyncio
async def test_rule_based_classifier():
    classifier = RuleBasedClassifier()

    dec_classes = await classifier.classify_utterance("We decided to migrate to Postgres.")
    assert UtteranceClass.DECISION in dec_classes

    act_classes = await classifier.classify_utterance("I will finish the test suite tomorrow.")
    assert UtteranceClass.COMMITMENT in act_classes

    prob_classes = await classifier.classify_utterance("We hit a timeout issue in Redis.")
    assert UtteranceClass.PROBLEM in prob_classes

    q_classes = await classifier.classify_utterance("What is our target latency?")
    assert UtteranceClass.QUESTION in q_classes


@pytest.mark.asyncio
async def test_rule_based_temporal_extractor():
    extractor = RuleBasedTemporalExtractor()
    ref_date = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)  # Tuesday

    results = await extractor.normalize_time(
        "Let us ship tomorrow and review by Friday.", reference_date=ref_date
    )
    assert len(results) >= 2
    raw_expressions = [r.text for r in results]
    assert any("tomorrow" in expr for expr in raw_expressions)
    assert any("friday" in expr for expr in raw_expressions)


@pytest.mark.asyncio
async def test_rule_based_relations():
    ner = RuleBasedNER()
    extractor = RuleBasedRelationExtractor()
    segment = TranscriptSegment(
        segment_id="seg-1",
        sequence=0,
        speaker_id="spk_0",
        start_time=0.0,
        end_time=5.0,
        text="Rahul will implement PostgreSQL by Friday.",
    )
    entities = await ner.extract_entities(segment.text)

    relations = await extractor.extract_relations(segment, entities, meeting_id="meet-1")
    assert len(relations) >= 1
    rel_types = {r.relationship_type for r in relations}
    assert (
        RelationType.ASSIGNED_TO in rel_types
        or RelationType.WORKS_ON in rel_types
        or RelationType.HAS_DEADLINE in rel_types
    )


@pytest.mark.asyncio
async def test_rule_based_events():
    ner = RuleBasedNER()
    extractor = RuleBasedEventExtractor()
    dt = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)

    seg1 = TranscriptSegment(
        segment_id="seg-1",
        sequence=0,
        speaker_id="spk_0",
        start_time=0.0,
        end_time=5.0,
        text="We decided to adopt PostgreSQL.",
    )
    ent1 = await ner.extract_entities(seg1.text)
    evts1 = await extractor.extract_events(
        [seg1],
        meeting_id="meet-1",
        meeting_date=dt,
        entities_by_segment={"seg-1": ent1},
    )
    assert any(e.event_type == EventType.DECISION_APPROVED for e in evts1)

    seg2 = TranscriptSegment(
        segment_id="seg-2",
        sequence=1,
        speaker_id="spk_0",
        start_time=5.0,
        end_time=10.0,
        text="We found an issue with connection limits.",
    )
    ent2 = await ner.extract_entities(seg2.text)
    evts2 = await extractor.extract_events(
        [seg2],
        meeting_id="meet-1",
        meeting_date=dt,
        entities_by_segment={"seg-2": ent2},
    )
    assert any(e.event_type == EventType.ISSUE_DETECTED for e in evts2)


@pytest.mark.asyncio
async def test_coreference_resolver():
    resolver = RuleBasedCoreferenceResolver()
    segments = [
        TranscriptSegment(
            segment_id="seg-1",
            sequence=0,
            speaker_id="spk_0",
            start_time=0.0,
            end_time=5.0,
            text="Rahul built the API. He deployed it successfully.",
        )
    ]
    resolved = await resolver.resolve(segments)
    assert len(resolved) == 1
    assert "Rahul" in resolved[0].text


def test_entity_resolver():
    resolver = EntityResolver()
    res1 = resolver.resolve("Postgres")
    assert res1.entity_id == "ent-postgresql"
    assert res1.name == "PostgreSQL"
    assert res1.entity_type == EntityType.TECHNOLOGY

    res2 = resolver.resolve("Rahul")
    assert res2.entity_id == "ent-rahul-verma"
    assert res2.name == "Rahul Verma"
    assert res2.entity_type == EntityType.PERSON
