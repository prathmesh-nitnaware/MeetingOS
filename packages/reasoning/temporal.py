import re
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

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
    EntityModel,
    EventModel,
    IssueModel,
    MeetingEntityModel,
    MeetingModel,
)
from pydantic import BaseModel, Field
from sqlalchemy import String, and_, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# model_name values used to tell apart where a timeline event came from
RECONCILER_MODEL_NAME = "temporal-reconciler"
NLP_EVENT_MODEL_NAME = "nlp-event-extractor"


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


class MeetingNotFoundError(LookupError):
    """Raised when a meeting does not exist in the caller's organisation."""


def _reconciliation_event_id(meeting_id: str, *parts: str) -> str:
    return f"evt-{uuid5(NAMESPACE_URL, 'reconcile:' + meeting_id + ':' + ':'.join(parts))}"


def _payload_mentions(value: str):
    """SQL predicate: the event payload (JSON rendered as text) contains ``value`` literally."""
    return cast(EventModel.payload_json, String).contains(value, autoescape=True)


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class TemporalIntelligenceEngine:
    """Decision lifecycle tracking, slippage detection, recurring issue analysis and timeline reconstruction.

    Must be instantiated with the authenticated user's ``org_id``: every query is scoped to
    that single tenant and ignores soft-deleted meetings.
    """

    def __init__(self, session: AsyncSession, org_id: str = "org_dev") -> None:
        self.session = session
        self.org_id = org_id

    # ------------------------------------------------------------------ scoping helpers

    def _visible_meeting(self):
        """Filter clause for meetings of this organisation that are not soft-deleted."""
        return and_(MeetingModel.org_id == self.org_id, MeetingModel.deleted_at.is_(None))

    def _event_item(self, evt: EventModel, meeting_title: str | None) -> TimelineEventItem:
        return TimelineEventItem(
            event_id=evt.id,
            event_type=EventType(evt.event_type),
            occurred_at=evt.occurred_at,
            meeting_id=evt.meeting_id,
            meeting_title=meeting_title,
            subject_entity_id=evt.subject_entity_id,
            payload=evt.payload_json,
            evidence_segment_id=evt.evidence_segment_id,
        )

    async def _events_mentioning(self, record_id: str) -> list[TimelineEventItem]:
        stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .where(
                self._visible_meeting(),
                or_(EventModel.subject_entity_id == record_id, _payload_mentions(record_id)),
            )
            .order_by(EventModel.occurred_at.asc(), EventModel.created_at.asc())
        )
        return [self._event_item(e, title) for e, title in (await self.session.execute(stmt)).all()]

    # -------------------------------------------------------------------- reconciliation

    async def reconcile_meeting_lifecycle(self, meeting_id: str) -> TemporalReconciliationResult:
        """Compare a meeting's facts with EARLIER meetings of the same organisation.

        Idempotent: events produced by a previous reconciliation of this meeting are replaced,
        not duplicated.
        """
        current_meeting = (
            await self.session.execute(
                select(MeetingModel).where(MeetingModel.id == meeting_id, self._visible_meeting())
            )
        ).scalar_one_or_none()
        if not current_meeting:
            raise MeetingNotFoundError(meeting_id)

        m_date = _ensure_aware(current_meeting.meeting_date) or datetime.now(UTC)
        m_created = _ensure_aware(current_meeting.created_at) or datetime.now(UTC)

        # Earlier meetings only: strictly earlier date, or same date but ingested earlier
        earlier = and_(
            self._visible_meeting(),
            MeetingModel.id != meeting_id,
            or_(
                MeetingModel.meeting_date < m_date,
                and_(MeetingModel.meeting_date == m_date, MeetingModel.created_at < m_created),
            ),
        )

        await self.session.execute(
            delete(EventModel).where(
                EventModel.meeting_id == meeting_id,
                EventModel.model_name == RECONCILER_MODEL_NAME,
            )
        )

        dec_changes = 0
        deadline_changes = 0
        recurring_issues = 0
        new_events: list[EventModel] = []

        def add_event(
            event_type: EventType, subject_id: str, payload: dict[str, Any], evidence: str | None
        ) -> None:
            new_events.append(
                EventModel(
                    id=_reconciliation_event_id(meeting_id, event_type.value, subject_id),
                    meeting_id=meeting_id,
                    event_type=str(event_type),
                    occurred_at=m_date,
                    subject_entity_id=subject_id,
                    payload_json=payload,
                    evidence_segment_id=evidence,
                    model_name=RECONCILER_MODEL_NAME,
                )
            )

        # 1. Decisions: reversals and modifications
        cur_decisions = (
            (
                await self.session.execute(
                    select(DecisionModel).where(DecisionModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )
        prior_decisions = (
            (
                await self.session.execute(
                    select(DecisionModel)
                    .join(MeetingModel, MeetingModel.id == DecisionModel.meeting_id)
                    .where(earlier)
                )
            )
            .scalars()
            .all()
        )

        reversal_markers = (
            "replaces",
            "switch from",
            "revert",
            "abandon",
            "reversal",
            "instead of",
        )
        for cur_dec in cur_decisions:
            cur_sub = cur_dec.subject.lower()
            cur_tokens = {t for t in re.findall(r"[a-z0-9]+", cur_sub) if len(t) > 4}
            for prior_dec in prior_decisions:
                prior_sub = prior_dec.subject.lower()
                prior_tokens = {t for t in re.findall(r"[a-z0-9]+", prior_sub) if len(t) > 4}
                shared = cur_tokens & prior_tokens

                if any(m in cur_sub for m in reversal_markers) and len(shared) >= 2:
                    prior_dec.status = str(DecisionStatus.REVERSED)
                    cur_dec.status = str(DecisionStatus.APPROVED)
                    dec_changes += 1
                    add_event(
                        EventType.DECISION_REVERSED,
                        prior_dec.id,
                        {
                            "prior_decision_id": prior_dec.id,
                            "prior_subject": prior_dec.subject,
                            "new_decision_id": cur_dec.id,
                            "new_subject": cur_dec.subject,
                            "reason": cur_dec.rationale or cur_dec.subject,
                        },
                        cur_dec.evidence_segment_id,
                    )
                elif (prior_sub in cur_sub or cur_sub in prior_sub) and (
                    cur_dec.status != prior_dec.status
                    and prior_dec.status != str(DecisionStatus.REVERSED)
                ):
                    prior_dec.status = str(DecisionStatus.MODIFIED)
                    dec_changes += 1
                    add_event(
                        EventType.DECISION_MODIFIED,
                        prior_dec.id,
                        {
                            "prior_decision_id": prior_dec.id,
                            "new_decision_id": cur_dec.id,
                            "new_status": cur_dec.status,
                        },
                        cur_dec.evidence_segment_id,
                    )

        # 2. Commitments: deadline changes / slippage
        cur_commitments = (
            (
                await self.session.execute(
                    select(CommitmentModel).where(CommitmentModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )
        prior_commitments = (
            (
                await self.session.execute(
                    select(CommitmentModel)
                    .join(MeetingModel, MeetingModel.id == CommitmentModel.meeting_id)
                    .where(earlier)
                )
            )
            .scalars()
            .all()
        )

        for cur_com in cur_commitments:
            cur_desc = cur_com.description.lower()
            for prior_com in prior_commitments:
                prior_desc = prior_com.description.lower()
                common_tokens = [t for t in cur_desc.split() if len(t) > 3 and t in prior_desc]
                if len(common_tokens) < 2 and cur_desc != prior_desc:
                    continue
                old_dl = _ensure_aware(prior_com.current_deadline)
                new_dl = _ensure_aware(cur_com.current_deadline)
                if old_dl and new_dl and old_dl != new_dl:
                    deadline_changes += 1
                    prior_com.current_deadline = new_dl
                    if new_dl > old_dl:
                        prior_com.status = str(CommitmentStatus.OVERDUE)
                    add_event(
                        EventType.DEADLINE_CHANGED,
                        prior_com.id,
                        {
                            "commitment_id": prior_com.id,
                            "new_commitment_id": cur_com.id,
                            "previous_deadline": old_dl.isoformat(),
                            "new_deadline": new_dl.isoformat(),
                            "owner_id": cur_com.owner_id or prior_com.owner_id,
                            "description": cur_com.description,
                        },
                        cur_com.evidence_segment_id,
                    )

        # 3. Issues: recurrence and resolution
        cur_issues = (
            (
                await self.session.execute(
                    select(IssueModel).where(IssueModel.meeting_id == meeting_id)
                )
            )
            .scalars()
            .all()
        )
        prior_issues = (
            (
                await self.session.execute(
                    select(IssueModel)
                    .join(MeetingModel, MeetingModel.id == IssueModel.meeting_id)
                    .where(earlier)
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
                if len(common_tokens) < 2 and cur_desc != prior_desc:
                    continue
                if (
                    cur_iss.status == str(IssueStatus.RESOLVED)
                    or "resolved" in cur_desc
                    or "fixed" in cur_desc
                ):
                    prior_iss.status = str(IssueStatus.RESOLVED)
                    prior_iss.resolution_meeting_id = meeting_id
                    prior_iss.last_mentioned_at = m_date
                    add_event(
                        EventType.ISSUE_RESOLVED,
                        prior_iss.id,
                        {
                            "issue_id": prior_iss.id,
                            "description": prior_iss.description,
                            "resolution_meeting_id": meeting_id,
                        },
                        cur_iss.evidence_segment_id,
                    )
                else:
                    prior_iss.status = str(IssueStatus.RECURRING)
                    prior_iss.last_mentioned_at = m_date
                    cur_iss.status = str(IssueStatus.RECURRING)
                    recurring_issues += 1
                    first_seen = _ensure_aware(prior_iss.first_detected_at) or m_date
                    add_event(
                        EventType.ISSUE_RECURRING,
                        prior_iss.id,
                        {
                            "issue_id": prior_iss.id,
                            "description": prior_iss.description,
                            "status": "Recurring",
                            "first_detected_at": first_seen.isoformat(),
                            "last_mentioned_at": m_date.isoformat(),
                        },
                        cur_iss.evidence_segment_id,
                    )

        # A pair can match more than once (e.g. two current decisions reversing one prior
        # decision); keep one event per deterministic id.
        unique_events = {evt.id: evt for evt in new_events}
        await self.session.flush()
        for evt in unique_events.values():
            self.session.add(evt)
        await self.session.flush()

        return TemporalReconciliationResult(
            meeting_id=meeting_id,
            decision_changes_detected=dec_changes,
            deadline_changes_detected=deadline_changes,
            recurring_issues_detected=recurring_issues,
            events_created=len(unique_events),
        )

    # ------------------------------------------------------------------------ timelines

    async def get_global_timeline(
        self,
        entity_id: str | None = None,
        event_type: EventType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TimelineEventItem]:
        """Fetch chronologically ordered events across the organisation's history."""
        stmt = (
            select(EventModel, MeetingModel.title)
            .join(MeetingModel, MeetingModel.id == EventModel.meeting_id)
            .where(self._visible_meeting())
        )
        if entity_id:
            stmt = stmt.where(
                or_(EventModel.subject_entity_id == entity_id, _payload_mentions(entity_id))
            )
        if event_type:
            stmt = stmt.where(EventModel.event_type == str(event_type))
        if start_date:
            stmt = stmt.where(EventModel.occurred_at >= start_date)
        if end_date:
            stmt = stmt.where(EventModel.occurred_at <= end_date)

        stmt = (
            stmt.order_by(EventModel.occurred_at.asc(), EventModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).all()
        return [self._event_item(evt, title) for evt, title in rows]

    async def reconstruct_decision_history(self, decision_id: str) -> DecisionHistoryItem | None:
        """Reconstruct the lifecycle history of a decision owned by this organisation."""
        row = (
            await self.session.execute(
                select(DecisionModel, MeetingModel)
                .join(MeetingModel, MeetingModel.id == DecisionModel.meeting_id)
                .where(DecisionModel.id == decision_id, self._visible_meeting())
            )
        ).first()
        if not row:
            return None

        dec, m = row
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
            events=await self._events_mentioning(decision_id),
        )

    async def reconstruct_commitment_history(
        self, commitment_id: str
    ) -> CommitmentHistoryItem | None:
        """Reconstruct deadline and assignment history of a commitment owned by this organisation."""
        com = (
            await self.session.execute(
                select(CommitmentModel)
                .join(MeetingModel, MeetingModel.id == CommitmentModel.meeting_id)
                .where(CommitmentModel.id == commitment_id, self._visible_meeting())
            )
        ).scalar_one_or_none()
        if not com:
            return None

        events = await self._events_mentioning(commitment_id)
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
            deadline_changes_count=sum(
                1 for e in events if e.event_type == EventType.DEADLINE_CHANGED
            ),
            events=events,
        )

    async def reconstruct_issue_history(self, issue_id: str) -> IssueHistoryItem | None:
        """Reconstruct detection and resolution lifecycle of an issue owned by this organisation."""
        iss = (
            await self.session.execute(
                select(IssueModel)
                .join(MeetingModel, MeetingModel.id == IssueModel.meeting_id)
                .where(IssueModel.id == issue_id, self._visible_meeting())
            )
        ).scalar_one_or_none()
        if not iss:
            return None

        events = await self._events_mentioning(issue_id)
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
        """Events, decisions, commitments and issues that mention an entity in this organisation."""
        events = await self.get_global_timeline(entity_id=entity_id, limit=100)

        entity = await self.session.get(EntityModel, entity_id)
        if entity is None:
            return EntityTimelineResponse(entity_id=entity_id, events=events)

        # Only meetings of this organisation in which the entity was actually detected
        meeting_ids = select(MeetingEntityModel.meeting_id).where(
            MeetingEntityModel.entity_id == entity_id
        )
        name = entity.name.lower()
        speaker_id = "spk_" + re.sub(r"\s+", "_", name.strip())

        def mentions(column):
            return func.lower(column).contains(name, autoescape=True)

        dec_rows = (
            (
                await self.session.execute(
                    select(DecisionModel)
                    .join(MeetingModel, MeetingModel.id == DecisionModel.meeting_id)
                    .where(
                        self._visible_meeting(),
                        DecisionModel.meeting_id.in_(meeting_ids),
                        mentions(DecisionModel.subject),
                    )
                    .order_by(DecisionModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        com_rows = (
            (
                await self.session.execute(
                    select(CommitmentModel)
                    .join(MeetingModel, MeetingModel.id == CommitmentModel.meeting_id)
                    .where(
                        self._visible_meeting(),
                        CommitmentModel.meeting_id.in_(meeting_ids),
                        or_(
                            CommitmentModel.owner_id == speaker_id,
                            mentions(CommitmentModel.description),
                        ),
                    )
                    .order_by(CommitmentModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        iss_rows = (
            (
                await self.session.execute(
                    select(IssueModel)
                    .join(MeetingModel, MeetingModel.id == IssueModel.meeting_id)
                    .where(
                        self._visible_meeting(),
                        IssueModel.meeting_id.in_(meeting_ids),
                        or_(IssueModel.owner_id == speaker_id, mentions(IssueModel.description)),
                    )
                    .order_by(IssueModel.created_at.asc())
                )
            )
            .scalars()
            .all()
        )

        return EntityTimelineResponse(
            entity_id=entity_id,
            events=events,
            decisions=[
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
            ],
            commitments=[
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
            ],
            issues=[
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
            ],
        )
