from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from packages.common.enums import UtteranceClass
from packages.common.models import (
    ExtractedEntity,
    ExtractedEvent,
    ExtractedRelation,
    NormalizedTemporal,
    TranscriptSegment,
)


class BaseNER(ABC):
    """Abstract provider interface for Named Entity Recognition."""

    @abstractmethod
    async def extract_entities(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[ExtractedEntity]:
        """Extract typed named entities from text."""
        ...


class BaseClassifier(ABC):
    """Abstract provider interface for Utterance Classification."""

    @abstractmethod
    async def classify_utterance(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[UtteranceClass]:
        """Classify semantic role(s) of an utterance."""
        ...


class BaseRelationExtractor(ABC):
    """Abstract provider interface for Relation Extraction."""

    @abstractmethod
    async def extract_relations(
        self,
        segment: TranscriptSegment,
        entities: list[ExtractedEntity],
        meeting_id: str,
        **kwargs: Any,
    ) -> list[ExtractedRelation]:
        """Extract typed relationships between entities in a transcript segment."""
        ...


class BaseEventExtractor(ABC):
    """Abstract provider interface for Event and Lifecycle Extraction."""

    @abstractmethod
    async def extract_events(
        self,
        segments: list[TranscriptSegment],
        meeting_id: str,
        meeting_date: datetime,
        **kwargs: Any,
    ) -> list[ExtractedEvent]:
        """Extract temporal and lifecycle change events from meeting transcript segments."""
        ...


class BaseTemporalExtractor(ABC):
    """Abstract provider interface for Temporal Normalization."""

    @abstractmethod
    async def normalize_time(
        self,
        text: str,
        reference_date: datetime,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedTemporal]:
        """Normalize relative time expressions relative to the reference meeting date."""
        ...


class BaseCoreferenceResolver(ABC):
    """Abstract provider interface for Coreference Resolution."""

    @abstractmethod
    async def resolve(
        self,
        segments: list[TranscriptSegment],
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        """Resolve pronouns and coreferences across transcript segments."""
        ...


class BaseEmbedder(ABC):
    """Abstract provider interface for Dense Vector Embeddings."""

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        """Generate dense vector embeddings for a list of text strings."""
        ...
