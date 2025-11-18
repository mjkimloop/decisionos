"""Cutover readiness judgment card for operations dashboard.

Provides instant visibility into production cutover readiness with
health checks, metrics, and Go/No-Go decision support.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# Health check states
HealthState = Literal["healthy", "degraded", "unhealthy", "unknown"]


@dataclass
class HealthCheck:
    """Single health check result."""

    name: str
    state: HealthState
    message: str
    details: dict[str, Any] | None = None


@dataclass
class CutoverReadinessCard:
    """Cutover readiness judgment card."""

    overall_state: HealthState
    go_no_go: Literal["GO", "NO-GO", "PENDING"]
    checks: list[HealthCheck]
    metrics: dict[str, Any]
    timestamp: str


def check_readyz_health() -> HealthCheck:
    """Check /readyz endpoint health."""
    import urllib.request

    readyz_url = os.environ.get("READYZ_URL", "http://localhost:8080/readyz")

    try:
        with urllib.request.urlopen(readyz_url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            status = data.get("status", "unknown")

            if status == "ok":
                return HealthCheck(
                    name="Readyz Endpoint",
                    state="healthy",
                    message="All systems operational",
                    details=data.get("checks"),
                )
            elif status == "degraded":
                return HealthCheck(
                    name="Readyz Endpoint",
                    state="degraded",
                    message="Some systems degraded",
                    details=data.get("checks"),
                )
            else:
                return HealthCheck(
                    name="Readyz Endpoint",
                    state="unhealthy",
                    message=f"Status: {status}",
                    details=data.get("checks"),
                )

    except Exception as e:
        return HealthCheck(
            name="Readyz Endpoint",
            state="unhealthy",
            message=f"Unreachable: {str(e)}",
        )


def check_evidence_integrity() -> HealthCheck:
    """Check evidence integrity."""
    evidence_dir = Path(os.environ.get("EVIDENCE_DIR", "var/evidence"))
    index_file = evidence_dir / "index.json"

    if not index_file.exists():
        return HealthCheck(
            name="Evidence Integrity",
            state="unhealthy",
            message="Evidence index not found",
        )

    try:
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        tampered = index.get("tampered", True)
        entry_count = len(index.get("entries", []))

        if tampered:
            return HealthCheck(
                name="Evidence Integrity",
                state="unhealthy",
                message="Evidence tampered",
                details={"entry_count": entry_count},
            )

        return HealthCheck(
            name="Evidence Integrity",
            state="healthy",
            message=f"{entry_count} entries verified",
            details={"entry_count": entry_count},
        )

    except Exception as e:
        return HealthCheck(
            name="Evidence Integrity",
            state="unhealthy",
            message=f"Verification failed: {str(e)}",
        )


def check_key_rotation_status() -> HealthCheck:
    """Check key rotation countdown status."""
    try:
        from apps.judge.crypto import MultiKeyLoader

        loader = MultiKeyLoader(env_var="DECISIONOS_POLICY_KEYS")
        keys = loader._keys

        if not keys:
            return HealthCheck(
                name="Key Rotation",
                state="unhealthy",
                message="No keys configured",
            )

        active_count = sum(1 for k in keys if k.state == "active")
        grace_count = sum(1 for k in keys if k.state == "grace")

        if active_count == 0:
            return HealthCheck(
                name="Key Rotation",
                state="unhealthy",
                message="No active keys",
            )

        # Check for expiring keys (simplified)
        return HealthCheck(
            name="Key Rotation",
            state="healthy",
            message=f"{active_count} active, {grace_count} grace",
            details={"active": active_count, "grace": grace_count},
        )

    except Exception as e:
        return HealthCheck(
            name="Key Rotation",
            state="unknown",
            message=f"Check failed: {str(e)}",
        )


def check_pii_circuit_breaker() -> HealthCheck:
    """Check PII middleware circuit breaker status."""
    try:
        from apps.security.pii_circuit_breaker import PIICircuitBreaker

        breaker = PIICircuitBreaker()
        state = breaker.get_state()

        if state.state == "enabled":
            return HealthCheck(
                name="PII Circuit Breaker",
                state="healthy",
                message="Enabled and operational",
            )
        elif state.state == "disabled_auto":
            return HealthCheck(
                name="PII Circuit Breaker",
                state="degraded",
                message=f"Auto-disabled: {state.reason}",
            )
        else:  # disabled_manual
            return HealthCheck(
                name="PII Circuit Breaker",
                state="degraded",
                message=f"Manually disabled: {state.reason}",
            )

    except Exception as e:
        return HealthCheck(
            name="PII Circuit Breaker",
            state="unknown",
            message=f"Check failed: {str(e)}",
        )


def check_canary_health() -> HealthCheck:
    """Check canary deployment health."""
    evidence_path = Path(
        os.environ.get("DECISIONOS_EVIDENCE_LATEST", "var/evidence/latest.json")
    )

    if not evidence_path.exists():
        return HealthCheck(
            name="Canary Health",
            state="unknown",
            message="No evidence available",
        )

    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)

        canary = evidence.get("canary", {})
        windows = canary.get("windows", [])

        if not windows:
            return HealthCheck(
                name="Canary Health",
                state="unknown",
                message="No canary windows",
            )

        # Check last 3 windows
        recent = windows[-3:]
        all_pass = all(w.get("pass", False) for w in recent)
        max_burst = max((w.get("burst", 0) for w in recent), default=0)

        if all_pass and max_burst <= 1.5:
            return HealthCheck(
                name="Canary Health",
                state="healthy",
                message=f"{len(recent)} green windows, burst={max_burst:.2f}x",
                details={"windows": len(recent), "max_burst": max_burst},
            )
        elif all_pass:
            return HealthCheck(
                name="Canary Health",
                state="degraded",
                message=f"High burst: {max_burst:.2f}x",
                details={"windows": len(recent), "max_burst": max_burst},
            )
        else:
            return HealthCheck(
                name="Canary Health",
                state="unhealthy",
                message="Failed windows detected",
                details={"windows": len(recent), "max_burst": max_burst},
            )

    except Exception as e:
        return HealthCheck(
            name="Canary Health",
            state="unknown",
            message=f"Check failed: {str(e)}",
        )


def check_manual_promotion_mode() -> HealthCheck:
    """Check if manual promotion mode is enabled."""
    marker_file = Path("var/runtime/manual_promotion.flag")

    autopromote_enable = os.environ.get("DECISIONOS_AUTOPROMOTE_ENABLE", "0")
    marker_exists = marker_file.exists()
    marker_mode = marker_file.read_text().strip() if marker_exists else None

    if autopromote_enable == "0" and marker_mode == "manual":
        return HealthCheck(
            name="Promotion Mode",
            state="healthy",
            message="Manual promotion enforced",
        )
    elif autopromote_enable == "0":
        return HealthCheck(
            name="Promotion Mode",
            state="degraded",
            message="Auto-promotion disabled (no marker)",
        )
    else:
        return HealthCheck(
            name="Promotion Mode",
            state="unhealthy",
            message="Auto-promotion ENABLED (unsafe for cutover)",
        )


def get_cutover_readiness_card() -> CutoverReadinessCard:
    """Generate cutover readiness judgment card.

    Returns:
        CutoverReadinessCard with all health checks and metrics
    """
    checks = [
        check_readyz_health(),
        check_evidence_integrity(),
        check_key_rotation_status(),
        check_pii_circuit_breaker(),
        check_canary_health(),
        check_manual_promotion_mode(),
    ]

    # Determine overall state
    unhealthy_count = sum(1 for c in checks if c.state == "unhealthy")
    degraded_count = sum(1 for c in checks if c.state == "degraded")
    unknown_count = sum(1 for c in checks if c.state == "unknown")

    if unhealthy_count > 0:
        overall_state = "unhealthy"
        go_no_go = "NO-GO"
    elif degraded_count > 0:
        overall_state = "degraded"
        go_no_go = "PENDING"
    elif unknown_count > 0:
        overall_state = "degraded"
        go_no_go = "PENDING"
    else:
        overall_state = "healthy"
        go_no_go = "GO"

    # Collect metrics
    metrics = {
        "total_checks": len(checks),
        "healthy": sum(1 for c in checks if c.state == "healthy"),
        "degraded": degraded_count,
        "unhealthy": unhealthy_count,
        "unknown": unknown_count,
    }

    return CutoverReadinessCard(
        overall_state=overall_state,
        go_no_go=go_no_go,
        checks=checks,
        metrics=metrics,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def format_card_text(card: CutoverReadinessCard) -> str:
    """Format card as human-readable text.

    Args:
        card: Cutover readiness card

    Returns:
        Formatted text output
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  CUTOVER READINESS DASHBOARD")
    lines.append("=" * 60)
    lines.append(f"  Overall: {card.overall_state.upper()}")
    lines.append(f"  Go/No-Go: {card.go_no_go}")
    lines.append(f"  Timestamp: {card.timestamp}")
    lines.append("=" * 60)
    lines.append("")

    for check in card.checks:
        icon = {
            "healthy": "✓",
            "degraded": "⚠",
            "unhealthy": "✗",
            "unknown": "?",
        }[check.state]

        lines.append(f"{icon} {check.name:25s} [{check.state:10s}] {check.message}")

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"  Metrics: {card.metrics['healthy']}/{card.metrics['total_checks']} healthy")
    lines.append("=" * 60)

    return "\n".join(lines)
