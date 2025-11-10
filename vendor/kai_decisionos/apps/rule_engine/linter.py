from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple

import yaml


@dataclass
class LintIssue:
    kind: str  # conflict | shadow | duplicate_name
    message: str
    rule: str
    other: str | None = None


def _load_rules_from_dir(path: Path) -> List[dict]:
    items: List[dict] = []
    for p in sorted(path.rglob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for r in data.get("rules", []) or []:
            r_copy = dict(r)
            r_copy["__file__"] = str(p)
            items.append(r_copy)
    return items


def _norm_when(when: str) -> str:
    return "".join(when.split()) if isinstance(when, str) else ""


def lint_rules(path: str | Path) -> Tuple[List[LintIssue], Dict[str, float]]:
    path = Path(path)
    rules = _load_rules_from_dir(path)
    issues: List[LintIssue] = []

    # Duplicate names
    seen_names: Dict[str, str] = {}
    for r in rules:
        name = r.get("name")
        if name in seen_names:
            issues.append(LintIssue("duplicate_name", f"Duplicate rule name '{name}'", name, seen_names[name]))
        else:
            seen_names[name] = r.get("__file__", "")

    # Conflicts and shadowing (simple heuristic: identical predicate with different class)
    by_when: Dict[str, List[dict]] = {}
    for r in rules:
        w = _norm_when(r.get("when", ""))
        by_when.setdefault(w, []).append(r)
    for w, group in by_when.items():
        if len(group) <= 1:
            continue
        classes = { (r.get("action") or {}).get("class") for r in group }
        if len(classes) > 1:
            for r in group:
                issues.append(LintIssue("conflict", f"Same predicate different class: {classes}", r.get("name", ""), None))
        # Shadowing: earlier higher priority with stop:true makes later unreachable
        ordered = sorted(group, key=lambda r: (-(r.get("priority") or 0)))
        if ((ordered[0].get("stop") is True) or (ordered[0].get("action") or {}).get("class")) and len(ordered) > 1:
            for r in ordered[1:]:
                issues.append(LintIssue("shadow", f"Shadowed by higher-priority rule with same predicate", r.get("name", ""), ordered[0].get("name", "")))

    total = max(len(rules), 1)
    with_priority = sum(1 for r in rules if "priority" in r)
    with_stop = sum(1 for r in rules if "stop" in r)
    with_action_class = sum(1 for r in rules if (r.get("action") or {}).get("class") is not None)
    coverage = {
        "rules": float(total),
        "priority_pct": round(100.0 * with_priority / total, 2),
        "stop_pct": round(100.0 * with_stop / total, 2),
        "action_class_pct": round(100.0 * with_action_class / total, 2),
    }
    return issues, coverage


def main():
    parser = argparse.ArgumentParser(description="Rule linter")
    parser.add_argument("path", type=str, help="Rules directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fail-on", choices=["conflict", "shadow", "duplicate_name", "any"],
                       default="conflict", help="Exit with code 2 on specific issue types")
    args = parser.parse_args()
    issues, coverage = lint_rules(args.path)

    if args.json:
        # JSON output format
        output = {
            "issues": [
                {
                    "kind": i.kind,
                    "message": i.message,
                    "rule": i.rule,
                    "other": i.other
                } for i in issues
            ],
            "coverage": coverage,
            "summary": {
                "total_issues": len(issues),
                "by_kind": {
                    kind: sum(1 for i in issues if i.kind == kind)
                    for kind in {"conflict", "shadow", "duplicate_name"}
                }
            }
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"=== Lint Report ===")
        print(f"Total rules analyzed: {int(coverage['rules'])}")
        print()

        if issues:
            print(f"Issues found: {len(issues)}")
            for i in issues:
                other_info = f" (conflicts with: {i.other})" if i.other else ""
                print(f"  [{i.kind.upper()}] {i.rule}: {i.message}{other_info}")
        else:
            print("No issues found!")

        print()
        print("=== Coverage Summary ===")
        print(f"  Rules with priority: {coverage['priority_pct']}%")
        print(f"  Rules with stop flag: {coverage['stop_pct']}%")
        print(f"  Rules with action.class: {coverage['action_class_pct']}%")

    # Determine exit code
    should_fail = False
    if args.fail_on == "any" and issues:
        should_fail = True
    elif args.fail_on == "conflict" and any(i.kind == "conflict" for i in issues):
        should_fail = True
    elif args.fail_on == "shadow" and any(i.kind == "shadow" for i in issues):
        should_fail = True
    elif args.fail_on == "duplicate_name" and any(i.kind == "duplicate_name" for i in issues):
        should_fail = True

    if should_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

