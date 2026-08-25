import re

from pydantic import BaseModel, Field


class QueryPlan(BaseModel):
    """Structured plan extracted from a user question for multi-channel retrieval."""

    person: str | None = None
    topic: str | None = None
    time_range: str | None = None
    type: str | None = None  # "decision", "action", "commitment", "issue", "timeline", "general"
    entities: list[str] = Field(default_factory=list)
    intent: str = "qa"


class QueryPlanner:
    """Parser and planner converting natural language queries into structured retrieval constraints."""

    KNOWN_PERSONS = [
        "rahul",
        "priya",
        "alex",
        "sharma",
        "verma",
        "rivera",
        "sarah",
        "john",
        "david",
    ]

    KNOWN_TOPICS = [
        "database",
        "authentication",
        "auth",
        "api",
        "security",
        "cache",
        "caching",
        "infrastructure",
        "performance",
        "diarization",
        "speech",
        "vector",
        "migration",
    ]

    KNOWN_ENTITIES = [
        "postgresql",
        "postgres",
        "mongodb",
        "mongo",
        "redis",
        "pgvector",
        "meetingos",
        "fastapi",
        "celery",
        "docker",
    ]

    def plan_query(self, question: str) -> QueryPlan:
        """Parse natural language question into structured QueryPlan."""
        lowered = question.lower()

        # 1. Detect fact/event type
        q_type: str | None = None
        if any(
            w in lowered
            for w in [
                "decide",
                "decision",
                "decisions",
                "agreed",
                "chose",
                "chosen",
                "using",
                "switch to",
                "adopt",
                "replaces",
                "why are we",
            ]
        ):
            q_type = "decision"
        elif any(
            w in lowered
            for w in [
                "action",
                "actions",
                "commit",
                "commitment",
                "assigned",
                "todo",
                "task",
                "deadline",
            ]
        ):
            q_type = "action"
        elif any(
            w in lowered
            for w in [
                "issue",
                "issues",
                "problem",
                "bug",
                "timeout",
                "error",
                "failure",
                "unresolved",
            ]
        ):
            q_type = "issue"
        elif any(
            w in lowered for w in ["timeline", "history", "chronology", "sequence", "when did"]
        ):
            q_type = "timeline"

        # 2. Detect Person
        person: str | None = None
        for p in self.KNOWN_PERSONS:
            if re.search(rf"\b{re.escape(p)}\b", lowered):
                person = p.title()
                break

        # 3. Detect Topic
        topic: str | None = None
        for t in self.KNOWN_TOPICS:
            if re.search(rf"\b{re.escape(t)}\b", lowered):
                topic = t.title()
                break

        # 4. Detect Entities
        entities: list[str] = []
        for e in self.KNOWN_ENTITIES:
            if re.search(rf"\b{re.escape(e)}\b", lowered):
                canonical = e.title()
                if e == "postgresql" or e == "postgres":
                    canonical = "PostgreSQL"
                elif e == "mongodb" or e == "mongo":
                    canonical = "MongoDB"
                elif e == "meetingos":
                    canonical = "MeetingOS"
                entities.append(canonical)

        # 5. Detect Time Range
        time_range: str | None = None
        time_patterns = [
            r"\blast month\b",
            r"\blast week\b",
            r"\byesterday\b",
            r"\btoday\b",
            r"\bby friday\b",
            r"\bnext week\b",
            r"\blast sprint\b",
            r"\bin august\b",
        ]
        for pat in time_patterns:
            match = re.search(pat, lowered)
            if match:
                time_range = match.group(0)
                break

        # 6. Intent
        intent = "qa"
        if (
            q_type == "timeline"
            or "history" in lowered
            or "why are we" in lowered
            or "how did" in lowered
        ):
            intent = "historical_reasoning"
        elif q_type == "issue" and "unresolved" in lowered:
            intent = "issue_tracking"

        return QueryPlan(
            person=person,
            topic=topic,
            time_range=time_range,
            type=q_type,
            entities=entities,
            intent=intent,
        )
