from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.agents.traces import (
    AgentExecutionTrace,
    global_trace_store,
    load_trace,
    load_traces,
)
from packages.memory.database import get_db_session

router = APIRouter(prefix="/query/traces", tags=["Query Traces"])


@router.get("", response_model=list[AgentExecutionTrace])
async def list_traces(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserIdentity = Depends(require_viewer),
) -> Any:
    """List recent agent execution traces of the caller's organisation."""
    try:
        async with get_db_session(settings.database_url) as session:
            traces = await load_traces(session, user.org_id, limit=limit, offset=offset)
    except Exception:
        traces = []
    if traces:
        return traces
    # Fallback: traces recorded by this process that could not be persisted
    return global_trace_store.list_traces(limit=limit, offset=offset, org_id=user.org_id)


@router.get("/{trace_id}", response_model=AgentExecutionTrace)
async def get_trace(
    trace_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> Any:
    """Retrieve a detailed execution trace of the caller's organisation by trace ID."""
    trace = None
    try:
        async with get_db_session(settings.database_url) as session:
            trace = await load_trace(session, trace_id, user.org_id)
    except Exception:
        trace = None
    trace = trace or global_trace_store.get_trace(trace_id, org_id=user.org_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace with ID {trace_id} not found")
    return trace
