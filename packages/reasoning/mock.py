from typing import Any

from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext
from packages.reasoning.interfaces import BaseReasoner


class MockReasoner(BaseReasoner):
    """Deterministic test reasoner that only quotes the retrieved evidence.

    It never states facts that are not in the evidence (earlier versions returned hard-coded
    answers such as "the team adopted PostgreSQL" for any question mentioning a database).
    """

    model_name = "mock-reasoner"

    async def reason(
        self,
        question: str,
        evidence: list[EvidenceItem],
        context: ReasoningContext | None = None,
        **kwargs: Any,
    ) -> AnswerWithAttribution:
        _ = (context, kwargs)
        if not evidence:
            return AnswerWithAttribution(
                question=question,
                answer="The available meeting memory does not establish an answer to this question.",
                evidence=[],
                confidence=0.0,
                reasoning_path=["No retrieved evidence segments matched the query criteria."],
            )

        quoted = " ".join(e.text_snapshot.strip() for e in evidence[:3])
        if len(quoted) > 300:
            quoted = quoted[:297].rstrip() + "..."
        return AnswerWithAttribution(
            question=question,
            answer=f"According to the retrieved evidence: {quoted}",
            evidence=list(evidence),
            confidence=0.95,
            reasoning_path=[
                f"Retrieved {len(evidence)} evidence segments.",
                "Quoted the evidence verbatim (mock reasoner).",
            ],
        )
