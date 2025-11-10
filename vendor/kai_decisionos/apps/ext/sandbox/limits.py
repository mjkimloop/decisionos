from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResourceLimits:
    cpu_ms: int = 1000
    memory_mb: int = 128
    tmp_mb: int = 16
    timeout_ms: int = 3000


DEFAULT_LIMITS = ResourceLimits()

__all__ = ["ResourceLimits", "DEFAULT_LIMITS"]
