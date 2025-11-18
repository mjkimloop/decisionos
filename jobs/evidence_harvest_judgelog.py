from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from apps.obs.evidence.ops import merge_blocks
from apps.obs.witness.canary_compare import compare as compare_canary
from apps.obs.witness.judge_perf_io import parse_judge_log_csv, summarize_judge_perf


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest judgelog → perf_judge (and optional canary) blocks")
    parser.add_argument("--judgelog", default="var/log/judgelog.csv", help="judge request log CSV")
    parser.add_argument("--out-json", default="var/evidence/perf-judge-latest.json", help="output JSON path")
    parser.add_argument("--evidence", help="Evidence JSON to merge perf_judge/canary blocks")
    parser.add_argument("--canary-json", help="Optional canary comparison JSON (control/canary CSV already compared)")
    parser.add_argument("--canary-control", help="Optional control CSV to compute canary deltas on the fly")
    parser.add_argument("--canary-canary", help="Optional canary CSV to compute canary deltas on the fly")
    parser.add_argument("--windows-json", help="Optional path to canary windows list")
    parser.add_argument("--s3-uri", help="Optional s3://bucket/key for uploading perf_judge JSON")
    return parser.parse_args()


def _upload_to_s3(local_path: Path, s3_uri: str) -> None:
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional path
        raise SystemExit("[evidence_harvest_judgelog] boto3 is required for --s3-uri") from exc
    if not s3_uri.startswith("s3://"):
        raise SystemExit(f"invalid s3 uri: {s3_uri}")
    bucket_key = s3_uri[5:]
    bucket, _, key = bucket_key.partition("/")
    if not bucket or not key:
        raise SystemExit(f"invalid s3 uri (bucket/key required): {s3_uri}")
    boto3.client("s3").upload_file(str(local_path), bucket, key)


def _load_canary(args: argparse.Namespace) -> Dict[str, Any] | None:
    if args.canary_json:
        return json.loads(Path(args.canary_json).read_text(encoding="utf-8"))
    if args.canary_control and args.canary_canary:
        return compare_canary(args.canary_control, args.canary_canary)
    block: Dict[str, Any] = {}
    if args.windows_json and Path(args.windows_json).exists():
        try:
            block["windows"] = json.loads(Path(args.windows_json).read_text(encoding="utf-8"))
        except Exception:
            pass
    return block or None


def main() -> None:
    args = _parse_args()
    judgelog_path = Path(args.judgelog)
    if not judgelog_path.exists():
        print(f"[evidence_harvest_judgelog] judgelog not found: {judgelog_path}", file=sys.stderr)
        raise SystemExit(1)

    requests = parse_judge_log_csv(str(judgelog_path))
    summary: Dict[str, Any] = summarize_judge_perf(requests)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence_harvest_judgelog] perf_judge summary -> {out_path}")

    canary_block = _load_canary(args)
    if args.evidence:
        blocks: Dict[str, Any] = {"perf_judge": summary}
        if canary_block:
            blocks.setdefault("canary", {}).update(canary_block)
        merge_blocks(args.evidence, **blocks)
        merged_keys = ", ".join(blocks.keys())
        print(f"[evidence_harvest_judgelog] merged blocks[{merged_keys}] -> {args.evidence}")

    if args.s3_uri:
        _upload_to_s3(out_path, args.s3_uri)
        print(f"[evidence_harvest_judgelog] uploaded {out_path} -> {args.s3_uri}")


+if __name__ == "__main__":
+    main()
