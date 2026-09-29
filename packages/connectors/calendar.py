from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import Meeting, MeetingMetadata, Participant, SpeakerInfo
from packages.connectors.models import ConnectorConfig, ConnectorParticipant
from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    """Normalized external calendar event model."""

    external_event_id: str
    provider: str
    calendar_id: str | None = None
    title: str
    start_time: datetime
    end_time: datetime
    description: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    organizer_email: str | None = None
    participants: list[ConnectorParticipant] = Field(default_factory=list)
    project_id: str | None = None
    sync_status: str = "synced"
    last_synced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseCalendarProvider(ABC):
    """Abstract base provider for calendar connectors (Google Calendar, Outlook/M365)."""

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def validate_config(self, config: ConnectorConfig) -> bool:
        pass

    @abstractmethod
    async def authenticate(self, config: ConnectorConfig) -> bool:
        pass

    @abstractmethod
    async def list_upcoming_events(
        self, config: ConnectorConfig, limit: int = 10
    ) -> list[CalendarEvent]:
        pass

    def convert_event_to_meeting(
        self,
        event: CalendarEvent,
        org_id: str = "org_dev",
        project_id: str | None = None,
    ) -> Meeting:
        """Convert an external calendar event into a text-first Meeting draft without fabricating content."""
        meeting_id = f"meet-{uuid4()}"
        participants = [
            Participant(
                id=str(uuid4()),
                canonical_name=p.name,
                aliases=[p.email] if p.email else [],
            )
            for p in event.participants
        ]

        duration = (event.end_time - event.start_time).total_seconds()

        metadata = MeetingMetadata(
            source_filename=f"calendar_{event.provider}_{event.external_event_id}.txt",
            content_type="notes",
            project_id=project_id or event.project_id,
        )

        return Meeting(
            meeting_id=meeting_id,
            title=event.title,
            meeting_date=event.start_time,
            duration_seconds=duration,
            source_type=SourceType.TEXT_TRANSCRIPT,
            content_type="notes",
            content="",  # Blank content awaiting actual notes / transcript
            summary=None,
            processing_status=ProcessingStatus.QUEUED,
            project_id=project_id or event.project_id,
            participants=participants,
            speakers=[
                SpeakerInfo(
                    speaker_id=f"spk_{p.canonical_name.lower().replace(' ', '_')}",
                    name=p.canonical_name,
                    canonical_entity_id=p.id,
                )
                for p in participants
            ],
            segments=[],
            metadata=metadata,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


class GoogleCalendarProvider(BaseCalendarProvider):
    """Google Calendar Provider."""

    def get_provider_name(self) -> str:
        return "google_calendar"

    def validate_config(self, config: ConnectorConfig) -> bool:
        return bool(config.enabled and config.client_id)

    async def authenticate(self, config: ConnectorConfig) -> bool:
        return bool(config.enabled and config.client_id and config.client_secret)

    async def list_upcoming_events(
        self, config: ConnectorConfig, limit: int = 10
    ) -> list[CalendarEvent]:
        now = datetime.now(UTC)
        sample_events = [
            CalendarEvent(
                external_event_id="gcal-event-101",
                provider="google_calendar",
                calendar_id="primary",
                title="Q4 Architecture & Security Review",
                start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=3),
                description="Review security posture and database architecture before launch.",
                location="Google Meet",
                meeting_link="https://meet.google.com/abc-defg-hij",
                organizer_email="alex@acmecorp.com",
                participants=[
                    ConnectorParticipant(id="u1", name="Sarah Chen", email="sarah@acmecorp.com"),
                    ConnectorParticipant(id="u2", name="Alex Rivera", email="alex@acmecorp.com"),
                    ConnectorParticipant(id="u3", name="Michael Scott", email="michael@acmecorp.com"),
                ],
            ),
            CalendarEvent(
                external_event_id="gcal-event-102",
                provider="google_calendar",
                calendar_id="primary",
                title="Weekly Product Sync",
                start_time=now + timedelta(days=1, hours=10),
                end_time=now + timedelta(days=1, hours=11),
                description="Cross-functional sync on product roadmap and open action items.",
                location="Google Meet",
                meeting_link="https://meet.google.com/xyz-uvwx-rst",
                organizer_email="sarah@acmecorp.com",
                participants=[
                    ConnectorParticipant(id="u1", name="Sarah Chen", email="sarah@acmecorp.com"),
                    ConnectorParticipant(id="u4", name="Emma Watson", email="emma@acmecorp.com"),
                ],
            ),
        ]
        return sample_events[:limit]


class MicrosoftCalendarProvider(BaseCalendarProvider):
    """Microsoft 365 / Outlook Calendar Provider."""

    def get_provider_name(self) -> str:
        return "microsoft_calendar"

    def validate_config(self, config: ConnectorConfig) -> bool:
        return bool(config.enabled and config.tenant_id and config.client_id)

    async def authenticate(self, config: ConnectorConfig) -> bool:
        return bool(config.enabled and config.tenant_id and config.client_id and config.client_secret)

    async def list_upcoming_events(
        self, config: ConnectorConfig, limit: int = 10
    ) -> list[CalendarEvent]:
        now = datetime.now(UTC)
        sample_events = [
            CalendarEvent(
                external_event_id="m365-event-201",
                provider="microsoft_calendar",
                calendar_id="default",
                title="Engineering Sprint Planning",
                start_time=now + timedelta(hours=4),
                end_time=now + timedelta(hours=5),
                description="Sprint commitment and milestone definition.",
                location="Microsoft Teams",
                meeting_link="https://teams.microsoft.com/l/meetup-join/12345",
                organizer_email="david@acmecorp.com",
                participants=[
                    ConnectorParticipant(id="u5", name="David Kim", email="david@acmecorp.com"),
                    ConnectorParticipant(id="u1", name="Sarah Chen", email="sarah@acmecorp.com"),
                ],
            )
        ]
        return sample_events[:limit]


class CalendarRegistry:
    """Registry managing available calendar providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseCalendarProvider] = {
            "google_calendar": GoogleCalendarProvider(),
            "google": GoogleCalendarProvider(),
            "microsoft_calendar": MicrosoftCalendarProvider(),
            "microsoft": MicrosoftCalendarProvider(),
            "outlook": MicrosoftCalendarProvider(),
        }

    def get(self, provider_name: str) -> BaseCalendarProvider | None:
        return self._providers.get(provider_name.lower())

    def list_providers(self) -> list[str]:
        return ["google_calendar", "microsoft_calendar"]


calendar_registry = CalendarRegistry()
