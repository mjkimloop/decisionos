from __future__ import annotations

from dataclasses import dataclass


_DEGRADE = False


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str | None = None


def set_degrade(on: bool) -> None:
    global _DEGRADE
    _DEGRADE = bool(on)


def is_degraded() -> bool:
    return _DEGRADE


def run_probes() -> list[ProbeResult]:
    # scaffold probes; in real code, check DB, external adapters, etc.
    results: list[ProbeResult] = []
    results.append(ProbeResult(name="core", ok=True))
    # degrade flips readiness false
    if _DEGRADE:
        results.append(ProbeResult(name="degrade", ok=False, detail="manual degrade"))
    else:
        results.append(ProbeResult(name="degrade", ok=True))
    return results

