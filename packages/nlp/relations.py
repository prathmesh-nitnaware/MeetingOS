import re
from typing import Any
from uuid import uuid4

from packages.common.enums import EntityType, RelationType
from packages.common.models import ExtractedEntity, ExtractedRelation, TranscriptSegment
from packages.nlp.interfaces import BaseRelationExtractor


class RuleBasedRelationExtractor(BaseRelationExtractor):
    """Extracts typed relationships between entities in meeting segments."""

    async def extract_relations(
        self,
        segment: TranscriptSegment,
        entities: list[ExtractedEntity],
        meeting_id: str,
        **kwargs: Any,
    ) -> list[ExtractedRelation]:
        _ = kwargs
        relations: list[ExtractedRelation] = []
        text = segment.text
        lowered = text.lower()

        # Augment entity candidates with speaker entity if utterance has first-person commitment
        candidate_entities = list(entities)
        if segment.speaker_id and any(
            w in lowered for w in ["i will", "i'll", "i am working", "i'm working", "i commit"]
        ):
            speaker_name = segment.speaker_id.replace("spk_", "").replace("_", " ").title()
            cand_id = f"ent-{segment.speaker_id.replace('spk_', '').replace('_', '-')}"
            if not any(e.entity_id == cand_id for e in candidate_entities):
                candidate_entities.append(
                    ExtractedEntity(
                        entity_id=cand_id,
                        name=speaker_name,
                        entity_type=EntityType.PERSON,
                        confidence=0.90,
                    )
                )

        if len(candidate_entities) < 2:
            return relations

        # Find entity pairs
        for i in range(len(candidate_entities)):
            for j in range(len(candidate_entities)):
                if i == j:
                    continue
                e1 = candidate_entities[i]
                e2 = candidate_entities[j]

                # Check ASSIGNED_TO / WORKS_ON
                if e1.entity_type == EntityType.PERSON:
                    if any(
                        w in lowered
                        for w in [
                            "will implement",
                            "assigned to",
                            "working on",
                            "responsible for",
                            "will migrate",
                            "will finish",
                            "will do",
                            "owns",
                            "i will",
                            "i'll",
                        ]
                    ):
                        relations.append(
                            ExtractedRelation(
                                relation_id=f"rel-{uuid4()}",
                                source_entity_id=e1.entity_id,
                                target_entity_id=e2.entity_id,
                                relationship_type=RelationType.ASSIGNED_TO
                                if any(w in lowered for w in ["assigned", "will", "i will", "i'll"])
                                else RelationType.WORKS_ON,
                                meeting_id=meeting_id,
                                segment_id=segment.segment_id,
                                confidence=0.88,
                            )
                        )

                # Check REPLACES
                if re.search(
                    rf"\b{re.escape(e1.name.lower())}\b.*\b(replaces|migrate from|switch from|replacing)\b.*\b{re.escape(e2.name.lower())}\b",
                    lowered,
                ):
                    relations.append(
                        ExtractedRelation(
                            relation_id=f"rel-{uuid4()}",
                            source_entity_id=e1.entity_id,
                            target_entity_id=e2.entity_id,
                            relationship_type=RelationType.REPLACES,
                            meeting_id=meeting_id,
                            segment_id=segment.segment_id,
                            confidence=0.92,
                        )
                    )

                # Check HAS_DEADLINE
                if e2.entity_type == EntityType.DATE and any(
                    w in lowered for w in ["by", "deadline", "due", "finish"]
                ):
                    relations.append(
                        ExtractedRelation(
                            relation_id=f"rel-{uuid4()}",
                            source_entity_id=e1.entity_id,
                            target_entity_id=e2.entity_id,
                            relationship_type=RelationType.HAS_DEADLINE,
                            meeting_id=meeting_id,
                            segment_id=segment.segment_id,
                            confidence=0.90,
                        )
                    )

                # Check RELATED_TO / DECIDED_IN (e.g. Technology -> Project or Technology -> Technology)
                if e1.entity_type == EntityType.TECHNOLOGY and e2.entity_type in {
                    EntityType.PROJECT,
                    EntityType.TECHNOLOGY,
                }:
                    relations.append(
                        ExtractedRelation(
                            relation_id=f"rel-{uuid4()}",
                            source_entity_id=e1.entity_id,
                            target_entity_id=e2.entity_id,
                            relationship_type=RelationType.RELATED_TO,
                            meeting_id=meeting_id,
                            segment_id=segment.segment_id,
                            confidence=0.85,
                        )
                    )

        # Deduplicate relations
        unique_relations: list[ExtractedRelation] = []
        seen = set()
        for r in relations:
            key = (r.source_entity_id, r.target_entity_id, r.relationship_type)
            if key not in seen:
                seen.add(key)
                unique_relations.append(r)

        return unique_relations
