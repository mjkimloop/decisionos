from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def _load_report(path: str) -> dict:
    file = Path(path)
    if not file.exists():
        return {"scenario": Path(path).stem, "status": "missing", "checks": [], "notes": []}
    return json.loads(file.read_text(encoding="utf-8"))


def build_markdown(reports: List[dict]) -> str:
    lines = ["## GameDay Drill Summary", ""]
    if not reports:
        lines.append("_No GameDay runs found._")
        return "\n".join(lines)
    lines.append("| Scenario | Status | Duration (s) | Notes |")
    lines.append("| --- | --- | ---: | --- |")
    for rep in reports:
        notes = "; ".join(rep.get("notes", [])) or "—"
        lines.append(
            f"| `{rep.get('scenario')}` | {rep.get('status','unknown').upper()} | "
            f"{rep.get('duration_sec', 0)} | {notes} |"
        )
    lines.append("")
    lines.append("### Checks")
    for rep in reports:
        checks = ", ".join(f"{c.get('name')}={c.get('status')}" for c in rep.get("checks", []))
        lines.append(f"- **{rep.get('scenario')}**: {checks or 'no checks'}")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render GameDay markdown report")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--out", default="var/ci/gameday_report.md")
    args = parser.parse_args(argv)

    reports = [_load_report(path) for path in args.inputs]
    markdown = build_markdown(reports)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(markdown, encoding="utf-8")
    print(f"[gameday] report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
