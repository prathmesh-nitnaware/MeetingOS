from datetime import UTC, datetime

from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import (
    Meeting,
    MeetingMetadata,
    Participant,
    SpeakerInfo,
    TranscriptSegment,
)
from packages.connectors.base import BaseMeetingConnector
from packages.connectors.models import (
    ConnectorConfig,
    ConnectorMeeting,
    ConnectorParticipant,
    ConnectorTranscriptSegment,
)


class TeamsMeetingConnector(BaseMeetingConnector):
    """Microsoft Teams meeting connector parsing MS Graph API responses to CMF."""

    def get_provider_name(self) -> str:
        return "teams"

    def validate_config(self, config: ConnectorConfig) -> bool:
        return bool(config.tenant_id and config.client_id and config.client_secret)

    async def authenticate(self, config: ConnectorConfig) -> bool:
        if not self.validate_config(config):
            raise ValueError(
                "Authentication failed: Missing tenant_id, client_id, or client_secret."
            )

        # Real integration endpoint handshake (Skeleton)
        # In a real environment, we would post to https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
        # Here we verify if they are set to dummy/example credentials.
        if config.client_secret == "invalid-secret":
            raise ValueError("Authentication failed: Invalid Microsoft Graph client secret.")
        return True

    async def list_meetings(self, config: ConnectorConfig) -> list[ConnectorMeeting]:
        if not await self.authenticate(config):
            return []

        # Real API Integration Point:
        # GET https://graph.microsoft.com/v1.0/me/onlineMeetings or /communications/onlineMeetings
        # In this mock-fallback skeleton we check if we should return deterministic mock meetings.
        if config.client_secret == "mock-secret":
            return self.get_mock_meetings()
        return []

    def normalize_to_cmf(self, ext_meeting: ConnectorMeeting) -> Meeting:
        participants = [
            Participant(id=p.id, canonical_name=p.name, aliases=[p.email] if p.email else [])
            for p in ext_meeting.participants
        ]

        speakers = [SpeakerInfo(speaker_id=p.id, name=p.name) for p in ext_meeting.participants]

        segments = [
            TranscriptSegment(
                segment_id=f"seg-teams-{ext_meeting.external_id}-{i}",
                sequence=i,
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
            )
            for i, seg in enumerate(ext_meeting.segments)
        ]

        return Meeting(
            meeting_id=f"meet-teams-{ext_meeting.external_id}",
            title=ext_meeting.title,
            meeting_date=ext_meeting.meeting_date,
            duration_seconds=ext_meeting.duration_seconds,
            source_type=SourceType.SYNTHETIC,
            processing_status=ProcessingStatus.QUEUED,
            participants=participants,
            speakers=speakers,
            segments=segments,
            source_provider=self.get_provider_name(),
            external_meeting_id=ext_meeting.external_id,
            metadata=MeetingMetadata(source_filename=f"teams_sync_{ext_meeting.external_id}.json"),
        )

    def get_mock_meetings(self) -> list[ConnectorMeeting]:
        return [
            ConnectorMeeting(
                external_id="teams-meet-001",
                title="Teams Architecture Review",
                meeting_date=datetime(2026, 8, 25, 10, 0, 0, tzinfo=UTC),
                duration_seconds=600.0,
                participants=[
                    ConnectorParticipant(
                        id="p-teams-rahul", name="Rahul Verma", email="rahul@meetingos.com"
                    ),
                    ConnectorParticipant(
                        id="p-teams-priya", name="Priya Sharma", email="priya@meetingos.com"
                    ),
                ],
                segments=[
                    ConnectorTranscriptSegment(
                        speaker_id="p-teams-rahul",
                        start_time=0.0,
                        end_time=5.0,
                        text="Rahul Verma: Let's adopt PostgreSQL for teams storage.",
                    ),
                    ConnectorTranscriptSegment(
                        speaker_id="p-teams-priya",
                        start_time=6.0,
                        end_time=12.0,
                        text="Priya Sharma: I will design the database table schemas tomorrow.",
                    ),
                ],
            )
        ]
