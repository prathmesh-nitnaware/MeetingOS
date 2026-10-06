import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.memory.models import (
    AuditLogModel,
    CommitmentModel,
    DecisionModel,
    EmbeddingModel,
    EventModel,
    EvidenceModel,
    IssueModel,
    JobModel,
    MeetingEntityModel,
    MeetingModel,
    ParticipantModel,
    RelationshipModel,
    RetentionPolicyModel,
    SpeakerModel,
    TopicModel,
    TranscriptSegmentModel,
    UtteranceClassificationModel,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Every table that hangs off meetings.id. Deleted explicitly so purges behave the same on
# SQLite (no FK cascade by default) and PostgreSQL.
MEETING_CHILD_MODELS = (
    MeetingEntityModel,
    TopicModel,
    DecisionModel,
    CommitmentModel,
    IssueModel,
    EventModel,
    RelationshipModel,
    UtteranceClassificationModel,
    EmbeddingModel,
    EvidenceModel,
    JobModel,
    ParticipantModel,
    SpeakerModel,
    TranscriptSegmentModel,
)


def meeting_storage_dir(storage_root: str | Path, org_id: str, meeting_id: str) -> Path:
    return Path(storage_root) / "orgs" / org_id / "meetings" / meeting_id


def remove_meeting_files(storage_root: str | Path | None, org_id: str, meeting_id: str) -> int:
    """Delete a meeting's uploaded media directory. Returns the number of files removed."""
    if not storage_root:
        return 0
    base = Path(storage_root).resolve()
    target = meeting_storage_dir(base, org_id, meeting_id).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        logger.warning("Refusing to delete files outside storage root: %s", target)
        return 0
    if not target.is_dir():
        return 0
    count = sum(1 for p in target.rglob("*") if p.is_file())
    shutil.rmtree(target, ignore_errors=True)
    return count


async def purge_meetings(session: AsyncSession, meeting_ids: list[str]) -> None:
    """Permanently delete meetings and every row that references them."""
    if not meeting_ids:
        return
    for model in MEETING_CHILD_MODELS:
        await session.execute(delete(model).where(model.meeting_id.in_(meeting_ids)))
    await session.execute(delete(MeetingModel).where(MeetingModel.id.in_(meeting_ids)))


class RetentionService:
    """Purges expired meetings, transcripts, evidence, audio and audit logs for ONE organisation."""

    def __init__(
        self,
        session: AsyncSession,
        org_id: str,
        upload_storage_dir: str | Path | None = None,
    ) -> None:
        self.session = session
        self.org_id = org_id
        self.upload_storage_dir = upload_storage_dir

    @staticmethod
    def _cutoff(days: int) -> datetime:
        return datetime.now(UTC) - timedelta(days=days)

    async def _expired_meeting_ids(self, days: int) -> list[str]:
        stmt = select(MeetingModel.id).where(
            MeetingModel.org_id == self.org_id, MeetingModel.created_at < self._cutoff(days)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _org_meeting_ids(self):
        return select(MeetingModel.id).where(MeetingModel.org_id == self.org_id)

    async def clean_expired_meetings(self, days: int | None, dry_run: bool = True) -> int:
        if not days or days <= 0:
            return 0
        meeting_ids = await self._expired_meeting_ids(days)
        if not dry_run and meeting_ids:
            for meeting_id in meeting_ids:
                remove_meeting_files(self.upload_storage_dir, self.org_id, meeting_id)
            await purge_meetings(self.session, meeting_ids)
        return len(meeting_ids)

    async def clean_expired_transcripts(self, days: int | None, dry_run: bool = True) -> int:
        if not days or days <= 0:
            return 0
        stmt = select(TranscriptSegmentModel.id).where(
            TranscriptSegmentModel.meeting_id.in_(self._org_meeting_ids()),
            TranscriptSegmentModel.created_at < self._cutoff(days),
        )
        seg_ids = list((await self.session.execute(stmt)).scalars().all())
        if not dry_run and seg_ids:
            await self.session.execute(
                delete(TranscriptSegmentModel).where(TranscriptSegmentModel.id.in_(seg_ids))
            )
        return len(seg_ids)

    async def clean_expired_evidence(self, days: int | None, dry_run: bool = True) -> int:
        if not days or days <= 0:
            return 0
        cutoff = self._cutoff(days)
        stmt = select(EvidenceModel.id).where(
            EvidenceModel.meeting_id.in_(self._org_meeting_ids()),
            EvidenceModel.created_at < cutoff,
        )
        ev_ids = list((await self.session.execute(stmt)).scalars().all())
        if not dry_run and ev_ids:
            await self.session.execute(delete(EvidenceModel).where(EvidenceModel.id.in_(ev_ids)))
            await self.session.execute(
                delete(EmbeddingModel).where(
                    EmbeddingModel.meeting_id.in_(self._org_meeting_ids()),
                    EmbeddingModel.created_at < cutoff,
                )
            )
        return len(ev_ids)

    async def clean_expired_audio(self, days: int | None, dry_run: bool = True) -> int:
        """Delete uploaded audio/video files older than ``days`` (transcripts are kept)."""
        if not days or days <= 0 or not self.upload_storage_dir:
            return 0
        removed = 0
        for meeting_id in await self._expired_meeting_ids(days):
            folder = meeting_storage_dir(self.upload_storage_dir, self.org_id, meeting_id)
            files = [p for p in folder.glob("audio.*") if p.is_file()] if folder.is_dir() else []
            removed += len(files)
            if not dry_run:
                for f in files:
                    f.unlink(missing_ok=True)
        return removed

    async def clean_expired_audit_logs(self, days: int | None, dry_run: bool = True) -> int:
        if not days or days <= 0:
            return 0
        stmt = select(AuditLogModel.id).where(
            AuditLogModel.org_id == self.org_id,
            AuditLogModel.timestamp < self._cutoff(days),
        )
        log_ids = list((await self.session.execute(stmt)).scalars().all())
        if not dry_run and log_ids:
            await self.session.execute(delete(AuditLogModel).where(AuditLogModel.id.in_(log_ids)))
        return len(log_ids)

    async def run_cleanup(
        self,
        meeting_days: int | None = None,
        transcript_days: int | None = None,
        evidence_days: int | None = None,
        audit_log_days: int | None = None,
        audio_days: int | None = None,
        dry_run: bool = True,
        actor_id: str = "system",
    ) -> dict[str, int]:
        """Purge (or, with dry_run, count) records matching the expiration criteria."""
        results = {
            "meetings_deleted": await self.clean_expired_meetings(meeting_days, dry_run),
            "transcripts_deleted": await self.clean_expired_transcripts(transcript_days, dry_run),
            "evidence_deleted": await self.clean_expired_evidence(evidence_days, dry_run),
            "audio_files_deleted": await self.clean_expired_audio(audio_days, dry_run),
            "audit_logs_deleted": await self.clean_expired_audit_logs(audit_log_days, dry_run),
        }

        if not dry_run:
            self.session.add(
                AuditLogModel(
                    org_id=self.org_id,
                    actor_id=actor_id,
                    action="run_retention_policy",
                    resource_type="organization",
                    resource_id=self.org_id,
                    outcome="succeeded",
                    metadata_json={
                        "meeting_days": meeting_days,
                        "transcript_days": transcript_days,
                        "evidence_days": evidence_days,
                        "audio_days": audio_days,
                        "audit_log_days": audit_log_days,
                        "deleted": results,
                    },
                )
            )
            await self.session.commit()

        return results


async def enforce_retention_policies(
    session: AsyncSession, upload_storage_dir: str | Path | None
) -> dict[str, Any]:
    """Apply every organisation's saved retention policy that has auto-delete enabled."""
    policies = (
        (
            await session.execute(
                select(RetentionPolicyModel).where(
                    RetentionPolicyModel.auto_delete_enabled.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )

    summary: dict[str, Any] = {}
    for policy in policies:
        service = RetentionService(
            session, org_id=policy.org_id, upload_storage_dir=upload_storage_dir
        )
        summary[policy.org_id] = await service.run_cleanup(
            meeting_days=policy.meeting_retention_days,
            transcript_days=policy.transcript_retention_days,
            evidence_days=policy.memory_retention_days,
            audio_days=policy.audio_retention_days,
            dry_run=False,
            actor_id="retention-scheduler",
        )
    return summary
