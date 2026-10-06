from abc import ABC, abstractmethod

from packages.common.models import Meeting
from packages.connectors.models import ConnectorConfig, ConnectorMeeting

# Client secret that switches a connector into offline demo mode (fixed sample meetings)
DEMO_CLIENT_SECRET = "mock-secret"


class ConnectorNotImplementedError(RuntimeError):
    """Raised when a live (non-demo) connector call is requested but not implemented."""


def is_placeholder(value: str | None) -> bool:
    """True for missing credentials or template values copied from .env.example."""
    if not value or not value.strip():
        return True
    lowered = value.strip().lower()
    return lowered.startswith("your-") or lowered.endswith("-here") or "placeholder" in lowered


class BaseMeetingConnector(ABC):
    """Abstract base class defining standard external meeting connector contracts.

    The Teams / Zoom / Google Meet connectors currently support demo mode only: with the
    client secret ``mock-secret`` they return fixed sample meetings. Real API calls are not
    implemented, and the connectors report that honestly instead of pretending to be
    authenticated.
    """

    display_name: str = "External"

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

    def is_demo(self, config: ConnectorConfig) -> bool:
        return config.client_secret == DEMO_CLIENT_SECRET

    def not_implemented(self) -> ConnectorNotImplementedError:
        return ConnectorNotImplementedError(
            f"The live {self.display_name} integration is not implemented yet. "
            f"Only demo mode (client secret '{DEMO_CLIENT_SECRET}') is available."
        )
