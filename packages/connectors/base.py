from abc import ABC, abstractmethod

from packages.common.models import Meeting
from packages.connectors.models import ConnectorConfig, ConnectorMeeting


class BaseMeetingConnector(ABC):
    """Abstract base class defining standard external meeting connector contracts."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the unique identifier string of the provider (e.g. 'teams')."""
        pass

    @abstractmethod
    def validate_config(self, config: ConnectorConfig) -> bool:
        """Verify if credentials and properties are populated in the config."""
        pass

    @abstractmethod
    async def authenticate(self, config: ConnectorConfig) -> bool:
        """Attempt connection or validation of access tokens against external service."""
        pass

    @abstractmethod
    async def list_meetings(self, config: ConnectorConfig) -> list[ConnectorMeeting]:
        """Fetch available meeting records from the external service."""
        pass

    @abstractmethod
    def normalize_to_cmf(self, ext_meeting: ConnectorMeeting) -> Meeting:
        """Normalize connector meeting representations to Common Meeting Format."""
        pass
