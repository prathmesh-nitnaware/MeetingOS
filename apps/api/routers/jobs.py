from datetime import datetime

from apps.api.config import settings
from fastapi import APIRouter, HTTPException
from packages.common.enums import ProcessingStatus
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from pydantic import BaseModel

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobDetailResponse(BaseModel):
    job_id: str
    meeting_id: str | None = None
    status: ProcessingStatus
    stage: str
    progress: float
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_status(job_id: str) -> JobDetailResponse:
    """Retrieve asynchronous processing job status, progress, and stage."""
    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)
        job = await repo.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobDetailResponse(
        job_id=job.id,
        meeting_id=job.meeting_id,
        status=ProcessingStatus(job.status),
        stage=job.stage,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
