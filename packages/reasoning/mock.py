from typing import Any

from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext
from packages.reasoning.interfaces import BaseReasoner


class MockReasoner(BaseReasoner):
    """Deterministic Mock Reasoner producing grounded answers with citations."""

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

        # Build deterministic synthesis from evidence
        evidence_texts = " ".join(e.text_snapshot for e in evidence)
        lowered_q = question.lower()

        if "database" in lowered_q or "postgres" in lowered_q or "mongodb" in lowered_q:
            answer = (
                "Based on the meeting records, the team evaluated MongoDB and PostgreSQL, and decided "
                "to adopt PostgreSQL with pgvector as the official database."
            )
        elif "rahul" in lowered_q or "schema" in lowered_q or "friday" in lowered_q:
            answer = "Rahul Verma committed to finishing the database schema by Friday as agreed during the meeting."
        else:
            answer = f"According to the retrieved evidence: {evidence_texts[:200]}..."

        return AnswerWithAttribution(
            question=question,
            answer=answer,
            evidence=list(evidence),
            confidence=0.95,
            reasoning_path=[
                f"Retrieved {len(evidence)} evidence segments.",
                "Grounded factual claims in source timestamps.",
            ],
        )
