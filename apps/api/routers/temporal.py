from datetime import datetime
from typing import Annotated

from apps.api.config import settings
from fastapi import APIRouter, HTTPException, Query, status
from packages.common.enums import EventType
from packages.memory.database import get_db_session
from packages.reasoning.temporal import (
    CommitmentHistoryItem,
    DecisionHistoryItem,
    IssueHistoryItem,
    TemporalIntelligenceEngine,
    TemporalReconciliationResult,
    TimelineEventItem,
)
from pydantic import BaseModel

router = APIRouter(tags=["Temporal Intelligence"])


class ReconcileRequest(BaseModel):
    meeting_id: str


@router.get("/timeline", response_model=list[TimelineEventItem])
async def get_global_timeline(
    entity_id: Annotated[str | None, Query(description="Filter by associated entity ID")] = None,
    event_type: Annotated[EventType | None, Query(description="Filter by event type")] = None,
    start_date: Annotated[datetime | None, Query(description="Filter by start date")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter by end date")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TimelineEventItem]:
    """Retrieve chronologically ordered organizational events across all ingested meetings."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        return await engine.get_global_timeline(
            entity_id=entity_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )


@router.post("/temporal/reconcile", response_model=TemporalReconciliationResult)
async def reconcile_meeting_lifecycle(
    request: ReconcileRequest,
) -> TemporalReconciliationResult:
    """Analyze a meeting's facts against prior organizational history to detect cross-meeting changes."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        return await engine.reconcile_meeting_lifecycle(request.meeting_id)


@router.get("/decisions/{decision_id}/history", response_model=DecisionHistoryItem)
async def get_decision_history(
    decision_id: str,
) -> DecisionHistoryItem:
    """Retrieve the complete chronological lifecycle and change history for a decision."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        history = await engine.reconstruct_decision_history(decision_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Decision '{decision_id}' not found",
            )
        return history


@router.get("/commitments/{commitment_id}/history", response_model=CommitmentHistoryItem)
async def get_commitment_history(
    commitment_id: str,
) -> CommitmentHistoryItem:
    """Retrieve deadline revisions, assignments, and slippage history for a commitment."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        history = await engine.reconstruct_commitment_history(commitment_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Commitment '{commitment_id}' not found",
            )
        return history


@router.get("/issues/{issue_id}/history", response_model=IssueHistoryItem)
async def get_issue_history(
    issue_id: str,
) -> IssueHistoryItem:
    """Retrieve detection, recurrence, and resolution history for an organizational issue."""
    async with get_db_session(settings.database_url) as session:
        engine = TemporalIntelligenceEngine(session)
        history = await engine.reconstruct_issue_history(issue_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue '{issue_id}' not found",
            )
        return history
