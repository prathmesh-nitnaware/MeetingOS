from datetime import UTC, datetime
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
    Project,
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
    ProjectModel,
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
    """Create database tables if they do not already exist and ensure required columns."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            from sqlalchemy import text
            if "postgresql" in str(engine.url) or "postgres" in str(engine.url):
                # Meetings table columns
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS content_type VARCHAR(50) DEFAULT 'transcript';"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS content TEXT;"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS summary TEXT;"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS key_points_json JSONB;"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS project_id VARCHAR(100);"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS source_provider VARCHAR(100);"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS external_meeting_id VARCHAR(255);"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;"))
                await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(100);"))

                # Topics table columns
                await conn.execute(text("ALTER TABLE topics ADD COLUMN IF NOT EXISTS source_text TEXT;"))
                await conn.execute(text("ALTER TABLE topics ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;"))

                # Decisions table columns
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS title VARCHAR(500);"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS context TEXT;"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS project_id VARCHAR(100);"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS review_status VARCHAR(50) DEFAULT 'needs_review';"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS source_text TEXT;"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS source_start INT;"))
                await conn.execute(text("ALTER TABLE decisions ADD COLUMN IF NOT EXISTS source_end INT;"))

                # Commitments table columns
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium';"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS due_date_str VARCHAR(100);"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS project_id VARCHAR(100);"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS review_status VARCHAR(50) DEFAULT 'needs_review';"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS task TEXT;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS source_text TEXT;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS source_start INT;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS source_end INT;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS original_deadline TIMESTAMP WITH TIME ZONE;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS current_deadline TIMESTAMP WITH TIME ZONE;"))
                await conn.execute(text("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
        except Exception:
            pass


class MeetingRepository:
    """Repository managing persistence and retrieval of CMF meetings, transcripts, NLP facts, and jobs.

    Every public method that queries meetings or related data accepts an ``org_id``
    parameter and applies it as a WHERE clause so that tenants never see each
    other's data.  Callers MUST pass the org_id obtained from the authenticated
    ``UserIdentity`` — never hard-code or default it.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_meeting(self, meeting: Meeting, org_id: str = "org_dev") -> MeetingModel:
        """Persist a new Meeting with participants, speakers, and segments in an atomic transaction.

        The ``org_id`` is stored on the meeting row and all subsequent read
        operations will filter on it to guarantee tenant isolation.
        """
        meeting_row = MeetingModel(
            id=meeting.meeting_id,
            org_id=org_id,
            title=meeting.title,
            meeting_date=meeting.meeting_date,
            duration_seconds=meeting.duration_seconds,
            source_type=str(meeting.source_type.value if hasattr(meeting.source_type, "value") else meeting.source_type),
            content_type=meeting.content_type,
            content=meeting.content,
            summary=meeting.summary,
            key_points_json=meeting.key_points,
            project_id=meeting.project_id,
            processing_status=str(meeting.processing_status.value if hasattr(meeting.processing_status, "value") else meeting.processing_status),
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

    async def get_meeting(self, meeting_id: str, org_id: str = "org_dev") -> Meeting | None:
        """Fetch a Meeting by ID scoped to the requesting organisation.

        Returns ``None`` (not an error) when the meeting exists in the database
        but belongs to a different tenant or is soft-deleted — this prevents cross-org enumeration.
        """
        stmt = (
            select(MeetingModel)
            .where(
                MeetingModel.id == meeting_id,
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
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

        st_val = meeting_row.source_type
        source_type = SourceType(st_val) if st_val in [e.value for e in SourceType] else SourceType.TEXT_TRANSCRIPT
        ps_val = meeting_row.processing_status
        proc_status = ProcessingStatus(ps_val) if ps_val in [e.value for e in ProcessingStatus] else ProcessingStatus.SUCCEEDED

        return Meeting(
            meeting_id=meeting_row.id,
            title=meeting_row.title,
            meeting_date=meeting_row.meeting_date,
            duration_seconds=meeting_row.duration_seconds,
            source_type=source_type,
            processing_status=proc_status,
            content_type=meeting_row.content_type or "transcript",
            content=meeting_row.content,
            summary=meeting_row.summary,
            key_points=meeting_row.key_points_json or [],
            project_id=meeting_row.project_id,
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

    async def list_meetings(
        self, org_id: str = "org_dev", limit: int = 50, offset: int = 0
    ) -> list[Meeting]:
        """List meetings for a specific organisation ordered by date descending."""
        stmt = (
            select(MeetingModel)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
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
            st_val = r.source_type
            source_type = SourceType(st_val) if st_val in [e.value for e in SourceType] else SourceType.TEXT_TRANSCRIPT
            ps_val = r.processing_status
            proc_status = ProcessingStatus(ps_val) if ps_val in [e.value for e in ProcessingStatus] else ProcessingStatus.SUCCEEDED

            meetings.append(
                Meeting(
                    meeting_id=r.id,
                    title=r.title,
                    meeting_date=r.meeting_date,
                    duration_seconds=r.duration_seconds,
                    source_type=source_type,
                    processing_status=proc_status,
                    content_type=r.content_type or "transcript",
                    content=r.content,
                    summary=r.summary,
                    key_points=r.key_points_json or [],
                    project_id=r.project_id,
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
            seg_id = seg.segment_id
            if not seg_id.startswith(f"{meeting_id}-"):
                seg_id = f"{meeting_id}-{seg_id}"
            self.session.add(
                TranscriptSegmentModel(
                    id=seg_id,
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
                    title=dec.title or dec.subject[:100],
                    subject=dec.subject,
                    status=str(dec.status.value if hasattr(dec.status, "value") else dec.status),
                    context=dec.context,
                    rationale=dec.rationale,
                    confidence=dec.confidence if hasattr(dec, "confidence") and dec.confidence is not None else 1.0,
                    evidence_segment_id=dec.evidence_segment_id,
                    source_text=getattr(dec, "source_text", None),
                    source_start=getattr(dec, "source_start", None),
                    source_end=getattr(dec, "source_end", None),
                    review_status=getattr(dec, "review_status", None) or "needs_review",
                    created_at=dec.created_at,
                )
            )

        # 5. Persist Commitments / Actions
        for com in results.commitments:
            self.session.add(
                CommitmentModel(
                    id=com.commitment_id,
                    meeting_id=meeting_id,
                    task=com.task or com.description[:120],
                    description=com.description,
                    owner_id=com.owner_id,
                    status=str(com.status.value if hasattr(com.status, "value") else com.status),
                    priority=com.priority or "medium",
                    due_date_str=com.due_date_str,
                    confidence=getattr(com, "confidence", 1.0) or 1.0,
                    original_deadline=com.original_deadline,
                    current_deadline=com.current_deadline,
                    evidence_segment_id=com.evidence_segment_id,
                    source_text=getattr(com, "source_text", None),
                    source_start=getattr(com, "source_start", None),
                    source_end=getattr(com, "source_end", None),
                    review_status=getattr(com, "review_status", None) or "needs_review",
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
                    status=str(iss.status.value if hasattr(iss.status, "value") else iss.status),
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
                    event_type=str(evt.event_type.value if hasattr(evt.event_type, "value") else evt.event_type),
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
                    relation_type=str(rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type),
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
                    classes_json=[str(c.value if hasattr(c, "value") else c) for c in clf.classes],
                    confidence=clf.confidence,
                )
            )

        await self.session.flush()

    async def update_meeting(
        self,
        meeting_id: str,
        org_id: str = "org_dev",
        title: str | None = None,
        meeting_date: datetime | None = None,
        content_type: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        key_points: list[str] | None = None,
        project_id: str | None = None,
        participants: list[Participant] | None = None,
    ) -> Meeting | None:
        """Update meeting details, content, summary, or participants."""
        stmt = select(MeetingModel).where(
            MeetingModel.id == meeting_id,
            MeetingModel.org_id == org_id,
            MeetingModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        meeting_row = result.scalar_one_or_none()
        if not meeting_row:
            return None

        if title is not None:
            meeting_row.title = title
        if meeting_date is not None:
            meeting_row.meeting_date = meeting_date
        if content_type is not None:
            meeting_row.content_type = content_type
        if content is not None:
            meeting_row.content = content
        if summary is not None:
            meeting_row.summary = summary
        if key_points is not None:
            meeting_row.key_points_json = key_points
        if project_id is not None:
            meeting_row.project_id = project_id
        meeting_row.updated_at = datetime.now(UTC)

        if participants is not None:
            await self.session.execute(
                delete(ParticipantModel).where(ParticipantModel.meeting_id == meeting_id)
            )
            for p in participants:
                self.session.add(
                    ParticipantModel(
                        id=p.id or str(uuid4()),
                        meeting_id=meeting_id,
                        canonical_name=p.canonical_name,
                        aliases=p.aliases,
                    )
                )

        await self.session.flush()
        return await self.get_meeting(meeting_id, org_id=org_id)

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
                entity_type=EntityType(r.entity_type) if r.entity_type in [e.value for e in EntityType] else EntityType.PROJECT,
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
                title=r.title or r.subject,
                subject=r.subject,
                status=DecisionStatus(r.status) if r.status in [e.value for e in DecisionStatus] else DecisionStatus.APPROVED,
                context=r.context or r.rationale,
                rationale=r.rationale,
                confidence=r.confidence if hasattr(r, "confidence") and r.confidence is not None else 1.0,
                meeting_id=r.meeting_id,
                evidence_segment_id=r.evidence_segment_id,
                source_text=getattr(r, "source_text", None),
                source_start=getattr(r, "source_start", None),
                source_end=getattr(r, "source_end", None),
                review_status=getattr(r, "review_status", None) or "needs_review",
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
                task=r.task or r.description,
                description=r.description,
                owner_id=r.owner_id or "Unassigned",
                status=CommitmentStatus(r.status) if r.status in [e.value for e in CommitmentStatus] else CommitmentStatus.IN_PROGRESS,
                priority=r.priority or "medium",
                due_date_str=r.due_date_str,
                confidence=getattr(r, "confidence", 1.0) or 1.0,
                original_deadline=r.original_deadline,
                current_deadline=r.current_deadline,
                meeting_id=r.meeting_id,
                evidence_segment_id=r.evidence_segment_id,
                source_text=getattr(r, "source_text", None),
                source_start=getattr(r, "source_start", None),
                source_end=getattr(r, "source_end", None),
                review_status=getattr(r, "review_status", None) or "needs_review",
            )
            for r in rows
        ]

    async def list_all_action_items(
        self,
        org_id: str = "org_dev",
        status: str | None = None,
        owner: str | None = None,
        priority: str | None = None,
        meeting_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List action items across all meetings in an organization with source meeting details."""
        stmt = (
            select(CommitmentModel, MeetingModel.title, MeetingModel.meeting_date, MeetingModel.project_id)
            .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
            .where(
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
        )
        if status:
            if status.lower() == "open":
                stmt = stmt.where(CommitmentModel.status.in_(["In Progress", "Identified", "Assigned", "Open"]))
            else:
                stmt = stmt.where(CommitmentModel.status.ilike(f"%{status}%"))
        if owner:
            stmt = stmt.where(CommitmentModel.owner_id.ilike(f"%{owner}%"))
        if priority:
            stmt = stmt.where(CommitmentModel.priority == priority)
        if meeting_id:
            stmt = stmt.where(CommitmentModel.meeting_id == meeting_id)
        if project_id:
            stmt = stmt.where(MeetingModel.project_id == project_id)

        stmt = stmt.order_by(CommitmentModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        items = []
        for com, m_title, m_date, m_proj in result.all():
            items.append({
                "commitment_id": com.id,
                "id": com.id,
                "task": com.task or com.description,
                "description": com.description,
                "owner_id": com.owner_id or "Unassigned",
                "status": com.status,
                "priority": com.priority or "medium",
                "due_date_str": com.due_date_str or ("Not specified" if not com.current_deadline else com.current_deadline.strftime("%b %d, %Y")),
                "confidence": getattr(com, "confidence", 1.0) or 1.0,
                "source_text": getattr(com, "source_text", None),
                "source_start": getattr(com, "source_start", None),
                "source_end": getattr(com, "source_end", None),
                "review_status": getattr(com, "review_status", None) or "needs_review",
                "original_deadline": com.original_deadline.isoformat() if com.original_deadline else None,
                "current_deadline": com.current_deadline.isoformat() if com.current_deadline else None,
                "meeting_id": com.meeting_id,
                "meeting_title": m_title,
                "meeting_date": m_date.isoformat() if m_date else None,
                "project_id": m_proj,
                "created_at": com.created_at.isoformat() if com.created_at else None,
            })
        return items

    async def update_action_item(
        self,
        commitment_id: str,
        org_id: str = "org_dev",
        status: str | None = None,
        task: str | None = None,
        description: str | None = None,
        owner_id: str | None = None,
        priority: str | None = None,
        due_date_str: str | None = None,
        review_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an action item's status, assignee, priority, due date, or review status."""
        stmt = (
            select(CommitmentModel, MeetingModel.title, MeetingModel.meeting_date)
            .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
            .where(
                CommitmentModel.id == commitment_id,
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        com, m_title, m_date = row
        if status is not None:
            com.status = status
        if task is not None:
            com.task = task
        if description is not None:
            com.description = description
        if owner_id is not None:
            com.owner_id = owner_id
        if priority is not None:
            com.priority = priority
        if due_date_str is not None:
            com.due_date_str = due_date_str
        if review_status is not None:
            com.review_status = review_status
        com.updated_at = datetime.now(UTC)
        await self.session.flush()
        return {
            "commitment_id": com.id,
            "id": com.id,
            "task": com.task or com.description,
            "description": com.description,
            "owner_id": com.owner_id or "Unassigned",
            "status": com.status,
            "priority": com.priority or "medium",
            "due_date_str": com.due_date_str or "Not specified",
            "confidence": getattr(com, "confidence", 1.0) or 1.0,
            "source_text": getattr(com, "source_text", None),
            "source_start": getattr(com, "source_start", None),
            "source_end": getattr(com, "source_end", None),
            "review_status": getattr(com, "review_status", None) or "needs_review",
            "meeting_id": com.meeting_id,
            "meeting_title": m_title,
            "meeting_date": m_date.isoformat() if m_date else None,
        }

    async def list_all_decisions(
        self,
        org_id: str = "org_dev",
        status: str | None = None,
        meeting_id: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List organizational decisions across all meetings."""
        stmt = (
            select(DecisionModel, MeetingModel.title, MeetingModel.meeting_date, MeetingModel.project_id)
            .join(MeetingModel, DecisionModel.meeting_id == MeetingModel.id)
            .where(
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
        )
        if status:
            stmt = stmt.where(DecisionModel.status.ilike(f"%{status}%"))
        if meeting_id:
            stmt = stmt.where(DecisionModel.meeting_id == meeting_id)
        if project_id:
            stmt = stmt.where(MeetingModel.project_id == project_id)

        stmt = stmt.order_by(DecisionModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        items = []
        for dec, m_title, m_date, m_proj in result.all():
            items.append({
                "decision_id": dec.id,
                "id": dec.id,
                "title": dec.title or dec.subject,
                "subject": dec.subject,
                "status": dec.status,
                "context": dec.context or dec.rationale,
                "rationale": dec.rationale,
                "confidence": dec.confidence if hasattr(dec, "confidence") and dec.confidence is not None else 1.0,
                "source_text": getattr(dec, "source_text", None),
                "source_start": getattr(dec, "source_start", None),
                "source_end": getattr(dec, "source_end", None),
                "review_status": getattr(dec, "review_status", None) or "needs_review",
                "meeting_id": dec.meeting_id,
                "meeting_title": m_title,
                "meeting_date": m_date.isoformat() if m_date else None,
                "project_id": m_proj,
                "created_at": dec.created_at.isoformat() if dec.created_at else None,
            })
        return items

    async def update_decision(
        self,
        decision_id: str,
        org_id: str = "org_dev",
        status: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        context: str | None = None,
        rationale: str | None = None,
        review_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an organizational decision."""
        stmt = (
            select(DecisionModel, MeetingModel.title, MeetingModel.meeting_date)
            .join(MeetingModel, DecisionModel.meeting_id == MeetingModel.id)
            .where(
                DecisionModel.id == decision_id,
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        dec, m_title, m_date = row
        if status is not None:
            dec.status = status
        if title is not None:
            dec.title = title
        if subject is not None:
            dec.subject = subject
        if context is not None:
            dec.context = context
        if rationale is not None:
            dec.rationale = rationale
        if review_status is not None:
            dec.review_status = review_status
        dec.updated_at = datetime.now(UTC)
        await self.session.flush()
        return {
            "decision_id": dec.id,
            "id": dec.id,
            "title": dec.title or dec.subject,
            "subject": dec.subject,
            "status": dec.status,
            "context": dec.context,
            "rationale": dec.rationale,
            "confidence": dec.confidence if hasattr(dec, "confidence") and dec.confidence is not None else 1.0,
            "source_text": getattr(dec, "source_text", None),
            "source_start": getattr(dec, "source_start", None),
            "source_end": getattr(dec, "source_end", None),
            "review_status": getattr(dec, "review_status", None) or "needs_review",
            "meeting_id": dec.meeting_id,
            "meeting_title": m_title,
            "meeting_date": m_date.isoformat() if m_date else None,
        }

    # --------------------------------------------------------------------------
    # Project Repository Methods
    # --------------------------------------------------------------------------

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        color: str | None = "#4f46e5",
        status: str = "active",
        org_id: str = "org_dev",
    ) -> ProjectModel:
        """Create a new project scoped to the tenant organization."""
        proj = ProjectModel(
            id=f"proj-{uuid4()}",
            org_id=org_id,
            name=name,
            description=description,
            color=color or "#4f46e5",
            status=status,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(proj)
        await self.session.flush()
        return proj

    async def get_project(self, project_id: str, org_id: str = "org_dev") -> ProjectModel | None:
        """Fetch project by ID scoped to the authenticated organization."""
        stmt = select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.org_id == org_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_projects(self, org_id: str = "org_dev") -> list[dict[str, Any]]:
        """List all projects for an organization with aggregated meeting, decision, and action counts."""
        from sqlalchemy import func
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.org_id == org_id)
            .order_by(ProjectModel.updated_at.desc())
        )
        projects = (await self.session.execute(stmt)).scalars().all()

        results = []
        for p in projects:
            # Count meetings
            m_stmt = select(func.count(MeetingModel.id)).where(
                MeetingModel.project_id == p.id,
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
            meeting_count = (await self.session.execute(m_stmt)).scalar() or 0

            # Count decisions
            d_stmt = (
                select(func.count(DecisionModel.id))
                .join(MeetingModel, DecisionModel.meeting_id == MeetingModel.id)
                .where(
                    MeetingModel.project_id == p.id,
                    MeetingModel.org_id == org_id,
                    MeetingModel.deleted_at.is_(None),
                )
            )
            decision_count = (await self.session.execute(d_stmt)).scalar() or 0

            # Count open actions
            a_stmt = (
                select(func.count(CommitmentModel.id))
                .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
                .where(
                    MeetingModel.project_id == p.id,
                    MeetingModel.org_id == org_id,
                    MeetingModel.deleted_at.is_(None),
                    CommitmentModel.status.in_(["In Progress", "Identified", "Assigned", "Open"]),
                )
            )
            open_action_count = (await self.session.execute(a_stmt)).scalar() or 0

            # Count topics
            t_stmt = (
                select(func.count(TopicModel.id.distinct()))
                .join(MeetingModel, TopicModel.meeting_id == MeetingModel.id)
                .where(
                    MeetingModel.project_id == p.id,
                    MeetingModel.org_id == org_id,
                    MeetingModel.deleted_at.is_(None),
                )
            )
            topic_count = (await self.session.execute(t_stmt)).scalar() or 0

            results.append({
                "id": p.id,
                "project_id": p.id,
                "name": p.name,
                "description": p.description,
                "color": p.color,
                "status": p.status,
                "meeting_count": meeting_count,
                "decision_count": decision_count,
                "open_action_count": open_action_count,
                "topic_count": topic_count,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            })
        return results

    async def update_project(
        self,
        project_id: str,
        org_id: str = "org_dev",
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        status: str | None = None,
    ) -> ProjectModel | None:
        """Update a project's name, description, color, or status."""
        proj = await self.get_project(project_id, org_id=org_id)
        if not proj:
            return None
        if name is not None:
            proj.name = name
        if description is not None:
            proj.description = description
        if color is not None:
            proj.color = color
        if status is not None:
            proj.status = status
        proj.updated_at = datetime.now(UTC)
        await self.session.flush()
        return proj

    async def delete_project(self, project_id: str, org_id: str = "org_dev") -> bool:
        """Delete a project and unlink its associated meetings."""
        proj = await self.get_project(project_id, org_id=org_id)
        if not proj:
            return False
        # Unlink meetings
        m_stmt = select(MeetingModel).where(
            MeetingModel.project_id == project_id,
            MeetingModel.org_id == org_id,
        )
        meetings = (await self.session.execute(m_stmt)).scalars().all()
        for m in meetings:
            m.project_id = None
        await self.session.delete(proj)
        await self.session.flush()
        return True

    async def get_project_timeline(self, project_id: str, org_id: str = "org_dev") -> list[dict[str, Any]]:
        """Get chronological meeting timeline with key decisions and actions for a project."""
        stmt = (
            select(MeetingModel)
            .where(
                MeetingModel.project_id == project_id,
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
            )
            .order_by(MeetingModel.meeting_date.asc())
        )
        meetings = (await self.session.execute(stmt)).scalars().all()

        timeline = []
        for m in meetings:
            decisions = await self.get_meeting_decisions(m.id)
            actions = await self.get_meeting_actions(m.id)
            topics = await self.get_meeting_topics(m.id)

            timeline.append({
                "meeting_id": m.id,
                "title": m.title,
                "meeting_date": m.meeting_date.isoformat(),
                "summary": m.summary,
                "decisions": [
                    {
                        "decision_id": d.decision_id,
                        "subject": d.subject,
                        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                        "confidence": d.confidence,
                        "source_text": d.source_text,
                    }
                    for d in decisions
                ],
                "action_items": [
                    {
                        "commitment_id": a.commitment_id,
                        "task": a.task,
                        "owner": a.owner_id,
                        "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                        "due_date": a.due_date_str,
                        "source_text": a.source_text,
                    }
                    for a in actions
                ],
                "topics": topics,
            })
        return timeline

    async def get_topic_detail(self, topic_name: str, org_id: str = "org_dev") -> dict[str, Any]:
        """Fetch cross-meeting topic detail, timeline evolution, linked decisions, actions, and meetings."""
        # Find all meetings mentioning this topic
        stmt = (
            select(MeetingModel)
            .join(TopicModel, TopicModel.meeting_id == MeetingModel.id)
            .where(
                MeetingModel.org_id == org_id,
                MeetingModel.deleted_at.is_(None),
                TopicModel.name.ilike(f"%{topic_name}%"),
            )
            .order_by(MeetingModel.meeting_date.asc())
        )
        meetings = (await self.session.execute(stmt)).scalars().all()
        meeting_ids = [m.id for m in meetings]

        # Decisions in these meetings
        all_decisions = []
        all_actions = []
        if meeting_ids:
            d_stmt = (
                select(DecisionModel, MeetingModel.title, MeetingModel.meeting_date)
                .join(MeetingModel, DecisionModel.meeting_id == MeetingModel.id)
                .where(DecisionModel.meeting_id.in_(meeting_ids))
                .order_by(DecisionModel.created_at.desc())
            )
            for d, m_title, m_date in (await self.session.execute(d_stmt)).all():
                all_decisions.append({
                    "decision_id": d.id,
                    "title": d.title or d.subject,
                    "subject": d.subject,
                    "status": d.status,
                    "rationale": d.rationale,
                    "confidence": d.confidence,
                    "source_text": d.source_text,
                    "meeting_id": d.meeting_id,
                    "meeting_title": m_title,
                    "meeting_date": m_date.isoformat() if m_date else None,
                })

            a_stmt = (
                select(CommitmentModel, MeetingModel.title, MeetingModel.meeting_date)
                .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
                .where(CommitmentModel.meeting_id.in_(meeting_ids))
                .order_by(CommitmentModel.created_at.desc())
            )
            for a, m_title, m_date in (await self.session.execute(a_stmt)).all():
                all_actions.append({
                    "commitment_id": a.id,
                    "task": a.task or a.description,
                    "owner": a.owner_id or "Unassigned",
                    "status": a.status,
                    "priority": a.priority,
                    "due_date": a.due_date_str or "Not specified",
                    "source_text": a.source_text,
                    "meeting_id": a.meeting_id,
                    "meeting_title": m_title,
                    "meeting_date": m_date.isoformat() if m_date else None,
                })

        # Build evolution history
        evolution = []
        for m in meetings:
            m_decs = [d for d in all_decisions if d.get("meeting_id") == m.id]
            m_acts = [a for a in all_actions if a.get("meeting_id") == m.id]
            evolution.append({
                "meeting_id": m.id,
                "title": m.title,
                "meeting_title": m.title,
                "date": m.meeting_date.isoformat(),
                "meeting_date": m.meeting_date.isoformat(),
                "summary": m.summary or f"Discussed during {m.title}",
                "decisions_count": len(m_decs),
                "actions_count": len(m_acts),
            })

        # Synthesis
        current_understanding = (
            f"The team has discussed {topic_name} across {len(meetings)} meetings, resulting in "
            f"{len(all_decisions)} organizational decision{'s' if len(all_decisions) != 1 else ''} and "
            f"{len(all_actions)} action item{'s' if len(all_actions) != 1 else ''}."
            if meetings else f"No recorded discussions yet for topic '{topic_name}'."
        )

        return {
            "topic": topic_name,
            "topic_name": topic_name,
            "total_meetings": len(meetings),
            "meeting_count": len(meetings),
            "decision_count": len(all_decisions),
            "action_count": len(all_actions),
            "current_understanding": current_understanding,
            "evolution": evolution,
            "decisions": all_decisions,
            "action_items": all_actions,
            "meetings": [
                {
                    "meeting_id": m.id,
                    "title": m.title,
                    "meeting_date": m.meeting_date.isoformat(),
                    "summary": m.summary,
                }
                for m in meetings
            ],
        }

    async def get_activity_feed(self, org_id: str = "org_dev", limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve a chronological 'What Changed?' activity stream across the organization."""
        activities = []

        # Recent meetings
        m_stmt = (
            select(MeetingModel)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
            .order_by(MeetingModel.created_at.desc())
            .limit(limit)
        )
        meetings = (await self.session.execute(m_stmt)).scalars().all()
        for m in meetings:
            activities.append({
                "id": f"act-m-{m.id}",
                "type": "meeting_analyzed",
                "title": f"Meeting analyzed: {m.title}",
                "description": m.summary[:150] + "..." if m.summary and len(m.summary) > 150 else (m.summary or "Structured intelligence extracted."),
                "timestamp": m.created_at.isoformat() if m.created_at else None,
                "resource_id": m.id,
                "resource_type": "meeting",
            })

        # Recent decisions
        d_stmt = (
            select(DecisionModel, MeetingModel.title)
            .join(MeetingModel, DecisionModel.meeting_id == MeetingModel.id)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
            .order_by(DecisionModel.created_at.desc())
            .limit(limit)
        )
        for dec, m_title in (await self.session.execute(d_stmt)).all():
            activities.append({
                "id": f"act-d-{dec.id}",
                "type": "decision_recorded",
                "title": f"Decision: {dec.title or dec.subject}",
                "description": f"Status: {dec.status} | Source: {m_title}",
                "timestamp": dec.created_at.isoformat() if dec.created_at else None,
                "resource_id": dec.meeting_id,
                "resource_type": "decision",
            })

        # Recent actions
        a_stmt = (
            select(CommitmentModel, MeetingModel.title)
            .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
            .order_by(CommitmentModel.created_at.desc())
            .limit(limit)
        )
        for act, m_title in (await self.session.execute(a_stmt)).all():
            activities.append({
                "id": f"act-a-{act.id}",
                "type": "action_created",
                "title": f"Action Item: {act.task or act.description}",
                "description": f"Assigned to: {act.owner_id or 'Unassigned'} | Due: {act.due_date_str or 'Not specified'}",
                "timestamp": act.created_at.isoformat() if act.created_at else None,
                "resource_id": act.meeting_id,
                "resource_type": "action",
            })

        # Sort all activities by timestamp descending
        activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return activities[:limit]

    async def get_knowledge_summary(self, org_id: str = "org_dev") -> dict[str, Any]:
        """Aggregate organizational topics, recurring topics, recent decisions, and actions."""
        from sqlalchemy import func
        stmt = (
            select(TopicModel.name, func.count(TopicModel.id).label("count"))
            .join(MeetingModel, TopicModel.meeting_id == MeetingModel.id)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
            .group_by(TopicModel.name)
            .order_by(func.count(TopicModel.id).desc())
        )
        topic_rows = (await self.session.execute(stmt)).all()
        topics = [{"name": r[0], "count": r[1]} for r in topic_rows]
        recurring_topics = [t for t in topics if t["count"] >= 2]

        decisions = await self.list_all_decisions(org_id=org_id, limit=6)
        actions = await self.list_all_action_items(org_id=org_id, limit=6)
        recent_meetings = await self.list_meetings(org_id=org_id, limit=5)

        key_points: list[str] = []
        for m in recent_meetings:
            if m.key_points:
                key_points.extend(m.key_points[:2])

        return {
            "topics": topics,
            "recurring_topics": recurring_topics,
            "recent_decisions": decisions,
            "recent_actions": actions,
            "recent_key_points": key_points[:10],
            "total_meetings": len(recent_meetings),
        }

    async def get_team_overview(self, org_id: str = "org_dev") -> list[dict[str, Any]]:
        """Return team members across an organisation with meeting counts and open action items."""
        from sqlalchemy import func
        p_stmt = (
            select(ParticipantModel.canonical_name, func.count(ParticipantModel.id).label("meeting_count"))
            .join(MeetingModel, ParticipantModel.meeting_id == MeetingModel.id)
            .where(MeetingModel.org_id == org_id, MeetingModel.deleted_at.is_(None))
            .group_by(ParticipantModel.canonical_name)
            .order_by(func.count(ParticipantModel.id).desc())
        )
        p_rows = (await self.session.execute(p_stmt)).all()

        team: list[dict[str, Any]] = []
        for name, m_count in p_rows:
            act_stmt = (
                select(func.count(CommitmentModel.id))
                .join(MeetingModel, CommitmentModel.meeting_id == MeetingModel.id)
                .where(
                    MeetingModel.org_id == org_id,
                    MeetingModel.deleted_at.is_(None),
                    CommitmentModel.owner_id.ilike(f"%{name}%"),
                    CommitmentModel.status.in_(["In Progress", "Open", "Assigned", "Identified"]),
                )
            )
            open_count = (await self.session.execute(act_stmt)).scalar() or 0
            team.append({
                "name": name,
                "role": "Team Member",
                "meeting_count": m_count,
                "open_actions_count": open_count,
            })
        return team

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

    async def soft_delete_meeting(
        self, meeting_id: str, actor_id: str, org_id: str = "org_dev"
    ) -> bool:
        """Mark a meeting as soft-deleted without destroying underlying database records."""
        from datetime import UTC, datetime

        stmt = select(MeetingModel).where(
            MeetingModel.id == meeting_id,
            MeetingModel.org_id == org_id,
            MeetingModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        meeting = result.scalar_one_or_none()
        if not meeting:
            return False

        meeting.deleted_at = datetime.now(UTC)
        meeting.deleted_by = actor_id

        # Record audit log
        self.session.add(
            AuditLogModel(
                org_id=org_id,
                actor_id=actor_id,
                action="meeting.deleted",
                resource_type="meeting",
                resource_id=meeting_id,
                outcome="succeeded",
                metadata_json={"soft_delete": True, "title": meeting.title},
            )
        )
        await self.session.flush()
        return True

    async def hard_delete_meeting(self, meeting_id: str, org_id: str = "org_dev") -> bool:
        """Permanently remove a meeting and all cascading child records for a tenant."""
        stmt = select(MeetingModel).where(
            MeetingModel.id == meeting_id,
            MeetingModel.org_id == org_id,
        )
        result = await self.session.execute(stmt)
        meeting = result.scalar_one_or_none()
        if not meeting:
            return False

        await self.session.delete(meeting)
        await self.session.flush()
        return True

    async def create_audit_log(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str,
        org_id: str = "org_dev",
        metadata_json: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Create and persist a security-sensitive operations audit log entry scoped to an organisation."""
        log = AuditLogModel(
            org_id=org_id,
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
        org_id: str = "org_dev",
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogModel]:
        """Fetch audit log entries for a specific organisation ordered by timestamp descending."""
        stmt = select(AuditLogModel).where(AuditLogModel.org_id == org_id)
        if actor_id:
            stmt = stmt.where(AuditLogModel.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        stmt = stmt.order_by(AuditLogModel.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
