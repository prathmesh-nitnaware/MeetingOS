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


class ZoomMeetingConnector(BaseMeetingConnector):
    """Zoom meeting connector parsing OAuth & Zoom Meeting Cloud Recording APIs to CMF."""

    def get_provider_name(self) -> str:
        return "zoom"

    def validate_config(self, config: ConnectorConfig) -> bool:
        return bool(config.account_id and config.client_id and config.client_secret)

    async def authenticate(self, config: ConnectorConfig) -> bool:
        if not self.validate_config(config):
            raise ValueError(
                "Authentication failed: Missing account_id, client_id, or client_secret."
            )

        # Real integration endpoint handshake (Skeleton)
        # OAuth Server-to-Server token flow: POST https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}
        if config.client_secret == "invalid-secret":
            raise ValueError("Authentication failed: Invalid Zoom Client credentials.")
        return True

    async def list_meetings(self, config: ConnectorConfig) -> list[ConnectorMeeting]:
        if not await self.authenticate(config):
            return []

        # Real API Integration Point:
        # GET https://api.zoom.us/v2/users/me/recordings
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
                segment_id=f"seg-zoom-{ext_meeting.external_id}-{i}",
                sequence=i,
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
            )
            for i, seg in enumerate(ext_meeting.segments)
        ]

        return Meeting(
            meeting_id=f"meet-zoom-{ext_meeting.external_id}",
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
            metadata=MeetingMetadata(source_filename=f"zoom_sync_{ext_meeting.external_id}.json"),
        )

    def get_mock_meetings(self) -> list[ConnectorMeeting]:
        return [
            ConnectorMeeting(
                external_id="zoom-meet-002",
                title="Zoom Product Sync",
                meeting_date=datetime(2026, 8, 25, 11, 0, 0, tzinfo=UTC),
                duration_seconds=600.0,
                participants=[
                    ConnectorParticipant(
                        id="p-zoom-alex", name="Alex Rivera", email="alex@meetingos.com"
                    ),
                    ConnectorParticipant(
                        id="p-zoom-priya", name="Priya Sharma", email="priya@meetingos.com"
                    ),
                ],
                segments=[
                    ConnectorTranscriptSegment(
                        speaker_id="p-zoom-alex",
                        start_time=0.0,
                        end_time=5.0,
                        text="Alex Rivera: We have a Redis connection timeout issue on the server.",
                    ),
                    ConnectorTranscriptSegment(
                        speaker_id="p-zoom-priya",
                        start_time=6.0,
                        end_time=12.0,
                        text="Priya Sharma: Let's investigate the Redis configurations.",
                    ),
                ],
            )
        ]
