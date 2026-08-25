from datetime import UTC, datetime, timedelta

from packages.memory.models import (
    AuditLogModel,
    EvidenceModel,
    MeetingModel,
    TranscriptSegmentModel,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class RetentionService:
    """Service responsible for purging expired meetings, transcripts, evidence, and audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def clean_expired_meetings(self, days: int, dry_run: bool = True) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(MeetingModel.id).where(MeetingModel.created_at < cutoff)
        result = await self.session.execute(stmt)
        meeting_ids = list(result.scalars().all())

        if not dry_run and meeting_ids:
            # CASCADE constraints automatically clean cascade tables
            del_stmt = delete(MeetingModel).where(MeetingModel.id.in_(meeting_ids))
            await self.session.execute(del_stmt)
        return len(meeting_ids)

    async def clean_expired_transcripts(self, days: int, dry_run: bool = True) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(TranscriptSegmentModel.id).where(TranscriptSegmentModel.created_at < cutoff)
        result = await self.session.execute(stmt)
        seg_ids = list(result.scalars().all())

        if not dry_run and seg_ids:
            del_stmt = delete(TranscriptSegmentModel).where(TranscriptSegmentModel.id.in_(seg_ids))
            await self.session.execute(del_stmt)
        return len(seg_ids)

    async def clean_expired_evidence(self, days: int, dry_run: bool = True) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(EvidenceModel.id).where(EvidenceModel.created_at < cutoff)
        result = await self.session.execute(stmt)
        ev_ids = list(result.scalars().all())

        if not dry_run and ev_ids:
            del_stmt = delete(EvidenceModel).where(EvidenceModel.id.in_(ev_ids))
            await self.session.execute(del_stmt)
        return len(ev_ids)

    async def clean_expired_audit_logs(self, days: int, dry_run: bool = True) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(AuditLogModel.id).where(AuditLogModel.timestamp < cutoff)
        result = await self.session.execute(stmt)
        log_ids = list(result.scalars().all())

        if not dry_run and log_ids:
            del_stmt = delete(AuditLogModel).where(AuditLogModel.id.in_(log_ids))
            await self.session.execute(del_stmt)
        return len(log_ids)

    async def run_cleanup(
        self,
        meeting_days: int | None = None,
        transcript_days: int | None = None,
        evidence_days: int | None = None,
        audit_log_days: int | None = None,
        dry_run: bool = True,
        actor_id: str = "system",
    ) -> dict[str, int]:
        """Purge records matching expiration criteria."""
        results = {
            "meetings_deleted": 0,
            "transcripts_deleted": 0,
            "evidence_deleted": 0,
            "audit_logs_deleted": 0,
        }

        results["meetings_deleted"] = await self.clean_expired_meetings(meeting_days or 0, dry_run)
        results["transcripts_deleted"] = await self.clean_expired_transcripts(
            transcript_days or 0, dry_run
        )
        results["evidence_deleted"] = await self.clean_expired_evidence(evidence_days or 0, dry_run)
        results["audit_logs_deleted"] = await self.clean_expired_audit_logs(
            audit_log_days or 0, dry_run
        )

        if not dry_run:
            from packages.memory.repository import MeetingRepository

            repo = MeetingRepository(self.session)
            await repo.create_audit_log(
                actor_id=actor_id,
                action="run_retention_policy",
                resource_type="system",
                resource_id=None,
                outcome="succeeded",
                metadata_json={
                    "dry_run": dry_run,
                    "meeting_days": meeting_days,
                    "transcript_days": transcript_days,
                    "evidence_days": evidence_days,
                    "audit_log_days": audit_log_days,
                    "deleted": results,
                },
            )
            await self.session.commit()

        return results
