from datetime import datetime

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends, HTTPException
from packages.common.enums import ProcessingStatus
from packages.memory.database import get_db_session
from packages.memory.models import JobModel, MeetingModel
from pydantic import BaseModel
from sqlalchemy import or_, select

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
async def get_job_status(
    job_id: str,
    user: UserIdentity = Depends(require_viewer),
) -> JobDetailResponse:
    """Retrieve processing job status, progress, and stage for the caller's organisation."""
    stmt = (
        select(JobModel)
        .outerjoin(MeetingModel, MeetingModel.id == JobModel.meeting_id)
        .where(
            JobModel.id == job_id,
            or_(
                JobModel.org_id == user.org_id,
                # Jobs created before jobs.org_id existed are scoped through their meeting
                (JobModel.org_id.is_(None)) & (MeetingModel.org_id == user.org_id),
            ),
        )
    )
    async with get_db_session(settings.database_url) as session:
        job = (await session.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")

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
