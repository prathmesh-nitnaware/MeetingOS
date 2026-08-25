from packages.connectors.base import BaseMeetingConnector


class UnknownProviderError(Exception):
    """Raised when requesting a connector provider that is not registered."""

    pass


class DuplicateProviderError(Exception):
    """Raised when registering a provider that already exists in the registry."""

    pass


class ConnectorRegistry:
    """Thread-safe registry for registering and retrieving external meeting connectors."""

    def __init__(self) -> None:
        self._registry: dict[str, BaseMeetingConnector] = {}

    def register(self, connector: BaseMeetingConnector) -> None:
        provider = connector.get_provider_name().lower()
        if provider in self._registry:
            raise DuplicateProviderError(
                f"Connector for provider '{provider}' is already registered."
            )
        self._registry[provider] = connector

    def get(self, provider: str) -> BaseMeetingConnector:
        prov_key = provider.lower()
        if prov_key not in self._registry:
            raise UnknownProviderError(f"No connector registered for provider '{provider}'.")
        return self._registry[prov_key]

    def list_available(self) -> list[str]:
        return list(self._registry.keys())

    def clear(self) -> None:
        """Clear registry for testing isolation."""
        self._registry.clear()


# Global registry instance
connector_registry = ConnectorRegistry()
