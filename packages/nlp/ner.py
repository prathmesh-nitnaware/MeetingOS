import re

from packages.common.enums import EntityType
from packages.common.models import ExtractedEntity
from packages.nlp.interfaces import BaseNER


class RuleBasedNER(BaseNER):
    """Rule-based and dictionary-assisted Named Entity Recognizer for meeting transcripts."""

    DEFAULT_KNOWN_ENTITIES: list[tuple[str, str, EntityType]] = [
        # Persons
        ("rahul verma", "Rahul Verma", EntityType.PERSON),
        ("rahul", "Rahul Verma", EntityType.PERSON),
        ("priya sharma", "Priya Sharma", EntityType.PERSON),
        ("priya", "Priya Sharma", EntityType.PERSON),
        ("sarah chen", "Sarah Chen", EntityType.PERSON),
        ("sarah", "Sarah Chen", EntityType.PERSON),
        ("alex rivera", "Alex Rivera", EntityType.PERSON),
        ("alex", "Alex Rivera", EntityType.PERSON),
        # Technologies
        ("postgresql", "PostgreSQL", EntityType.TECHNOLOGY),
        ("postgres", "PostgreSQL", EntityType.TECHNOLOGY),
        ("pgvector", "pgvector", EntityType.TECHNOLOGY),
        ("mongodb", "MongoDB", EntityType.TECHNOLOGY),
        ("redis", "Redis", EntityType.TECHNOLOGY),
        ("celery", "Celery", EntityType.TECHNOLOGY),
        ("fastapi", "FastAPI", EntityType.TECHNOLOGY),
        ("pydantic", "Pydantic", EntityType.TECHNOLOGY),
        ("sqlalchemy", "SQLAlchemy", EntityType.TECHNOLOGY),
        ("whisper", "Whisper", EntityType.TECHNOLOGY),
        ("faster-whisper", "faster-whisper", EntityType.TECHNOLOGY),
        ("docker", "Docker", EntityType.TECHNOLOGY),
        # Projects
        ("meetingos", "MeetingOS", EntityType.PROJECT),
        ("api gateway", "API Gateway", EntityType.PROJECT),
        ("auth service", "Auth Service", EntityType.PROJECT),
        # Organizations
        ("deepmind", "DeepMind", EntityType.ORGANIZATION),
        ("google", "Google", EntityType.ORGANIZATION),
        ("openai", "OpenAI", EntityType.ORGANIZATION),
        ("anthropic", "Anthropic", EntityType.ORGANIZATION),
        # Locations
        ("conference room b", "Conference Room B", EntityType.LOCATION),
        ("london", "London", EntityType.LOCATION),
        ("san francisco", "San Francisco", EntityType.LOCATION),
    ]

    DATE_PATTERNS = [
        re.compile(
            r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
        ),
        re.compile(r"\b(today|tomorrow|yesterday|next week|end of the week)\b", re.IGNORECASE),
        re.compile(
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    ]

    def __init__(self, custom_entities: list[tuple[str, str, EntityType]] | None = None) -> None:
        self.known_entities = list(custom_entities or self.DEFAULT_KNOWN_ENTITIES)
        # Sort by trigger length descending so longest matches take precedence
        self.known_entities.sort(key=lambda x: len(x[0]), reverse=True)

    async def extract_entities(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: object,
    ) -> list[ExtractedEntity]:
        _ = kwargs
        entities: list[ExtractedEntity] = []
        lowered = text.lower()
        matched_spans: list[tuple[int, int]] = []

        # 1. Match known dictionary entities
        for trigger, canonical, ent_type in self.known_entities:
            # Word boundary regex for clean match
            pattern = re.compile(rf"\b{re.escape(trigger)}\b", re.IGNORECASE)
            for m in pattern.finditer(lowered):
                start, end = m.start(), m.end()
                # Check for overlap
                if any(start < s_end and end > s_start for s_start, s_end in matched_spans):
                    continue

                matched_spans.append((start, end))
                entities.append(
                    ExtractedEntity(
                        entity_id=f"ent-{canonical.lower().replace(' ', '-')}",
                        name=canonical,
                        entity_type=ent_type,
                        start_char=start,
                        end_char=end,
                        segment_id=segment_id,
                        confidence=0.95,
                    )
                )

        # 2. Match dates
        for d_pat in self.DATE_PATTERNS:
            for m in d_pat.finditer(text):
                start, end = m.start(), m.end()
                if any(start < s_end and end > s_start for s_start, s_end in matched_spans):
                    continue
                matched_spans.append((start, end))
                entities.append(
                    ExtractedEntity(
                        entity_id=f"ent-date-{start}",
                        name=m.group(0),
                        entity_type=EntityType.DATE,
                        start_char=start,
                        end_char=end,
                        segment_id=segment_id,
                        confidence=0.90,
                    )
                )

        # Sort by start_char
        entities.sort(key=lambda e: e.start_char or 0)
        return entities
