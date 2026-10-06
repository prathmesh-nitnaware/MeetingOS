from abc import ABC, abstractmethod
from typing import Any

from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext


class BaseReasoner(ABC):
    """Abstract provider interface for Evidence-Grounded Reasoning and QA."""

    @abstractmethod
    async def reason(
        self,
        question: str,
        evidence: list[EvidenceItem],
        context: ReasoningContext | None = None,
        **kwargs: Any,
    ) -> AnswerWithAttribution:
        """Produce an evidence-backed answer based strictly on retrieved facts and evidence."""
        ...
