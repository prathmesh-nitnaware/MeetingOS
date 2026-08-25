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


class GoogleMeetMeetingConnector(BaseMeetingConnector):
    """Google Meet meeting connector parsing Google Calendar and Meet transcripts to CMF."""

    def get_provider_name(self) -> str:
        return "google_meet"

    def validate_config(self, config: ConnectorConfig) -> bool:
        return bool(config.client_id and config.client_secret)

    async def authenticate(self, config: ConnectorConfig) -> bool:
        if not self.validate_config(config):
            raise ValueError("Authentication failed: Missing client_id or client_secret.")

        # Real integration endpoint handshake (Skeleton)
        # OAuth client flow using Google credentials.
        if config.client_secret == "invalid-secret":
            raise ValueError("Authentication failed: Invalid Google Client credentials.")
        return True

    async def list_meetings(self, config: ConnectorConfig) -> list[ConnectorMeeting]:
        if not await self.authenticate(config):
            return []

        # Real API Integration Point:
        # GET https://www.googleapis.com/calendar/v3/calendars/primary/events
        # filtering events with conferenceData indicating a Google Meet conference.
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
                segment_id=f"seg-google_meet-{ext_meeting.external_id}-{i}",
                sequence=i,
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
            )
            for i, seg in enumerate(ext_meeting.segments)
        ]

        return Meeting(
            meeting_id=f"meet-google_meet-{ext_meeting.external_id}",
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
            metadata=MeetingMetadata(
                source_filename=f"google_meet_sync_{ext_meeting.external_id}.json"
            ),
        )

    def get_mock_meetings(self) -> list[ConnectorMeeting]:
        return [
            ConnectorMeeting(
                external_id="gmeet-meet-003",
                title="Google Meet Retro",
                meeting_date=datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC),
                duration_seconds=600.0,
                participants=[
                    ConnectorParticipant(
                        id="p-gmeet-alex", name="Alex Rivera", email="alex@meetingos.com"
                    ),
                    ConnectorParticipant(
                        id="p-gmeet-rahul", name="Rahul Verma", email="rahul@meetingos.com"
                    ),
                ],
                segments=[
                    ConnectorTranscriptSegment(
                        speaker_id="p-gmeet-alex",
                        start_time=0.0,
                        end_time=5.0,
                        text="Alex Rivera: The Redis connection issue is fully resolved now.",
                    ),
                    ConnectorTranscriptSegment(
                        speaker_id="p-gmeet-rahul",
                        start_time=6.0,
                        end_time=12.0,
                        text="Rahul Verma: Great, let's close that issue on the board.",
                    ),
                ],
            )
        ]
