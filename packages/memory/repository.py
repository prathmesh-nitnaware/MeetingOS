from typing import Any
from uuid import uuid4

from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EntityType,
    EventType,
    IssueStatus,
    ProcessingStatus,
    RelationType,
    SourceType,
)
from packages.common.models import (
    EvidenceItem,
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIssue,
    ExtractedRelation,
    Meeting,
    MeetingMetadata,
    Participant,
    SpeakerInfo,
    TranscriptSegment,
)
from packages.memory.models import (
    AuditLogModel,
    Base,
    CommitmentModel,
    DecisionModel,
    EmbeddingModel,
    EntityModel,
    EventModel,
    EvidenceModel,
    IssueModel,
    JobModel,
    MeetingEntityModel,
    MeetingModel,
    ParticipantModel,
    RelationshipModel,
    SpeakerModel,
    TopicModel,
    TranscriptSegmentModel,
    UtteranceClassificationModel,
)
from packages.nlp.pipeline import NLPExtractionResult
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload


async def init_db(engine: AsyncEngine) -> None:
    """Create database tables if they do not already exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class MeetingRepository:
    """Repository managing persistence and retrieval of CMF meetings, transcripts, NLP facts, and jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_meeting(self, meeting: Meeting) -> MeetingModel:
        """Persist a new Meeting with participants, speakers, and segments in an atomic transaction."""
        meeting_row = MeetingModel(
            id=meeting.meeting_id,
            title=meeting.title,
            meeting_date=meeting.meeting_date,
            duration_seconds=meeting.duration_seconds,
            source_type=str(meeting.source_type),
            processing_status=str(meeting.processing_status),
            model_pipeline_version=meeting.metadata.model_pipeline_version,
            metadata_json=meeting.metadata.model_dump(),
            source_provider=meeting.source_provider,
            external_meeting_id=meeting.external_meeting_id,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )
        self.session.add(meeting_row)

        for p in meeting.participants:
            self.session.add(
                ParticipantModel(
                    id=p.id,
                    meeting_id=meeting.meeting_id,
                    canonical_name=p.canonical_name,
                    aliases=p.aliases,
                )
            )

        for spk in meeting.speakers:
            self.session.add(
                SpeakerModel(
                    id=str(uuid4()),
                    meeting_id=meeting.meeting_id,
                    speaker_id=spk.speaker_id,
                    name=spk.name,
                    canonical_entity_id=spk.canonical_entity_id,
                )
            )

        for seg in meeting.segments:
            self.session.add(
                TranscriptSegmentModel(
                    id=seg.segment_id,
                    meeting_id=meeting.meeting_id,
                    sequence=seg.sequence,
                    speaker_id=seg.speaker_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                )
            )

        await self.session.flush()
        return meeting_row

    async def get_meeting(self, meeting_id: str) -> Meeting | None:
        """Fetch a Meeting by ID with all participants, speakers, and ordered segments as CMF."""
        stmt = (
            select(MeetingModel)
            .where(MeetingModel.id == meeting_id)
            .options(
                selectinload(MeetingModel.participants),
                selectinload(MeetingModel.speakers),
                selectinload(MeetingModel.segments),
            )
        )
        result = await self.session.execute(stmt)
        meeting_row = result.scalar_one_or_none()
        if not meeting_row:
            return None

        meta_dict = meeting_row.metadata_json or {}
        metadata = MeetingMetadata.model_validate(meta_dict) if meta_dict else MeetingMetadata()

        return Meeting(
            meeting_id=meeting_row.id,
            title=meeting_row.title,
            meeting_date=meeting_row.meeting_date,
            duration_seconds=meeting_row.duration_seconds,
            source_type=SourceType(meeting_row.source_type),
            processing_status=ProcessingStatus(meeting_row.processing_status),
            source_provider=meeting_row.source_provider,
            external_meeting_id=meeting_row.external_meeting_id,
            participants=[
                Participant(id=p.id, canonical_name=p.canonical_name, aliases=p.aliases or [])
                for p in meeting_row.participants
            ],
            speakers=[
                SpeakerInfo(
                    speaker_id=s.speaker_id,
                    name=s.name,
                    canonical_entity_id=s.canonical_entity_id,
                )
                for s in meeting_row.speakers
            ],
            segments=[
                TranscriptSegment(
                    segment_id=seg.id,
                    sequence=seg.sequence,
                    speaker_id=seg.speaker_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                )
                for seg in meeting_row.segments
            ],
            metadata=metadata,
            created_at=meeting_row.created_at,
            updated_at=meeting_row.updated_at,
        )

    async def list_meetings(self, limit: int = 50, offset: int = 0) -> list[Meeting]:
        """List meetings ordered by date descending."""
        stmt = (
            select(MeetingModel)
            .options(
                selectinload(MeetingModel.participants),
                selectinload(MeetingModel.speakers),
                selectinload(MeetingModel.segments),
            )
            .order_by(MeetingModel.meeting_date.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        meetings: list[Meeting] = []
        for r in rows:
            meta = (
                MeetingMetadata.model_validate(r.metadata_json)
                if r.metadata_json
                else MeetingMetadata()
            )
            meetings.append(
                Meeting(
                    meeting_id=r.id,
                    title=r.title,
                    meeting_date=r.meeting_date,
                    duration_seconds=r.duration_seconds,
                    source_type=SourceType(r.source_type),
                    processing_status=ProcessingStatus(r.processing_status),
                    source_provider=r.source_provider,
                    external_meeting_id=r.external_meeting_id,
                    participants=[
                        Participant(
                            id=p.id, canonical_name=p.canonical_name, aliases=p.aliases or []
                        )
                        for p in r.participants
                    ],
                    speakers=[
                        SpeakerInfo(
                            speaker_id=s.speaker_id,
                            name=s.name,
                            canonical_entity_id=s.canonical_entity_id,
                        )
                        for s in r.speakers
                    ],
                    segments=[
                        TranscriptSegment(
                            segment_id=seg.id,
                            sequence=seg.sequence,
                            speaker_id=seg.speaker_id,
                            start_time=seg.start_time,
                            end_time=seg.end_time,
                            text=seg.text,
                        )
                        for seg in r.segments
                    ],
                    metadata=meta,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return meetings

    async def save_transcript_segments(
        self,
        meeting_id: str,
        segments: list[TranscriptSegment],
        speakers: list[SpeakerInfo] | None = None,
    ) -> None:
        """Replace or add transcript segments and speaker profiles for a meeting."""
        await self.session.execute(
            delete(TranscriptSegmentModel).where(TranscriptSegmentModel.meeting_id == meeting_id)
        )

        for seg in segments:
            self.session.add(
                TranscriptSegmentModel(
                    id=seg.segment_id,
                    meeting_id=meeting_id,
                    sequence=seg.sequence,
                    speaker_id=seg.speaker_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                )
            )

        if speakers:
            await self.session.execute(
                delete(SpeakerModel).where(SpeakerModel.meeting_id == meeting_id)
            )
            for spk in speakers:
                self.session.add(
                    SpeakerModel(
                        id=str(uuid4()),
                        meeting_id=meeting_id,
                        speaker_id=spk.speaker_id,
                        name=spk.name,
                        canonical_entity_id=spk.canonical_entity_id,
                    )
                )

        await self.session.flush()

    async def get_transcript_segments(self, meeting_id: str) -> list[TranscriptSegment]:
        """Fetch transcript segments for a meeting ordered by sequence."""
        stmt = (
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.meeting_id == meeting_id)
            .order_by(TranscriptSegmentModel.sequence.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            TranscriptSegment(
                segment_id=r.id,
                sequence=r.sequence,
                speaker_id=r.speaker_id,
                start_time=r.start_time,
                end_time=r.end_time,
                text=r.text,
            )
            for r in rows
        ]

    async def update_meeting_status(
        self,
        meeting_id: str,
        status: ProcessingStatus,
        duration_seconds: float | None = None,
    ) -> None:
        """Update processing status and duration of a meeting."""
        stmt = select(MeetingModel).where(MeetingModel.id == meeting_id)
        result = await self.session.execute(stmt)
        meeting = result.scalar_one_or_none()
        if meeting:
            meeting.processing_status = str(status)
            if duration_seconds is not None:
                meeting.duration_seconds = duration_seconds
            await self.session.flush()

    # --------------------------------------------------------------------------
    # Phase 2: NLP Facts Persistence & Querying
    # --------------------------------------------------------------------------

    async def save_nlp_extraction_results(
        self,
        meeting_id: str,
        results: NLPExtractionResult,
    ) -> None:
        """Persist entities, topics, decisions, commitments, issues, events, and relations in an atomic transaction."""
        # 1. Clean existing facts for this meeting
        await self.session.execute(
            delete(MeetingEntityModel).where(MeetingEntityModel.meeting_id == meeting_id)
        )
        await self.session.execute(delete(TopicModel).where(TopicModel.meeting_id == meeting_id))
        await self.session.execute(
            delete(DecisionModel).where(DecisionModel.meeting_id == meeting_id)
        )
        await self.session.execute(
            delete(CommitmentModel).where(CommitmentModel.meeting_id == meeting_id)
        )
        await self.session.execute(delete(IssueModel).where(IssueModel.meeting_id == meeting_id))
        await self.session.execute(delete(EventModel).where(EventModel.meeting_id == meeting_id))
        await self.session.execute(
            delete(RelationshipModel).where(RelationshipModel.meeting_id == meeting_id)
        )
        await self.session.execute(
            delete(UtteranceClassificationModel).where(
                UtteranceClassificationModel.meeting_id == meeting_id
            )
        )

        # 2. Persist Entities & Associations
        for ent in results.entities:
            # Check or upsert entity
            stmt = select(EntityModel).where(EntityModel.id == ent.entity_id)
            existing = (await self.session.execute(stmt)).scalar_one_or_none()
            if not existing:
                self.session.add(
                    EntityModel(
                        id=ent.entity_id,
                        name=ent.name,
                        entity_type=str(ent.entity_type),
                    )
                )
            self.session.add(
                MeetingEntityModel(
                    meeting_id=meeting_id,
                    entity_id=ent.entity_id,
                )
            )

        # 3. Persist Topics
        for top in results.topics:
            self.session.add(
                TopicModel(
                    meeting_id=meeting_id,
                    name=top,
                )
            )

        # 4. Persist Decisions
        for dec in results.decisions:
            self.session.add(
                DecisionModel(
                    id=dec.decision_id,
                    meeting_id=meeting_id,
                    subject=dec.subject,
                    status=str(dec.status),
                    rationale=dec.rationale,
                    evidence_segment_id=dec.evidence_segment_id,
                    created_at=dec.created_at,
                )
            )

        # 5. Persist Commitments / Actions
        for com in results.commitments:
            self.session.add(
                CommitmentModel(
                    id=com.commitment_id,
                    meeting_id=meeting_id,
                    description=com.description,
                    owner_id=com.owner_id,
                    status=str(com.status),
                    original_deadline=com.original_deadline,
                    current_deadline=com.current_deadline,
                    evidence_segment_id=com.evidence_segment_id,
                )
            )

        # 6. Persist Issues
        for iss in results.issues:
            self.session.add(
                IssueModel(
                    id=iss.issue_id,
                    meeting_id=meeting_id,
                    description=iss.description,
                    owner_id=iss.owner_id,
                    status=str(iss.status),
                    first_detected_at=iss.first_detected_at,
                    last_mentioned_at=iss.last_mentioned_at,
                    resolution_meeting_id=iss.resolution_meeting_id,
                    evidence_segment_id=iss.evidence_segment_id,
                )
            )

        # 7. Persist Events
        for evt in results.events:
            self.session.add(
                EventModel(
                    id=evt.event_id,
                    meeting_id=meeting_id,
                    event_type=str(evt.event_type),
                    occurred_at=evt.occurred_at,
                    subject_entity_id=evt.subject_entity_id,
                    payload_json=evt.payload,
                    evidence_segment_id=evt.evidence_segment_id,
                )
            )

        # 8. Persist Relationships
        for rel in results.relations:
            self.session.add(
                RelationshipModel(
                    id=rel.relation_id,
                    meeting_id=meeting_id,
                    source_entity_id=rel.source_entity_id,
                    target_entity_id=rel.target_entity_id,
                    relation_type=str(rel.relationship_type),
                    segment_id=rel.segment_id,
                    confidence=rel.confidence,
                )
            )

        # 9. Persist Utterance Classifications
        for clf in results.classifications:
            self.session.add(
                UtteranceClassificationModel(
                    meeting_id=meeting_id,
                    segment_id=clf.segment_id,
                    classes_json=[str(c) for c in clf.classes],
                    confidence=clf.confidence,
                )
            )

        await self.session.flush()

    async def get_meeting_entities(self, meeting_id: str) -> list[ExtractedEntity]:
        """Fetch all entities associated with a meeting."""
        stmt = (
            select(EntityModel)
            .join(MeetingEntityModel, MeetingEntityModel.entity_id == EntityModel.id)
            .where(MeetingEntityModel.meeting_id == meeting_id)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedEntity(
                entity_id=r.id,
                name=r.name,
                entity_type=EntityType(r.entity_type),
            )
            for r in rows
        ]

    async def get_meeting_topics(self, meeting_id: str) -> list[str]:
        """Fetch all discussion topics for a meeting."""
        stmt = (
            select(TopicModel.name)
            .where(TopicModel.meeting_id == meeting_id)
            .order_by(TopicModel.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_meeting_decisions(self, meeting_id: str) -> list[ExtractedDecision]:
        """Fetch decisions extracted from a meeting."""
        stmt = (
            select(DecisionModel)
            .where(DecisionModel.meeting_id == meeting_id)
            .order_by(DecisionModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedDecision(
                decision_id=r.id,
                subject=r.subject,
                status=DecisionStatus(r.status),
                rationale=r.rationale,
                meeting_id=r.meeting_id,
                evidence_segment_id=r.evidence_segment_id,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def get_meeting_actions(self, meeting_id: str) -> list[ExtractedCommitment]:
        """Fetch commitments and actions extracted from a meeting."""
        stmt = (
            select(CommitmentModel)
            .where(CommitmentModel.meeting_id == meeting_id)
            .order_by(CommitmentModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedCommitment(
                commitment_id=r.id,
                description=r.description,
                owner_id=r.owner_id,
                status=CommitmentStatus(r.status),
                original_deadline=r.original_deadline,
                current_deadline=r.current_deadline,
                meeting_id=r.meeting_id,
                evidence_segment_id=r.evidence_segment_id,
            )
            for r in rows
        ]

    async def get_meeting_issues(self, meeting_id: str) -> list[ExtractedIssue]:
        """Fetch issues extracted from a meeting."""
        stmt = (
            select(IssueModel)
            .where(IssueModel.meeting_id == meeting_id)
            .order_by(IssueModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedIssue(
                issue_id=r.id,
                description=r.description,
                owner_id=r.owner_id,
                status=IssueStatus(r.status),
                first_detected_at=r.first_detected_at,
                last_mentioned_at=r.last_mentioned_at or r.first_detected_at,
                resolution_meeting_id=r.resolution_meeting_id,
                evidence_segment_id=r.evidence_segment_id,
            )
            for r in rows
        ]

    async def get_meeting_timeline(self, meeting_id: str) -> list[ExtractedEvent]:
        """Fetch chronological events extracted from a meeting."""
        stmt = (
            select(EventModel)
            .where(EventModel.meeting_id == meeting_id)
            .order_by(EventModel.occurred_at.asc(), EventModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedEvent(
                event_id=r.id,
                event_type=EventType(r.event_type),
                occurred_at=r.occurred_at,
                meeting_id=r.meeting_id,
                subject_entity_id=r.subject_entity_id,
                payload=r.payload_json or {},
                evidence_segment_id=r.evidence_segment_id,
            )
            for r in rows
        ]

    async def get_meeting_relations(self, meeting_id: str) -> list[ExtractedRelation]:
        """Fetch typed relationships extracted from a meeting."""
        stmt = (
            select(RelationshipModel)
            .where(RelationshipModel.meeting_id == meeting_id)
            .order_by(RelationshipModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            ExtractedRelation(
                relation_id=r.id,
                source_entity_id=r.source_entity_id,
                target_entity_id=r.target_entity_id,
                relationship_type=RelationType(r.relation_type),
                meeting_id=r.meeting_id,
                segment_id=r.segment_id,
                confidence=r.confidence,
            )
            for r in rows
        ]

    # --------------------------------------------------------------------------
    # Embeddings & Evidence Operations
    # --------------------------------------------------------------------------

    async def save_embeddings(
        self,
        meeting_id: str,
        embeddings: list[tuple[str, str, str, list[float]]],
    ) -> None:
        """Persist vector representations for transcript chunks or facts.

        Args:
            meeting_id: Meeting ID
            embeddings: List of (source_type, source_id, chunk_text, vector) tuples
        """
        await self.session.execute(
            delete(EmbeddingModel).where(EmbeddingModel.meeting_id == meeting_id)
        )
        for src_type, src_id, chunk_text, vec in embeddings:
            self.session.add(
                EmbeddingModel(
                    meeting_id=meeting_id,
                    source_type=src_type,
                    source_id=src_id,
                    chunk_text=chunk_text,
                    embedding_json=vec,
                )
            )
        await self.session.flush()

    async def save_evidence_records(
        self,
        meeting_id: str,
        evidence_items: list[EvidenceItem],
    ) -> None:
        """Persist provenance evidence items linking facts to transcript slices."""
        await self.session.execute(
            delete(EvidenceModel).where(EvidenceModel.meeting_id == meeting_id)
        )
        for evi in evidence_items:
            self.session.add(
                EvidenceModel(
                    meeting_id=meeting_id,
                    segment_id=evi.segment_id,
                    start_time=evi.start_time,
                    end_time=evi.end_time,
                    text_snapshot=evi.text_snapshot,
                    source_type=str(evi.source_type),
                )
            )
        await self.session.flush()

    async def get_evidence_records(self, meeting_id: str) -> list[EvidenceItem]:
        """Fetch all evidence records for a meeting."""
        stmt = (
            select(EvidenceModel)
            .where(EvidenceModel.meeting_id == meeting_id)
            .order_by(EvidenceModel.start_time.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            EvidenceItem(
                meeting_id=r.meeting_id,
                segment_id=r.segment_id,
                start_time=r.start_time,
                end_time=r.end_time,
                text_snapshot=r.text_snapshot,
                source_type=SourceType(r.source_type),
            )
            for r in rows
        ]

    # --------------------------------------------------------------------------
    # Job Operations
    # --------------------------------------------------------------------------

    async def create_job(
        self,
        job_id: str,
        meeting_id: str | None = None,
        stage: str = "initialized",
    ) -> JobModel:
        """Create a job tracking record."""
        job = JobModel(
            id=job_id,
            meeting_id=meeting_id,
            status=str(ProcessingStatus.QUEUED),
            stage=stage,
            progress=0.0,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_job(
        self,
        job_id: str,
        status: ProcessingStatus | str,
        stage: str | None = None,
        progress: float | None = None,
        error_message: str | None = None,
    ) -> JobModel | None:
        """Update job status, progress, stage, or error."""
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return None

        job.status = str(status.value if isinstance(status, ProcessingStatus) else status)
        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = progress
        if error_message is not None:
            job.error_message = error_message

        await self.session.flush()
        return job

    async def get_job(self, job_id: str) -> JobModel | None:
        """Fetch a job record by ID."""
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_audit_log(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Create and persist a security-sensitive operations audit log entry."""
        log = AuditLogModel(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            metadata_json=metadata_json,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_audit_logs(
        self,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogModel]:
        """Fetch audit log entries ordered by timestamp descending."""
        stmt = select(AuditLogModel)
        if actor_id:
            stmt = stmt.where(AuditLogModel.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        stmt = stmt.order_by(AuditLogModel.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
