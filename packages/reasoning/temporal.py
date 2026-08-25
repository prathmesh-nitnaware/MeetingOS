from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from packages.common.enums import (
    CommitmentStatus,
    DecisionStatus,
    EventType,
    IssueStatus,
)
from packages.common.models import (
    ExtractedCommitment,
    ExtractedDecision,
    ExtractedIssue,
)
from packages.memory.models import (
    CommitmentModel,
    DecisionModel,
    EventModel,
    IssueModel,
    MeetingModel,
)
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class TimelineEventItem(BaseModel):
    event_id: str
    event_type: EventType
    occurred_at: datetime
    meeting_id: str
    meeting_title: str | None = None
    subject_entity_id: str | None = None
    payload: dict[str, Any] | None = None
    evidence_segment_id: str | None = None


class DecisionHistoryItem(BaseModel):
    decision: ExtractedDecision
    status: DecisionStatus
    meeting_id: str
    meeting_title: str
    meeting_date: datetime
    events: list[TimelineEventItem] = Field(default_factory=list)


class CommitmentHistoryItem(BaseModel):
    commitment: ExtractedCommitment
    status: CommitmentStatus
    original_deadline: datetime | None = None
    current_deadline: datetime | None = None
    deadline_changes_count: int = 0
    events: list[TimelineEventItem] = Field(default_factory=list)


class IssueHistoryItem(BaseModel):
    issue: ExtractedIssue
    status: IssueStatus
    first_detected_at: datetime
    last_mentioned_at: datetime
    meetings_count: int = 1
    is_recurring: bool = False
    is_resolved: bool = False
    events: list[TimelineEventItem] = Field(default_factory=list)


class EntityTimelineResponse(BaseModel):
    entity_id: str
    events: list[TimelineEventItem] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    commitments: list[ExtractedCommitment] = Field(default_factory=list)
    issues: list[ExtractedIssue] = Field(default_factory=list)


class TemporalReconciliationResult(BaseModel):
    meeting_id: str
    decision_changes_detected: int = 0
    deadline_changes_detected: int = 0
    recurring_issues_detected: int = 0
    events_created: int = 0


class TemporalIntelligenceEngine:
    """Engine providing decision lifecycle tracking, slippage detection, recurring issue analysis, and timeline reconstruction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reconcile_meeting_lifecycle(self, meeting_id: str) -> TemporalReconciliationResult:
        """Analyze a newly ingested meeting against prior meeting history to detect cross-meeting changes."""
        # 1. Fetch current meeting and its date
        current_meeting_stmt = select(MeetingModel).where(MeetingModel.id == meeting_id)
        current_meeting = (await self.session.execute(current_meeting_stmt)).scalar_one_or_none()
        if not current_meeting:
            return TemporalReconciliationResult(meeting_id=meeting_id)

        m_date = current_meeting.meeting_date or datetime.now(UTC)

        dec_changes = 0
        deadline_changes = 0
        recurring_issues = 0
        events_created = 0

        # 2. Reconcile Decisions (Modifications & Reversals)
        cur_decisions = list(
            (
                await self.session.execute(
                    select(DecisionModel).where(DecisionModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )

        prior_decisions = list(
            (
                await self.session.execute(
                    select(DecisionModel).where(DecisionModel.meeting_id != meeting_id)
                )
            )
            .scalars()
            .all()
        )

        for cur_dec in cur_decisions:
            cur_sub = cur_dec.subject.lower()
            for prior_dec in prior_decisions:
                prior_sub = prior_dec.subject.lower()

                # Check if this decision reverses or replaces a prior decision
                if any(
                    w in cur_sub
                    for w in [
                        "replaces",
                        "switch from",
                        "revert",
                        "abandon",
                        "reversal",
                        "instead of",
                    ]
                ) and any(tok in cur_sub for tok in prior_sub.split() if len(tok) > 4):
                    prior_dec.status = str(DecisionStatus.REVERSED)
                    cur_dec.status = str(DecisionStatus.APPROVED)
                    dec_changes += 1

                    # Record DECISION_REVERSED event
                    self.session.add(
                        EventModel(
                            id=f"evt-{uuid4()}",
                            meeting_id=meeting_id,
                            event_type=str(EventType.DECISION_REVERSED),
                            occurred_at=m_date,
                            subject_entity_id=prior_dec.id,
                            payload_json={
                                "prior_decision_id": prior_dec.id,
                                "prior_subject": prior_dec.subject,
                                "new_decision_id": cur_dec.id,
                                "new_subject": cur_dec.subject,
                                "reason": cur_dec.rationale or cur_dec.subject,
                            },
                            evidence_segment_id=cur_dec.evidence_segment_id,
                        )
                    )
                    events_created += 1

                elif prior_sub in cur_sub or cur_sub in prior_sub:
                    if cur_dec.status != prior_dec.status and prior_dec.status != str(
                        DecisionStatus.REVERSED
                    ):
                        prior_dec.status = str(DecisionStatus.MODIFIED)
                        dec_changes += 1
                        self.session.add(
                            EventModel(
                                id=f"evt-{uuid4()}",
                                meeting_id=meeting_id,
                                event_type=str(EventType.DECISION_MODIFIED),
                                occurred_at=m_date,
                                subject_entity_id=prior_dec.id,
                                payload_json={
                                    "prior_decision_id": prior_dec.id,
                                    "new_decision_id": cur_dec.id,
                                    "new_status": cur_dec.status,
                                },
                                evidence_segment_id=cur_dec.evidence_segment_id,
                            )
                        )
                        events_created += 1

        # 3. Reconcile Commitments (Deadline Changes & Slippage)
        cur_commitments = list(
            (
                await self.session.execute(
                    select(CommitmentModel).where(CommitmentModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )

        prior_commitments = list(
            (
                await self.session.execute(
                    select(CommitmentModel).where(CommitmentModel.meeting_id != meeting_id)
                )
            )
            .scalars()
            .all()
        )

        for cur_com in cur_commitments:
            cur_desc = cur_com.description.lower()
            for prior_com in prior_commitments:
                prior_desc = prior_com.description.lower()
                # If same action description / task keywords
                common_tokens = [t for t in cur_desc.split() if len(t) > 3 and t in prior_desc]
                if len(common_tokens) >= 2 or cur_desc == prior_desc:
                    if (
                        cur_com.current_deadline
                        and prior_com.current_deadline
                        and cur_com.current_deadline != prior_com.current_deadline
                    ):
                        # Deadline changed
                        deadline_changes += 1
                        old_dl = prior_com.current_deadline
                        new_dl = cur_com.current_deadline
                        prior_com.current_deadline = new_dl
                        if new_dl > old_dl:
                            prior_com.status = str(CommitmentStatus.OVERDUE)

                        self.session.add(
                            EventModel(
                                id=f"evt-{uuid4()}",
                                meeting_id=meeting_id,
                                event_type=str(EventType.DEADLINE_CHANGED),
                                occurred_at=m_date,
                                subject_entity_id=prior_com.id,
                                payload_json={
                                    "commitment_id": prior_com.id,
                                    "previous_deadline": old_dl.isoformat(),
                                    "new_deadline": new_dl.isoformat(),
                                    "owner_id": cur_com.owner_id or prior_com.owner_id,
                                    "description": cur_com.description,
                                },
                                evidence_segment_id=cur_com.evidence_segment_id,
                            )
                        )
                        events_created += 1

        # 4. Reconcile Issues (Recurring & Unresolved Tracking)
        cur_issues = list(
            (
                await self.session.execute(
                    select(IssueModel).where(IssueModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )

        prior_issues = list(
            (
                await self.session.execute(
                    select(IssueModel).where(IssueModel.meeting_id != meeting_id)
                )
            )
            .scalars()
            .all()
        )

        for cur_iss in cur_issues:
            cur_desc = cur_iss.description.lower()
            for prior_iss in prior_issues:
                prior_desc = prior_iss.description.lower()
                common_tokens = [t for t in cur_desc.split() if len(t) > 3 and t in prior_desc]
                if len(common_tokens) >= 2 or cur_desc == prior_desc:
                    if (
                        cur_iss.status == str(IssueStatus.RESOLVED)
                        or "resolved" in cur_desc
                        or "fixed" in cur_desc
                    ):
                        prior_iss.status = str(IssueStatus.RESOLVED)
                        prior_iss.resolution_meeting_id = meeting_id
                        prior_iss.last_mentioned_at = m_date
                        self.session.add(
                            EventModel(
                                id=f"evt-{uuid4()}",
                                meeting_id=meeting_id,
                                event_type=str(EventType.ISSUE_RESOLVED),
                                occurred_at=m_date,
                                subject_entity_id=prior_iss.id,
                                payload_json={
                                    "issue_id": prior_iss.id,
                                    "description": prior_iss.description,
                                    "resolution_meeting_id": meeting_id,
                                },
                                evidence_segment_id=cur_iss.evidence_segment_id,
                            )
                        )
                        events_created += 1
                    else:
                        # Recurring issue across multiple meetings
                        prior_iss.status = str(IssueStatus.RECURRING)
                        prior_iss.last_mentioned_at = m_date
                        cur_iss.status = str(IssueStatus.RECURRING)
                        recurring_issues += 1
                        self.session.add(
                            EventModel(
                                id=f"evt-{uuid4()}",
                                meeting_id=meeting_id,
                                event_type=str(EventType.ISSUE_DETECTED),
                                occurred_at=m_date,
                                subject_entity_id=prior_iss.id,
                                payload_json={
                                    "issue_id": prior_iss.id,
                                    "description": prior_iss.description,
                                    "status": "Recurring",
                                    "first_detected_at": prior_iss.first_detected_at.isoformat(),
                                    "last_mentioned_at": m_date.isoformat(),
                                },
                                evidence_segment_id=cur_iss.evidence_segment_id,
                            )
                        )
                        events_created += 1

        await self.session.flush()

        return TemporalReconciliationResult(
            meeting_id=meeting_id,
            decision_changes_detected=dec_changes,
            deadline_changes_detected=deadline_changes,
            recurring_issues_detected=recurring_issues,
            events_created=events_created,
        )

    async def get_global_timeline(
        self,
        entity_id: str | None = None,
        event_type: EventType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TimelineEventItem]:
        """Fetch chronologically ordered events across organizational history."""
        stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .order_by(EventModel.occurred_at.asc(), EventModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        if entity_id:
            stmt = stmt.where(
                or_(
                    EventModel.subject_entity_id == entity_id,
                    EventModel.payload_json.ilike(f"%{entity_id}%"),
                )
            )
        if event_type:
            stmt = stmt.where(EventModel.event_type == str(event_type))
        if start_date:
            stmt = stmt.where(EventModel.occurred_at >= start_date)
        if end_date:
            stmt = stmt.where(EventModel.occurred_at <= end_date)

        rows = (await self.session.execute(stmt)).all()
        events: list[TimelineEventItem] = []
        for evt, m_title in rows:
            events.append(
                TimelineEventItem(
                    event_id=evt.id,
                    event_type=EventType(evt.event_type),
                    occurred_at=evt.occurred_at,
                    meeting_id=evt.meeting_id,
                    meeting_title=m_title,
                    subject_entity_id=evt.subject_entity_id,
                    payload=evt.payload_json,
                    evidence_segment_id=evt.evidence_segment_id,
                )
            )
        return events

    async def reconstruct_decision_history(self, decision_id: str) -> DecisionHistoryItem | None:
        """Reconstruct the end-to-end lifecycle history of a decision."""
        stmt = (
            select(DecisionModel, MeetingModel)
            .join(MeetingModel, MeetingModel.id == DecisionModel.meeting_id)
            .where(DecisionModel.id == decision_id)
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            return None

        dec, m = row
        # Fetch associated events
        e_stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .where(
                or_(
                    EventModel.subject_entity_id == decision_id,
                    EventModel.payload_json.ilike(f"%{decision_id}%"),
                )
            )
            .order_by(EventModel.occurred_at.asc())
        )
        e_rows = (await self.session.execute(e_stmt)).all()
        events = [
            TimelineEventItem(
                event_id=e.id,
                event_type=EventType(e.event_type),
                occurred_at=e.occurred_at,
                meeting_id=e.meeting_id,
                meeting_title=title,
                subject_entity_id=e.subject_entity_id,
                payload=e.payload_json,
                evidence_segment_id=e.evidence_segment_id,
            )
            for e, title in e_rows
        ]

        return DecisionHistoryItem(
            decision=ExtractedDecision(
                decision_id=dec.id,
                subject=dec.subject,
                status=DecisionStatus(dec.status),
                rationale=dec.rationale,
                meeting_id=dec.meeting_id,
                evidence_segment_id=dec.evidence_segment_id,
                created_at=dec.created_at,
            ),
            status=DecisionStatus(dec.status),
            meeting_id=dec.meeting_id,
            meeting_title=m.title,
            meeting_date=m.meeting_date,
            events=events,
        )

    async def reconstruct_commitment_history(
        self, commitment_id: str
    ) -> CommitmentHistoryItem | None:
        """Reconstruct deadline and assignment history of a commitment."""
        stmt = select(CommitmentModel).where(CommitmentModel.id == commitment_id)
        com = (await self.session.execute(stmt)).scalar_one_or_none()
        if not com:
            return None

        e_stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .where(
                or_(
                    EventModel.subject_entity_id == commitment_id,
                    EventModel.payload_json.ilike(f"%{commitment_id}%"),
                )
            )
            .order_by(EventModel.occurred_at.asc())
        )
        e_rows = (await self.session.execute(e_stmt)).all()
        events = [
            TimelineEventItem(
                event_id=e.id,
                event_type=EventType(e.event_type),
                occurred_at=e.occurred_at,
                meeting_id=e.meeting_id,
                meeting_title=title,
                subject_entity_id=e.subject_entity_id,
                payload=e.payload_json,
                evidence_segment_id=e.evidence_segment_id,
            )
            for e, title in e_rows
        ]

        dl_changes = sum(1 for e in events if e.event_type == EventType.DEADLINE_CHANGED)

        return CommitmentHistoryItem(
            commitment=ExtractedCommitment(
                commitment_id=com.id,
                description=com.description,
                owner_id=com.owner_id,
                status=CommitmentStatus(com.status),
                original_deadline=com.original_deadline,
                current_deadline=com.current_deadline,
                meeting_id=com.meeting_id,
                evidence_segment_id=com.evidence_segment_id,
            ),
            status=CommitmentStatus(com.status),
            original_deadline=com.original_deadline,
            current_deadline=com.current_deadline,
            deadline_changes_count=dl_changes,
            events=events,
        )

    async def reconstruct_issue_history(self, issue_id: str) -> IssueHistoryItem | None:
        """Reconstruct detection and resolution lifecycle of an issue."""
        stmt = select(IssueModel).where(IssueModel.id == issue_id)
        iss = (await self.session.execute(stmt)).scalar_one_or_none()
        if not iss:
            return None

        e_stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .where(
                or_(
                    EventModel.subject_entity_id == issue_id,
                    EventModel.payload_json.ilike(f"%{issue_id}%"),
                )
            )
            .order_by(EventModel.occurred_at.asc())
        )
        e_rows = (await self.session.execute(e_stmt)).all()
        events = [
            TimelineEventItem(
                event_id=e.id,
                event_type=EventType(e.event_type),
                occurred_at=e.occurred_at,
                meeting_id=e.meeting_id,
                meeting_title=title,
                subject_entity_id=e.subject_entity_id,
                payload=e.payload_json,
                evidence_segment_id=e.evidence_segment_id,
            )
            for e, title in e_rows
        ]

        m_ids = {e.meeting_id for e in events}
        m_ids.add(iss.meeting_id)

        return IssueHistoryItem(
            issue=ExtractedIssue(
                issue_id=iss.id,
                description=iss.description,
                owner_id=iss.owner_id,
                status=IssueStatus(iss.status),
                first_detected_at=iss.first_detected_at,
                last_mentioned_at=iss.last_mentioned_at or iss.first_detected_at,
                resolution_meeting_id=iss.resolution_meeting_id,
                evidence_segment_id=iss.evidence_segment_id,
            ),
            status=IssueStatus(iss.status),
            first_detected_at=iss.first_detected_at,
            last_mentioned_at=iss.last_mentioned_at or iss.first_detected_at,
            meetings_count=len(m_ids),
            is_recurring=iss.status == str(IssueStatus.RECURRING) or len(m_ids) > 1,
            is_resolved=iss.status == str(IssueStatus.RESOLVED),
            events=events,
        )

    async def reconstruct_entity_timeline(self, entity_id: str) -> EntityTimelineResponse:
        """Reconstruct unified chronological stream of all events and facts involving an entity."""
        events = await self.get_global_timeline(entity_id=entity_id, limit=100)

        # Related decisions (via relations or direct mention)
        dec_stmt = select(DecisionModel).where(DecisionModel.subject.ilike(f"%{entity_id}%"))
        dec_rows = (await self.session.execute(dec_stmt)).scalars().all()
        decisions = [
            ExtractedDecision(
                decision_id=d.id,
                subject=d.subject,
                status=DecisionStatus(d.status),
                rationale=d.rationale,
                meeting_id=d.meeting_id,
                evidence_segment_id=d.evidence_segment_id,
                created_at=d.created_at,
            )
            for d in dec_rows
        ]

        # Related commitments
        com_stmt = select(CommitmentModel).where(
            or_(
                CommitmentModel.owner_id.ilike(f"%{entity_id}%"),
                CommitmentModel.description.ilike(f"%{entity_id}%"),
            )
        )
        com_rows = (await self.session.execute(com_stmt)).scalars().all()
        commitments = [
            ExtractedCommitment(
                commitment_id=c.id,
                description=c.description,
                owner_id=c.owner_id,
                status=CommitmentStatus(c.status),
                original_deadline=c.original_deadline,
                current_deadline=c.current_deadline,
                meeting_id=c.meeting_id,
                evidence_segment_id=c.evidence_segment_id,
            )
            for c in com_rows
        ]

        # Related issues
        iss_stmt = select(IssueModel).where(
            or_(
                IssueModel.owner_id.ilike(f"%{entity_id}%"),
                IssueModel.description.ilike(f"%{entity_id}%"),
            )
        )
        iss_rows = (await self.session.execute(iss_stmt)).scalars().all()
        issues = [
            ExtractedIssue(
                issue_id=i.id,
                description=i.description,
                owner_id=i.owner_id,
                status=IssueStatus(i.status),
                first_detected_at=i.first_detected_at,
                last_mentioned_at=i.last_mentioned_at or i.first_detected_at,
                resolution_meeting_id=i.resolution_meeting_id,
                evidence_segment_id=i.evidence_segment_id,
            )
            for i in iss_rows
        ]

        return EntityTimelineResponse(
            entity_id=entity_id,
            events=events,
            decisions=decisions,
            commitments=commitments,
            issues=issues,
        )
