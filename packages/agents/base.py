from abc import ABC, abstractmethod

from packages.agents.context import AgentContext


class BaseAgent(ABC):
    """Abstract base class representing a specialist or reasoning agent."""

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentContext:
        """Process the agent context and return the enriched context."""
        pass
