from typing import Any

from packages.common.models import AnswerWithAttribution, EvidenceItem, ReasoningContext
from packages.memory.graph import GraphService
from packages.reasoning.interfaces import BaseReasoner
from packages.reasoning.mock import MockReasoner
from packages.reasoning.planner import QueryPlan, QueryPlanner
from packages.reasoning.temporal import TemporalIntelligenceEngine
from packages.retrieval.search import HybridSearchEngine
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class QueryRequest(BaseModel):
    question: str
    query_plan_override: QueryPlan | None = None
    max_evidence_items: int = 10


class QueryResponse(BaseModel):
    question: str
    answer: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    query_plan: QueryPlan
    confidence: float = 1.0
    reasoning_path: list[str] = Field(default_factory=list)
    model_name: str = "mock-reasoner"
    model_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"


class RAGPipeline:
    """Full Question-Answering and Reasoning Pipeline orchestrating Planning, Hybrid Retrieval, Graph Traversal, and Answer Generation."""

    def __init__(
        self,
        session: AsyncSession,
        planner: QueryPlanner | None = None,
        reasoner: BaseReasoner | None = None,
    ) -> None:
        self.session = session
        self.planner = planner or QueryPlanner()
        self.reasoner = reasoner or MockReasoner()
        self.search_engine = HybridSearchEngine(session)
        self.graph_service = GraphService(session)
        self.temporal_engine = TemporalIntelligenceEngine(session)

    async def answer_question(
        self,
        question: str,
        plan_override: QueryPlan | None = None,
        max_evidence: int = 10,
    ) -> QueryResponse:
        """Execute full multi-channel retrieval and grounded reasoning pipeline."""
        # 1. Query Planning
        plan = plan_override or self.planner.plan_query(question)
        reasoning_path: list[str] = [
            f"Parsed query intent: '{plan.intent}', type filter: '{plan.type}', person: '{plan.person}', topic: '{plan.topic}', entities: {plan.entities}."
        ]

        # 2. Hybrid Retrieval (Lexical + Vector + Metadata Constraints)
        search_res = await self.search_engine.search(
            query=question,
            person=plan.person,
            topic=plan.topic,
            result_type=None,
            limit=max_evidence,
        )

        evidence_list: list[EvidenceItem] = []
        for candidate in search_res.results:
            if candidate.evidence and candidate.evidence not in evidence_list:
                evidence_list.append(candidate.evidence)

        reasoning_path.append(
            f"Hybrid search retrieved {search_res.total_results} candidates and {len(evidence_list)} direct transcript evidence citations."
        )

        # 3. Knowledge Graph & Timeline Enrichment
        graph_paths: list[dict[str, Any]] = []
        for ent_name in plan.entities:
            # Query entity graph details if available
            cand_id = f"ent-{ent_name.lower().replace(' ', '-')}"
            detail = await self.graph_service.get_entity_detail(cand_id)
            if detail:
                graph_paths.append(
                    {
                        "entity": detail.entity.name,
                        "meetings_count": detail.meetings_count,
                        "related": [r.relationship_type.value for r in detail.relationships],
                    }
                )

        timeline_events = await self.temporal_engine.get_global_timeline(limit=10)
        if timeline_events:
            reasoning_path.append(
                f"Retrieved {len(timeline_events)} historical lifecycle change events for temporal grounding."
            )

        # 4. Reasoner / Synthesis Layer
        reasoning_context = ReasoningContext(
            query_plan=plan.model_dump(),
            retrieved_segments=[],
            graph_paths=graph_paths,
            timeline_events=[],
        )

        # Execute reasoner
        if not evidence_list and not search_res.results:
            return QueryResponse(
                question=question,
                answer="The available meeting memory does not establish an answer to this question.",
                evidence=[],
                query_plan=plan,
                confidence=0.0,
                reasoning_path=reasoning_path
                + ["No relevant evidence found in organizational memory."],
                model_name="mock-reasoner",
                model_version="1.0.0",
                pipeline_version="1.0.0",
            )

        # Build grounded synthesis based on evidence and retrieved facts
        reasoner_result: AnswerWithAttribution = await self.reasoner.reason(
            question=question,
            evidence=evidence_list,
            context=reasoning_context,
        )

        # If answer was constructed from structured candidate summaries when direct segment evidence is sparse:
        final_answer = reasoner_result.answer
        if not evidence_list and search_res.results:
            top_candidates = [c.text for c in search_res.results[:3]]
            final_answer = f"According to organizational records: {' '.join(top_candidates)}"

        return QueryResponse(
            question=question,
            answer=final_answer,
            evidence=evidence_list,
            query_plan=plan,
            confidence=reasoner_result.confidence,
            reasoning_path=reasoning_path + reasoner_result.reasoning_path,
            model_name="mock-reasoner",
            model_version="1.0.0",
            pipeline_version="1.0.0",
        )
