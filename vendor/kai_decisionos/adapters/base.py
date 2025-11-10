from abc import ABC, abstractmethod
from typing import Any, Dict

class Adapter(ABC):
    """Abstract base class for all adapters."""

    @abstractmethod
    def estimate_cost(self, prompt: str, model: str) -> float:
        """Estimate the cost of a request."""
        pass

    @abstractmethod
    async def execute(self, prompt: str, model: str) -> Dict[str, Any]:
        """Execute the request and return the response."""
        pass
