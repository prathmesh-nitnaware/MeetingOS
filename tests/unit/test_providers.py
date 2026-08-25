from datetime import UTC, datetime

import pytest
from packages.common.enums import EntityType, EventType, RelationType, UtteranceClass
from packages.common.models import EvidenceItem, ExtractedEntity, TranscriptSegment
from packages.nlp.mock import (
    MockClassifier,
    MockCoreferenceResolver,
    MockEmbedder,
    MockEventExtractor,
    MockNER,
    MockRelationExtractor,
    MockTemporalExtractor,
)
from packages.reasoning.mock import MockReasoner
from packages.speech.mock import MockASR, MockDiarizer


@pytest.mark.asyncio
async def test_mock_asr():
    asr = MockASR()
    segments = await asr.transcribe("dummy_path.wav")
    assert len(segments) == 3
    assert segments[0].speaker_id == "spk_0"
    assert "MeetingOS" in segments[0].text
    assert segments[1].start_time == 6.0


@pytest.mark.asyncio
async def test_mock_diarizer():
    diarizer = MockDiarizer()
    speakers = await diarizer.diarize("dummy_path.wav")
    assert len(speakers) == 2
    assert speakers[0].speaker_id == "spk_0"
    assert speakers[0].name == "Priya Sharma"


@pytest.mark.asyncio
async def test_mock_ner():
    ner = MockNER()
    text = "Rahul and Priya discussed adopting PostgreSQL for MeetingOS by Friday."
    entities = await ner.extract_entities(text, segment_id="seg-1")
    assert len(entities) >= 4
    entity_names = {e.name: e.entity_type for e in entities}
    assert entity_names["Rahul Verma"] == EntityType.PERSON
    assert entity_names["Priya Sharma"] == EntityType.PERSON
    assert entity_names["PostgreSQL"] == EntityType.TECHNOLOGY
    assert entity_names["MeetingOS"] == EntityType.PROJECT


@pytest.mark.asyncio
async def test_mock_classifier():
    classifier = MockClassifier()
    decision_text = "We agreed to decide on adopting PostgreSQL."
    classes = await classifier.classify_utterance(decision_text)
    assert UtteranceClass.DECISION in classes

    action_text = "Rahul please finish the schema by Friday."
    classes = await classifier.classify_utterance(action_text)
    assert UtteranceClass.ACTION in classes

    question_text = "What database are we using?"
    classes = await classifier.classify_utterance(question_text)
    assert UtteranceClass.QUESTION in classes


@pytest.mark.asyncio
async def test_mock_relation_extractor():
    extractor = MockRelationExtractor()
    segment = TranscriptSegment(
        segment_id="s1",
        sequence=0,
        speaker_id="spk_0",
        start_time=0.0,
        end_time=5.0,
        text="Rahul will work on MeetingOS and PostgreSQL.",
    )
    entities = [
        ExtractedEntity(entity_id="ent-rahul", name="Rahul Verma", entity_type=EntityType.PERSON),
        ExtractedEntity(
            entity_id="ent-meetingos", name="MeetingOS", entity_type=EntityType.PROJECT
        ),
        ExtractedEntity(
            entity_id="ent-postgresql", name="PostgreSQL", entity_type=EntityType.TECHNOLOGY
        ),
    ]
    relations = await extractor.extract_relations(segment, entities, meeting_id="m1")
    assert len(relations) == 2
    rel_types = {r.relationship_type for r in relations}
    assert RelationType.WORKS_ON in rel_types
    assert RelationType.ASSIGNED_TO in rel_types


@pytest.mark.asyncio
async def test_mock_event_extractor():
    extractor = MockEventExtractor()
    segments = [
        TranscriptSegment(
            segment_id="s1",
            sequence=0,
            speaker_id="spk_0",
            start_time=0.0,
            end_time=5.0,
            text="We agreed to make PostgreSQL the official choice.",
        ),
        TranscriptSegment(
            segment_id="s2",
            sequence=1,
            speaker_id="spk_0",
            start_time=5.1,
            end_time=10.0,
            text="Rahul please finish the schema by Friday.",
        ),
    ]
    meeting_date = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)
    events = await extractor.extract_events(segments, meeting_id="m1", meeting_date=meeting_date)
    assert len(events) == 2
    event_types = {e.event_type for e in events}
    assert EventType.DECISION_APPROVED in event_types
    assert EventType.COMMITMENT_ASSIGNED in event_types


@pytest.mark.asyncio
async def test_mock_temporal_extractor():
    extractor = MockTemporalExtractor()
    ref_date = datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC)
    norm = await extractor.normalize_time(
        "We will finish tomorrow and review on Friday.", reference_date=ref_date
    )
    assert len(norm) == 2
    assert norm[0].text == "tomorrow"
    assert norm[0].normalized_date.day == 26


@pytest.mark.asyncio
async def test_mock_coreference_resolver():
    resolver = MockCoreferenceResolver()
    segments = [
        TranscriptSegment(
            segment_id="s1",
            sequence=0,
            speaker_id="spk_0",
            start_time=0.0,
            end_time=5.0,
            text="He will finish it.",
        )
    ]
    resolved = await resolver.resolve(segments)
    assert "Rahul Verma will finish the schema" in resolved[0].text


@pytest.mark.asyncio
async def test_mock_embedder():
    embedder = MockEmbedder(dimension=384)
    vectors = await embedder.embed(["Hello world", "PostgreSQL database"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384
    # Check deterministic consistency
    vectors_repeat = await embedder.embed(["Hello world"])
    assert vectors[0] == vectors_repeat[0]


@pytest.mark.asyncio
async def test_mock_reasoner():
    reasoner = MockReasoner()
    evidence = [
        EvidenceItem(
            meeting_id="m1",
            segment_id="s1",
            start_time=10.0,
            end_time=20.0,
            text_snapshot="We decided to adopt PostgreSQL with pgvector.",
        )
    ]
    answer = await reasoner.reason("What database did we choose?", evidence=evidence)
    assert "PostgreSQL with pgvector" in answer.answer
    assert len(answer.evidence) == 1
    assert answer.confidence == 0.95

    # Test empty evidence fallback
    empty_answer = await reasoner.reason("What is our budget?", evidence=[])
    assert "does not establish an answer" in empty_answer.answer
    assert empty_answer.confidence == 0.0
