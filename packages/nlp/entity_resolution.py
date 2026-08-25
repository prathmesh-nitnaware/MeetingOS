from packages.common.enums import EntityType
from packages.common.models import ExtractedEntity


class EntityResolver:
    """Canonical entity resolver matching surface mentions to canonical entity IDs and names."""

    CANONICAL_DIRECTORY: dict[str, tuple[str, str, EntityType, list[str]]] = {
        # (id, canonical_name, entity_type, aliases)
        "ent-rahul-verma": (
            "ent-rahul-verma",
            "Rahul Verma",
            EntityType.PERSON,
            ["Rahul", "Rahul V", "R. Verma"],
        ),
        "ent-priya-sharma": (
            "ent-priya-sharma",
            "Priya Sharma",
            EntityType.PERSON,
            ["Priya", "Priya S", "P. Sharma"],
        ),
        "ent-sarah-chen": (
            "ent-sarah-chen",
            "Sarah Chen",
            EntityType.PERSON,
            ["Sarah", "Sarah C", "S. Chen"],
        ),
        "ent-alex-rivera": (
            "ent-alex-rivera",
            "Alex Rivera",
            EntityType.PERSON,
            ["Alex", "Alex R", "A. Rivera"],
        ),
        "ent-postgresql": (
            "ent-postgresql",
            "PostgreSQL",
            EntityType.TECHNOLOGY,
            ["Postgres", "PostgreSQL DB", "pg"],
        ),
        "ent-pgvector": (
            "ent-pgvector",
            "pgvector",
            EntityType.TECHNOLOGY,
            ["pgvector extension", "vector extension"],
        ),
        "ent-redis": (
            "ent-redis",
            "Redis",
            EntityType.TECHNOLOGY,
            ["Redis cache", "Redis queue"],
        ),
        "ent-celery": (
            "ent-celery",
            "Celery",
            EntityType.TECHNOLOGY,
            ["Celery worker", "Celery tasks"],
        ),
        "ent-fastapi": (
            "ent-fastapi",
            "FastAPI",
            EntityType.TECHNOLOGY,
            ["FastAPI framework", "FastAPI app"],
        ),
        "ent-pydantic": (
            "ent-pydantic",
            "Pydantic",
            EntityType.TECHNOLOGY,
            ["Pydantic v2", "Pydantic models"],
        ),
        "ent-meetingos": (
            "ent-meetingos",
            "MeetingOS",
            EntityType.PROJECT,
            ["Meeting OS", "MeetingOS project"],
        ),
    }

    def __init__(self) -> None:
        self.lookup: dict[str, tuple[str, str, EntityType]] = {}
        for canonical_id, canonical_name, ent_type, aliases in self.CANONICAL_DIRECTORY.values():
            self.lookup[canonical_name.lower()] = (canonical_id, canonical_name, ent_type)
            for alias in aliases:
                self.lookup[alias.lower()] = (canonical_id, canonical_name, ent_type)

    def resolve(
        self, surface_form: str, default_type: EntityType = EntityType.PROJECT
    ) -> ExtractedEntity:
        """Resolve a raw surface mention to a canonical ExtractedEntity."""
        clean = surface_form.strip()
        lowered = clean.lower()

        if lowered in self.lookup:
            can_id, can_name, ent_type = self.lookup[lowered]
            return ExtractedEntity(
                entity_id=can_id,
                name=can_name,
                entity_type=ent_type,
                confidence=0.98,
            )

        # Fallback generated canonical ID
        generated_id = f"ent-{lowered.replace(' ', '-')}"
        return ExtractedEntity(
            entity_id=generated_id,
            name=clean,
            entity_type=default_type,
            confidence=0.75,
        )

    def resolve_entities_in_list(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Normalize a list of extracted entities."""
        resolved: list[ExtractedEntity] = []
        for ent in entities:
            res = self.resolve(ent.name, default_type=ent.entity_type)
            resolved.append(
                ExtractedEntity(
                    entity_id=res.entity_id,
                    name=res.name,
                    entity_type=res.entity_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    segment_id=ent.segment_id,
                    confidence=max(ent.confidence, res.confidence),
                )
            )
        return resolved
