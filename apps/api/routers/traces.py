from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.agents.traces import AgentExecutionTrace, global_trace_store

router = APIRouter(prefix="/query/traces", tags=["Query Traces"])


@router.get("", response_model=list[AgentExecutionTrace])
async def list_traces(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: UserIdentity = Depends(require_viewer),
) -> Any:
    """List recent agent execution traces for observability."""
    return global_trace_store.list_traces(limit=limit, offset=offset)


@router.get("/{trace_id}", response_model=AgentExecutionTrace)
async def get_trace(
    trace_id: str,
    _user: UserIdentity = Depends(require_viewer),
) -> Any:
    """Retrieve detailed execution trace by trace ID."""
    trace = global_trace_store.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace with ID {trace_id} not found")
    return trace
