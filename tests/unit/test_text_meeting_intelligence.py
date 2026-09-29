import pytest
from datetime import UTC, datetime
from packages.common.enums import CommitmentStatus, DecisionStatus
from packages.nlp.text_analyzer import analyze_text_intelligence, parse_text_to_segments


def test_parse_text_to_segments_transcript():
    content = """Alice: We need to finalize the API architecture this week.
Bob: I can handle the authentication module.
Charlie: We should move the deployment to Friday.
Alice: Agreed. Let's target Friday."""
    segments, speakers = parse_text_to_segments(content, content_type="transcript")
    assert len(segments) == 4
    assert segments[0].speaker_id == "spk_alice"
    assert "Alice: We need to finalize" in segments[0].text
    assert len(speakers) == 3


def test_parse_text_to_segments_notes():
    content = """- Discussed API architecture
- Bob will handle authentication
- Deployment moved to Friday
- Need final testing before release"""
    segments, speakers = parse_text_to_segments(content, content_type="notes")
    assert len(segments) == 4
    assert any("Bob" in s.text for s in segments)


def test_analyze_text_intelligence_no_hallucinations():
    content = """Alex: We need to finalize the launch plan by the end of this week.
Sarah: The product is ready from the design side. We still need to finish the onboarding flow.
David: Engineering can complete the onboarding work by Thursday.
Maya: Then let's target Friday for the internal release.
Alex: Agreed. We'll use Friday as the internal release target."""

    analysis = analyze_text_intelligence(
        title="Product Launch Kickoff",
        content=content,
        meeting_date=datetime.now(UTC),
    )

    assert analysis.summary != ""
    assert len(analysis.decisions) >= 1
    assert any("Friday" in d.subject for d in analysis.decisions)
    assert len(analysis.action_items) >= 1
    assert any("David" in a.owner_id or "onboarding" in a.task.lower() for a in analysis.action_items)
    assert len(analysis.topics) >= 1
    assert any("Launch" in t or "Release" in t or "API" in t or "Onboarding" in t for t in analysis.topics)


def test_action_item_unassigned_when_no_owner():
    content = """- Need to update documentation before launch
- Deployment scheduled for Friday"""
    analysis = analyze_text_intelligence(
        title="General Sync",
        content=content,
    )
    # Check that owner is Unassigned when not specified
    for act in analysis.action_items:
        if "update documentation" in act.description.lower():
            assert act.owner_id == "Unassigned"
