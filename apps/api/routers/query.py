from apps.api.config import settings
from fastapi import APIRouter
from packages.agents.context import AgentResult
from packages.agents.orchestrator import AgentOrchestrator
from packages.memory.database import get_db_session
from packages.reasoning.qa import QueryRequest, QueryResponse, RAGPipeline

router = APIRouter(tags=["Query Intelligence"])


@router.post("/query", response_model=QueryResponse)
async def query_organizational_memory(
    request: QueryRequest,
) -> QueryResponse:
    """Answer historical organizational questions using multi-channel retrieval, knowledge graph context, and grounded evidence attribution."""
    async with get_db_session(settings.database_url) as session:
        pipeline = RAGPipeline(session)
        return await pipeline.answer_question(
            question=request.question,
            plan_override=request.query_plan_override,
            max_evidence=request.max_evidence_items,
        )


@router.post("/query/agentic", response_model=AgentResult)
async def query_organizational_memory_agentic(
    request: QueryRequest,
) -> AgentResult:
    """Answer historical organizational questions using a controlled multi-agent reasoning system."""
    async with get_db_session(settings.database_url) as session:
        orchestrator = AgentOrchestrator(session)
        return await orchestrator.query(request.question)
