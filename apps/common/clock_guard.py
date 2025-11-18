from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from apps.common.clock import now_utc

ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _read_reference(path: Path) -> datetime:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("reference timestamp empty")
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


def ensure_reference(path: str) -> datetime:
    ref_path = Path(path)
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref = now_utc()
    ref_path.write_text(ref.strftime(ISO_FMT), encoding="utf-8")
    return ref


def check_clock(ref_path: str, max_skew_sec: float) -> Tuple[bool, float]:
    path = Path(ref_path)
    now = now_utc()
    if not path.exists():
        ensure_reference(ref_path)
        return True, 0.0

    try:
        ref = _read_reference(path)
    except Exception as exc:
        raise ValueError(f"invalid reference timestamp: {exc}") from exc

    drift = abs((now - ref).total_seconds())
    return drift <= max_skew_sec, drift


__all__ = ["check_clock", "ensure_reference"]
