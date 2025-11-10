"""Payment adapter registry."""

from .registry import get_adapter, list_adapters, register_adapter
# Ensure default adapters are registered
from . import manual_stub  # noqa: F401
from . import stripe_stub  # noqa: F401
from . import generic_pg  # noqa: F401

__all__ = ["register_adapter", "get_adapter", "list_adapters"]
