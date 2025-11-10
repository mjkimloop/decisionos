from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _collect_paths_and_meta(root: Path) -> Tuple[List[str], str | None, str]:
    if not root.exists():
        return [], None, "missing"

    index_path = root / "index.json"
    if index_path.exists():
        raw = index_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw) or {}
        except json.JSONDecodeError:
            data = {}
        items = data.get("files") or data.get("items") or []
        paths: List[str] = []
        for item in items:
            if item.get("tier") not in {"WIP", "LOCKED"}:
                continue
            rel = item.get("path")
            if not rel:
                continue
            candidate = root / rel
            if candidate.is_file():
                paths.append(str(candidate))
        last_updated = data.get("last_updated") or data.get("generated_at")
        signature = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return paths, last_updated, signature

    paths = sorted(
        str(path)
        for path in root.iterdir()
        if path.is_file() and path.name.endswith(".json") and path.name.startswith("evidence-")
    )
    latest_ts = 0.0
    sig_parts: List[str] = []
    for path_str in paths:
        candidate = Path(path_str)
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            continue
        latest_ts = max(latest_ts, stat.st_mtime)
        sig_parts.append(f"{candidate.name}:{int(stat.st_mtime_ns)}:{stat.st_size}")
    last_updated = (
        dt.datetime.fromtimestamp(latest_ts, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        if latest_ts
        else None
    )
    signature = hashlib.sha256("|".join(sig_parts).encode("utf-8")).hexdigest() if sig_parts else "missing"
    return paths, last_updated, signature


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


def get_index_signature(evidence_dir: str = "var/evidence") -> Tuple[str, str | None]:
    _, last_updated, signature = _collect_paths_and_meta(Path(evidence_dir))
    return signature, last_updated


def aggregate_reason_trend(evidence_dir: str = "var/evidence", days: int = 7) -> Dict[str, Any]:
    root_path = Path(evidence_dir)
    paths, last_updated, signature = _collect_paths_and_meta(root_path)
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
        "last_updated": last_updated,
        "index_signature": signature,
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
        f"- last_updated: {trend.get('last_updated')}",
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
