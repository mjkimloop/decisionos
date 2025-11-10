from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from .schema import LintIssue, PackSpec


def lint_spec(spec: PackSpec) -> List[LintIssue]:
    issues: List[LintIssue] = []

    # Duplicate component IDs
    counter = Counter(c.id for c in spec.components)
    for comp_id, count in counter.items():
        if count > 1:
            issues.append(
                LintIssue(level="error", message="duplicate component id", subject=comp_id)
            )

    # Missing required contracts or rulesets
    if not spec.contracts:
        issues.append(LintIssue(level="warning", message="no contracts linked"))
    if not spec.rulesets:
        issues.append(LintIssue(level="warning", message="no rulesets linked"))

    # Ensure checklist items exist
    checklist_counter = Counter(spec.checklist)
    for item, count in checklist_counter.items():
        if count > 1:
            issues.append(LintIssue(level="warning", message="checklist item duplicated", subject=item))

    # Ensure version pattern already validated; surface info for readability
    if not spec.meta.description:
        issues.append(LintIssue(level="info", message="meta.description missing"))

    return issues


def summarize_levels(issues: Iterable[LintIssue]) -> dict[str, int]:
    counter = Counter(issue.level for issue in issues)
    return dict(counter)


__all__ = ["lint_spec", "summarize_levels"]

