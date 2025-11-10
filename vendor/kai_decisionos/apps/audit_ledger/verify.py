from __future__ import annotations

from pathlib import Path

from .verify_hashes import verify_chain
from packages.common.config import settings


def verify_default() -> bool:
    return bool(verify_chain(Path(settings.audit_log_path)))
