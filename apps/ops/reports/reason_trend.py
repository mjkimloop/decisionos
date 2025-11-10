from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def _iter_evidence_paths(root: str) -> List[str]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    index_path = root_path / "index.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        items = data.get("files") or data.get("items") or []
        return [
            str(root_path / item["path"])
            for item in items
            if item.get("tier") in {"WIP", "LOCKED"}
        ]
    return sorted(
        str(path)
        for path in root_path.iterdir()
        if path.is_file() and path.name.endswith(".json") and path.name.startswith("evidence-")
    )


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _extract_reason_codes(evidence_obj: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    for judge in evidence_obj.get("judges") or []:
        for reason in judge.get("reasons") or []:
            code = reason.get("code")
            if code:
                codes.append(code)
    return codes


def _extract_timestamp(evidence_obj: Dict[str, Any]) -> dt.datetime | None:
    meta = evidence_obj.get("meta") or {}
    iso_ts = meta.get("generated_at")
    if not iso_ts:
        return None
    try:
        return dt.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return None


def aggregate_reason_trend(evidence_dir: str = "var/evidence", days: int = 7) -> Dict[str, Any]:
    paths = _iter_evidence_paths(evidence_dir)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    daily: Dict[str, Counter] = defaultdict(Counter)
    total = Counter()

    for path in paths:
        payload = _load_json(path)
        ts = _extract_timestamp(payload)
        if not ts or ts < cutoff:
            continue
        day = ts.date().isoformat()
        for code in _extract_reason_codes(payload):
            daily[day][code] += 1
            total[code] += 1

    return {
        "window_days": days,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_top": total.most_common(20),
        "by_day": {day: counts.most_common(20) for day, counts in sorted(daily.items())},
        "count_evidence": sum(sum(counts.values()) for counts in daily.values()),
    }


def save_trend_reports(
    trend: Dict[str, Any],
    out_json: str = "var/reports/reason_trend.json",
    out_md: str = "var/reports/reason_trend.md",
) -> None:
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(trend, fh, ensure_ascii=False, indent=2)

    lines = [
        f"# Reason Trend (last {trend['window_days']} days)",
        f"- generated_at: {trend['generated_at']}",
        f"- total reason count: {trend['count_evidence']}",
        "## Top Reasons (overall)",
    ]
    for code, count in (trend.get("total_top") or [])[:10]:
        lines.append(f"- `{code}` x {count}")

    lines.append("## Daily Top-5")
    for day, pairs in trend.get("by_day", {}).items():
        lines.append(f"### {day}")
        for code, count in pairs[:5]:
            lines.append(f"- `{code}` x {count}")

    Path(out_md).parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate reason trends from evidence directory.")
    parser.add_argument("--dir", default="var/evidence")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json-out", default="var/reports/reason_trend.json")
    parser.add_argument("--md-out", default="var/reports/reason_trend.md")
    args = parser.parse_args()

    trend = aggregate_reason_trend(args.dir, args.days)
    save_trend_reports(trend, args.json_out, args.md_out)


if __name__ == "__main__":
    main()
