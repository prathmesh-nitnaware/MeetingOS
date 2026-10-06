from packages.connectors.base import (
    DEMO_CLIENT_SECRET,
    BaseMeetingConnector,
    ConnectorNotImplementedError,
    is_placeholder,
)
from packages.connectors.google_meet import GoogleMeetMeetingConnector
from packages.connectors.models import (
    ConnectorConfig,
    ConnectorMeeting,
    ConnectorParticipant,
    ConnectorSyncResult,
    ConnectorTranscriptSegment,
)
from packages.connectors.registry import (
    DuplicateProviderError,
    UnknownProviderError,
    connector_registry,
)
from packages.connectors.teams import TeamsMeetingConnector
from packages.connectors.zoom import ZoomMeetingConnector

# Auto-register default meeting connectors
connector_registry.register(TeamsMeetingConnector())
connector_registry.register(ZoomMeetingConnector())
connector_registry.register(GoogleMeetMeetingConnector())

__all__ = [
    "BaseMeetingConnector",
    "ConnectorNotImplementedError",
    "DEMO_CLIENT_SECRET",
    "is_placeholder",
    "ConnectorMeeting",
    "ConnectorTranscriptSegment",
    "ConnectorParticipant",
    "ConnectorConfig",
    "ConnectorSyncResult",
    "connector_registry",
    "UnknownProviderError",
    "DuplicateProviderError",
    "TeamsMeetingConnector",
    "ZoomMeetingConnector",
    "GoogleMeetMeetingConnector",
]
