from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from apps.api.providers import build_embedder, build_reasoner
from apps.api.rate_limiter import rate_limit
from fastapi import APIRouter, Depends
from packages.agents.context import AgentResult
from packages.agents.orchestrator import AgentOrchestrator
from packages.memory.database import get_db_session
from packages.reasoning.qa import QueryRequest, QueryResponse, RAGPipeline

router = APIRouter(tags=["Query Intelligence"])

query_rate_limit = rate_limit("query", lambda: settings.rate_limit_query_per_min)
agentic_rate_limit = rate_limit("agentic", lambda: settings.rate_limit_agentic_per_min)


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(query_rate_limit)])
async def query_organizational_memory(
    request: QueryRequest,
    user: UserIdentity = Depends(require_viewer),
) -> QueryResponse:
    """Answer historical organisational questions using multi-channel retrieval, knowledge graph context, and grounded evidence attribution."""
    async with get_db_session(settings.database_url) as session:
        pipeline = RAGPipeline(
            session,
            reasoner=build_reasoner(),
            embedder=build_embedder(),
            org_id=user.org_id,
        )
        return await pipeline.answer_question(
            question=request.question,
            plan_override=request.query_plan_override,
            max_evidence=request.max_evidence_items,
        )


@router.post(
    "/query/agentic", response_model=AgentResult, dependencies=[Depends(agentic_rate_limit)]
)
async def query_organizational_memory_agentic(
    request: QueryRequest,
    user: UserIdentity = Depends(require_viewer),
) -> AgentResult:
    """Answer historical organisational questions using a controlled multi-agent reasoning system."""
    async with get_db_session(settings.database_url) as session:
        orchestrator = AgentOrchestrator(
            session,
            reasoner=build_reasoner(),
            org_id=user.org_id,
            embedder=build_embedder(),
        )
        return await orchestrator.query(request.question)
