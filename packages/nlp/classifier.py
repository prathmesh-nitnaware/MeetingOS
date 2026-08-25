import re

from packages.common.enums import UtteranceClass
from packages.nlp.interfaces import BaseClassifier


class RuleBasedClassifier(BaseClassifier):
    """Rule-based multi-label Utterance Classifier for conversational meeting speech."""

    DECISION_PATTERNS = [
        re.compile(
            r"\b(we decided|let us decide|officially decide|agreed to|the decision is|we will adopt|approved|settled on)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(choice is|official choice|consensus is|selected)\b", re.IGNORECASE),
    ]

    ACTION_PATTERNS = [
        re.compile(
            r"\b(please finish|please do|will deliver|take the action|action item|assigned to|responsible for)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(need to complete|todo|follow up with|next step is|work on)\b", re.IGNORECASE
        ),
    ]

    COMMITMENT_PATTERNS = [
        re.compile(
            r"\b(i will|i'll|i commit|i can take|i'll make sure|i promise|i will finish|i will deliver)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(by friday|by next week|by tomorrow|by monday)\b", re.IGNORECASE),
    ]

    QUESTION_PATTERNS = [
        re.compile(r"\?"),
        re.compile(
            r"\b(what|why|how|when|who|where|which|is there|can we|should we|could we)\b",
            re.IGNORECASE,
        ),
    ]

    SUGGESTION_PATTERNS = [
        re.compile(
            r"\b(how about|what if|suggest|propose|recommend|maybe we should|we could try|i propose)\b",
            re.IGNORECASE,
        ),
    ]

    PROBLEM_PATTERNS = [
        re.compile(
            r"\b(problem|issue|bug|failure|error|timeout|blocker|risk|crash|bottleneck|down)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(failing|broken|intermittent|not working|slow|regression)\b", re.IGNORECASE),
    ]

    async def classify_utterance(
        self,
        text: str,
        segment_id: str | None = None,
        **kwargs: object,
    ) -> list[UtteranceClass]:
        _ = (segment_id, kwargs)
        classes: list[UtteranceClass] = []
        lowered = text.lower()

        if any(p.search(lowered) for p in self.DECISION_PATTERNS):
            classes.append(UtteranceClass.DECISION)

        if any(p.search(lowered) for p in self.ACTION_PATTERNS):
            classes.append(UtteranceClass.ACTION)

        if any(p.search(lowered) for p in self.COMMITMENT_PATTERNS):
            classes.append(UtteranceClass.COMMITMENT)

        if any(p.search(text) for p in self.QUESTION_PATTERNS):
            classes.append(UtteranceClass.QUESTION)

        if any(p.search(lowered) for p in self.SUGGESTION_PATTERNS):
            classes.append(UtteranceClass.SUGGESTION)

        if any(p.search(lowered) for p in self.PROBLEM_PATTERNS):
            classes.append(UtteranceClass.PROBLEM)

        # Fallback to Information if no specific class matched
        if not classes:
            classes.append(UtteranceClass.INFORMATION)

        return classes
