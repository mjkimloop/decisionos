from __future__ import annotations

from pathlib import Path

from apps.audit_ledger.verify_hashes import verify_chain
from apps.rule_engine.linter import lint_rules


def seal_check(strict: bool = False) -> dict:
    results = {"docs": True, "rules": True, "audit": True, "metrics": True}
    # rules
    issues, cov = lint_rules(Path("packages/rules/triage"))
    if issues:
        results["rules"] = False
    # audit
    from packages.common.config import settings
    ok = verify_chain(Path(settings.audit_log_path))
    results["audit"] = bool(ok)
    # metrics presence optional
    if strict and not Path("var/reports/simulate_lead_triage.json").exists():
        results["metrics"] = False
    return results

