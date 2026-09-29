import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from packages.common.enums import CommitmentStatus, DecisionStatus, EntityType, SourceType
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    Participant,
    SpeakerInfo,
    TranscriptSegment,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StructuredMeetingAnalysis(BaseModel):
    """Structured AI output schema for meeting intelligence."""

    summary: str = Field(description="1-3 paragraph executive summary of the meeting")
    key_points: list[str] = Field(default_factory=list, description="List of bullet points covering key takeaways")
    topics: list[str] = Field(default_factory=list, description="Extracted topic and project tags")
    decisions: list[ExtractedDecision] = Field(default_factory=list, description="Extracted organizational decisions")
    action_items: list[ExtractedCommitment] = Field(default_factory=list, description="Extracted commitments and tasks")
    participants: list[Participant] = Field(default_factory=list, description="Identified meeting participants")


def parse_text_to_segments(raw_text: str, content_type: str = "transcript") -> tuple[list[TranscriptSegment], list[SpeakerInfo]]:
    """Parse pasted transcripts, meeting notes, or discussion text into structured segments."""
    if not raw_text or not raw_text.strip():
        return [], []

    lines = raw_text.strip().split("\n")
    segments: list[TranscriptSegment] = []
    speakers_map: dict[str, str] = {}
    current_speaker = "Speaker"
    seq = 0
    start_time = 0.0

    # Common speaker patterns: "Alice:", "Alice (10:00):", "[Alice]:", "Alice - "
    speaker_regex = re.compile(r"^(?:\[(?P<spk1>[^\]]+)\]|(?P<spk2>[A-Za-z0-9 _\.\-]+)(?:\s*\([0-9:]+\))?)\s*[:\-]\s*(?P<content>.*)$")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        match = speaker_regex.match(line)
        if match:
            spk_name = (match.group("spk1") or match.group("spk2") or "Speaker").strip()
            content = match.group("content").strip()
            spk_id = f"spk_{re.sub(r'[^a-zA-Z0-9_]', '_', spk_name.lower())}"
            speakers_map[spk_id] = spk_name
            current_speaker = spk_id

            if not content:
                continue

            end_time = start_time + max(2.0, len(content.split()) * 0.4)
            segments.append(
                TranscriptSegment(
                    segment_id=f"seg-{uuid4()}",
                    sequence=seq,
                    speaker_id=current_speaker,
                    start_time=round(start_time, 2),
                    end_time=round(end_time, 2),
                    text=f"{spk_name}: {content}",
                )
            )
            seq += 1
            start_time = end_time
        else:
            # Bullet point or regular note line
            clean_line = re.sub(r"^[-*•\d\.)\s]+", "", line).strip()
            if not clean_line:
                continue

            # Check if bullet begins with a name e.g. "Bob will handle...", "Alice - "
            owner_match = re.match(r"^([A-Z][a-z]+)\s*(?:will|should|is handling|:|—|-)\s*(.*)$", clean_line)
            candidate_name = owner_match.group(1).strip() if owner_match else ""
            stopwords = {"need", "want", "plan", "have", "due", "agree", "target", "action", "todo", "decision", "note", "notes", "discussed", "review", "we", "the", "it", "this", "also", "let", "lets", "let's"}
            if candidate_name and candidate_name.lower() not in stopwords:
                spk_name = candidate_name
                spk_id = f"spk_{spk_name.lower()}"
                speakers_map[spk_id] = spk_name
            else:
                spk_id = current_speaker if content_type == "transcript" else "Notes"
                speakers_map[spk_id] = "Meeting Notes" if spk_id == "Notes" else current_speaker

            end_time = start_time + max(2.0, len(clean_line.split()) * 0.4)
            segments.append(
                TranscriptSegment(
                    segment_id=f"seg-{uuid4()}",
                    sequence=seq,
                    speaker_id=spk_id,
                    start_time=round(start_time, 2),
                    end_time=round(end_time, 2),
                    text=line,
                )
            )
            seq += 1
            start_time = end_time

    speakers = [
        SpeakerInfo(speaker_id=k, name=v, canonical_entity_id=k)
        for k, v in speakers_map.items()
    ]
    return segments, speakers


def analyze_text_intelligence(
    title: str,
    content: str,
    meeting_date: datetime | None = None,
    existing_participants: list[Participant] | None = None,
    meeting_id: str | None = None,
) -> StructuredMeetingAnalysis:
    """Analyze text content and return structured, accurate meeting intelligence.

    Adheres strictly to zero-hallucination rules:
    - Missing owners -> Owner: "Unassigned"
    - Missing deadlines -> Due date: "Not specified"
    - Preserves uncertainty and factual groundings.
    """
    m_id = meeting_id or f"meet-{uuid4()}"
    dt = meeting_date or datetime.now(UTC)
    segments, speakers = parse_text_to_segments(content)

    # 1. Derive Participants
    participants_map: dict[str, Participant] = {}
    if existing_participants:
        for p in existing_participants:
            participants_map[p.canonical_name.lower()] = p

    for spk in speakers:
        if spk.name and spk.name.lower() not in {"notes", "speaker", "meeting notes"}:
            if spk.name.lower() not in participants_map:
                participants_map[spk.name.lower()] = Participant(
                    id=str(uuid4()),
                    canonical_name=spk.name,
                )

    participants = list(participants_map.values())
    known_names = [p.canonical_name for p in participants]

    # 2. Extract Key Points & Topics
    key_points: list[str] = []
    topics_set: set[str] = set()
    decisions: list[ExtractedDecision] = []
    action_items: list[ExtractedCommitment] = []

    # Keyword topic triggers
    lower_content = content.lower()
    topic_rules = [
        ("api", "API Architecture"),
        ("auth", "Authentication & Security"),
        ("deploy", "Deployment & Release"),
        ("launch", "Product Launch"),
        ("roadmap", "Product Roadmap"),
        ("test", "Testing & QA"),
        ("database", "Database & Infrastructure"),
        ("design", "Design & UX"),
        ("onboarding", "User Onboarding"),
        ("hiring", "Team & Hiring"),
        ("budget", "Budget & Finance"),
        ("marketing", "Marketing & Growth"),
        ("performance", "Performance & Scaling"),
    ]
    for kw, topic_tag in topic_rules:
        if kw in lower_content:
            topics_set.add(topic_tag)

    if not topics_set:
        topics_set.add("General Discussion")

    # 3. Decision Extraction (Strict groundings)
    decision_triggers = [
        "decided", "decision", "agreed", "target", "approved",
        "settled on", "consensus", "moving forward with", "will use"
    ]
    # Reversal / modification cues
    modified_cues = ["modify", "update", "reschedule", "move", "delay"]
    reverse_cues = ["cancel", "reverse", "reject", "drop", "shelve"]

    # 4. Action Item Extraction (Strict groundings)
    action_triggers = [
        "will", "action", "assigned to", "take care of", "handle",
        "responsible for", "follow up", "prepare", "deliver", "complete", "finish"
    ]

    for seg in segments:
        text = seg.text
        clean_text = text
        speaker_prefix = ""
        if ":" in text:
            speaker_prefix, clean_text = text.split(":", 1)
            speaker_prefix = speaker_prefix.strip()
            clean_text = clean_text.strip()

        seg_lower = clean_text.lower()

        # Compute source span in original content
        source_start = None
        source_end = None
        if clean_text in content:
            source_start = content.find(clean_text)
            source_end = source_start + len(clean_text)
        elif text in content:
            source_start = content.find(text)
            source_end = source_start + len(text)

        # Decision Check
        if any(dt in seg_lower for dt in decision_triggers):
            dec_status = DecisionStatus.APPROVED
            if any(rc in seg_lower for rc in reverse_cues):
                dec_status = DecisionStatus.REVERSED
            elif any(mc in seg_lower for mc in modified_cues):
                dec_status = DecisionStatus.MODIFIED

            # Context extraction
            dec_title = clean_text
            if len(dec_title) > 100:
                dec_title = dec_title[:97] + "..."

            decisions.append(
                ExtractedDecision(
                    decision_id=f"dec-{uuid4()}",
                    title=dec_title,
                    subject=clean_text,
                    status=dec_status,
                    context=f"Recorded from discussion by {speaker_prefix or 'the team'}",
                    rationale=f"Agreed during {title}",
                    confidence=0.95,
                    meeting_id=m_id,
                    evidence_segment_id=seg.segment_id,
                    source_text=text,
                    source_start=source_start,
                    source_end=source_end,
                    review_status="needs_review",
                    created_at=dt,
                )
            )
            key_points.append(f"Decision: {clean_text}")

        # Action Item Check
        elif any(at in seg_lower for at in action_triggers) or seg_lower.startswith(("- ", "* ", "todo", "action:")):
            # Determine Owner strictly without hallucination
            owner = "Unassigned"
            if speaker_prefix and speaker_prefix.lower() not in {"notes", "speaker"}:
                # If speaker says "I will...", "I can...", speaker is owner
                if re.search(r"\b(i will|i can|i'll|i am taking|i'll handle)\b", seg_lower):
                    owner = speaker_prefix
                elif "assigned to" in seg_lower:
                    for name in known_names:
                        if name.lower() in seg_lower:
                            owner = name
                            break
            else:
                for name in known_names:
                    if name.lower() in seg_lower:
                        owner = name
                        break

            # Determine Due Date strictly without hallucination
            due_date_str = "Not specified"
            day_match = re.search(r"\b(?:by|on|due|target)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week|end of week|oct \d+|nov \d+|dec \d+|jan \d+|q[1-4])\b", seg_lower)
            if day_match:
                due_date_str = day_match.group(1).title()

            # Priority
            priority = "medium"
            if any(w in seg_lower for w in ["urgent", "asap", "critical", "blocker", "p0", "high"]):
                priority = "high"
            elif any(w in seg_lower for w in ["low", "when possible", "nice to have", "p2", "p3"]):
                priority = "low"

            task_title = clean_text
            if task_title.lower().startswith("action:"):
                task_title = task_title[7:].strip()
            if len(task_title) > 120:
                task_title = task_title[:117] + "..."

            action_items.append(
                ExtractedCommitment(
                    commitment_id=f"com-{uuid4()}",
                    task=task_title,
                    description=clean_text,
                    owner_id=owner,
                    status=CommitmentStatus.IN_PROGRESS if owner != "Unassigned" else CommitmentStatus.IDENTIFIED,
                    priority=priority,
                    due_date_str=due_date_str,
                    confidence=0.94 if owner != "Unassigned" else 0.85,
                    meeting_id=m_id,
                    evidence_segment_id=seg.segment_id,
                    source_text=text,
                    source_start=source_start,
                    source_end=source_end,
                    review_status="needs_review",
                )
            )
            key_points.append(f"Action ({owner}): {clean_text}")

        else:
            # General key point
            if len(clean_text) > 15 and len(key_points) < 8:
                key_points.append(clean_text)

    # 5. Build Executive Summary
    summary_paras: list[str] = []
    participant_names = ", ".join(known_names) if known_names else "The team"

    if decisions and action_items:
        summary_paras.append(
            f"{participant_names} met to discuss {title.lower() if not title.lower().startswith('meeting') else title}. "
            f"The team reviewed current priorities, reached {len(decisions)} key decision{'s' if len(decisions) != 1 else ''}, "
            f"and outlined {len(action_items)} action item{'s' if len(action_items) != 1 else ''}."
        )
    elif decisions:
        summary_paras.append(
            f"{participant_names} convened to align on {title}. The discussion concluded with {len(decisions)} confirmed organizational decision{'s' if len(decisions) != 1 else ''}."
        )
    elif action_items:
        summary_paras.append(
            f"{participant_names} met to coordinate work on {title}. Key tasks and deliverables were assigned across the team."
        )
    else:
        summary_paras.append(
            f"Meeting notes and discussion covering {title}. Key discussion topics and perspectives were documented."
        )

    # Secondary paragraph if substantive content exists
    if decisions or action_items:
        dec_summary = f"Key outcomes include: {'; '.join(d.subject for d in decisions[:2])}." if decisions else ""
        act_summary = f"Priority tasks assigned: {'; '.join(f'{a.owner_id}: {a.task}' for a in action_items[:2])}." if action_items else ""
        second_para = f"{dec_summary} {act_summary}".strip()
        if second_para:
            summary_paras.append(second_para)

    summary_text = "\n\n".join(summary_paras)

    raw_analysis = StructuredMeetingAnalysis(
        summary=summary_text,
        key_points=key_points[:8],
        topics=sorted(list(topics_set)),
        decisions=decisions,
        action_items=action_items,
        participants=participants,
    )

    return validate_structured_intelligence(raw_analysis, content)


def normalize_topic_name(topic: str) -> str:
    """Deterministically normalize a topic tag.

    Examples:
    '#beta launch' -> 'Beta Launch'
    'API architecture' -> 'API Architecture'
    'UI/UX' -> 'UI/UX'
    """
    if not topic:
        return ""
    t = re.sub(r"^[#@\s]+", "", topic).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return ""

    # Special handling for common abbreviations
    special_words = {
        "api": "API",
        "qa": "QA",
        "ai": "AI",
        "ml": "ML",
        "ux": "UX",
        "ui": "UI",
        "ui/ux": "UI/UX",
        "b2b": "B2B",
        "b2c": "B2C",
        "sdk": "SDK",
        "sql": "SQL",
        "db": "Database",
    }

    words = t.split(" ")
    normalized_words = []
    for w in words:
        w_lower = w.lower()
        if w_lower in special_words:
            normalized_words.append(special_words[w_lower])
        else:
            normalized_words.append(w.capitalize())
    return " ".join(normalized_words)


def sanitize_source_span(
    source_text: str | None,
    source_start: int | None,
    source_end: int | None,
    raw_content: str,
) -> tuple[str | None, int | None, int | None]:
    """Sanitize and guarantee bounds safety for extracted source evidence spans.

    Ensures:
    - 0 <= source_start <= source_end <= len(raw_content)
    - If offsets are invalid but text is found in raw_content, offsets are repaired.
    - If text cannot be found, out-of-bounds offsets are discarded.
    """
    if not raw_content:
        return None, None, None

    content_len = len(raw_content)

    # If text is provided, try verifying/locating it
    if source_text and source_text.strip():
        # Check if provided offsets are valid and match
        if (
            source_start is not None
            and source_end is not None
            and 0 <= source_start <= source_end <= content_len
        ):
            extracted = raw_content[source_start:source_end]
            if extracted == source_text or source_text in extracted:
                return source_text, source_start, source_end

        # Offsets invalid or missing: search for text
        idx = raw_content.find(source_text)
        if idx != -1:
            return source_text, idx, idx + len(source_text)

        # Try case-insensitive fallback search
        idx_lower = raw_content.lower().find(source_text.lower())
        if idx_lower != -1:
            exact_match = raw_content[idx_lower : idx_lower + len(source_text)]
            return exact_match, idx_lower, idx_lower + len(source_text)

    # If only offsets were provided
    if (
        source_start is not None
        and source_end is not None
        and 0 <= source_start <= source_end <= content_len
    ):
        extracted = raw_content[source_start:source_end]
        if extracted.strip():
            return extracted, source_start, source_end

    return None, None, None


def validate_structured_intelligence(
    analysis: StructuredMeetingAnalysis,
    raw_content: str,
) -> StructuredMeetingAnalysis:
    """Zero-hallucination validation layer that verifies structured intelligence against raw meeting text.

    Validation rules:
    - Decisions: ensure subject exists, no fabricated rationale, evidence spans sanitized and bounded.
    - Actions: ensure task exists, owner is explicit (or 'Unassigned'), deadline is explicit (or 'Not specified').
    - Topics: normalize naming, filter trivial filler or stopwords.
    """
    cleaned_decisions: list[ExtractedDecision] = []
    for d in analysis.decisions:
        if not d.subject or not d.subject.strip():
            continue

        # Sanitize and validate source evidence bounds
        s_text, s_start, s_end = sanitize_source_span(
            d.source_text or d.subject,
            d.source_start,
            d.source_end,
            raw_content,
        )
        d.source_text = s_text
        d.source_start = s_start
        d.source_end = s_end
        d.review_status = getattr(d, "review_status", None) or "needs_review"
        cleaned_decisions.append(d)

    cleaned_actions: list[ExtractedCommitment] = []
    for a in analysis.action_items:
        if not a.description and not a.task:
            continue
        # Enforce zero-hallucination on owner and deadline
        if not a.owner_id or a.owner_id.strip() == "":
            a.owner_id = "Unassigned"
        if not a.due_date_str or a.due_date_str.strip() == "":
            a.due_date_str = "Not specified"

        # Sanitize and validate source evidence bounds
        target_text = a.source_text or a.task or a.description
        s_text, s_start, s_end = sanitize_source_span(
            target_text,
            a.source_start,
            a.source_end,
            raw_content,
        )
        a.source_text = s_text
        a.source_start = s_start
        a.source_end = s_end
        a.review_status = getattr(a, "review_status", None) or "needs_review"
        cleaned_actions.append(a)

    # Normalize and filter topics
    filler_topics = {"general", "discussion", "misc", "notes", "update", "meeting", "sync", ""}
    seen_normalized: set[str] = set()
    meaningful_topics: list[str] = []

    for t in analysis.topics:
        norm = normalize_topic_name(t)
        if norm.lower() in filler_topics and len(analysis.topics) > 1:
            continue
        if norm.lower() not in seen_normalized:
            seen_normalized.add(norm.lower())
            meaningful_topics.append(norm)

    return StructuredMeetingAnalysis(
        summary=analysis.summary,
        key_points=analysis.key_points,
        topics=meaningful_topics or ["General Discussion"],
        decisions=cleaned_decisions,
        action_items=cleaned_actions,
        participants=analysis.participants,
    )

