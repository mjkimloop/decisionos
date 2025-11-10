from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from apps.obs.evidence.ops import merge_blocks
from apps.obs.evidence.snapshot import sha256_file
from apps.obs.witness.perf import parse_reqlog_csv, summarize_perf


def _upload_to_s3(local_path: Path, s3_uri: str) -> None:
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional path
        raise SystemExit("[evidence_harvest_reqlog] boto3 is required for --s3-uri") from exc

    if not s3_uri.startswith("s3://"):
        raise SystemExit(f"invalid s3 uri: {s3_uri}")
    bucket_key = s3_uri[5:]
    bucket, _, key = bucket_key.partition("/")
    if not bucket or not key:
        raise SystemExit(f"invalid s3 uri (bucket/key required): {s3_uri}")
    boto3.client("s3").upload_file(str(local_path), bucket, key)


def _load_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest reqlog → perf evidence block")
    parser.add_argument("--reqlog", default="var/log/reqlog.csv", help="reqlog CSV path")
    parser.add_argument(
        "--out-json", default="var/evidence/perf-latest.json", help="output JSON path for perf summary"
    )
    parser.add_argument("--evidence", help="Evidence JSON to merge perf block into")
    parser.add_argument("--s3-uri", help="Optional s3://bucket/prefix/key for uploading the perf summary")
    parser.add_argument("--sha-out", help="Optional path to write SHA256(reqlog)")
    return parser.parse_args()


def main() -> None:
    args = _load_args()
    reqlog_path = Path(args.reqlog)
    if not reqlog_path.exists():
        print(f"[evidence_harvest_reqlog] reqlog not found: {reqlog_path}", file=sys.stderr)
        raise SystemExit(1)

    with reqlog_path.open("r", encoding="utf-8") as fh:
        rows = parse_reqlog_csv(fh)
    summary: Dict[str, Any] = summarize_perf(rows)

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence_harvest_reqlog] perf summary -> {out_path}")

    if args.sha_out:
        sha_path = Path(args.sha_out)
        sha_path.parent.mkdir(parents=True, exist_ok=True)
        sha_path.write_text(sha256_file(str(reqlog_path)), encoding="utf-8")
        print(f"[evidence_harvest_reqlog] sha256(reqlog) -> {sha_path}")

    if args.evidence:
        merge_blocks(args.evidence, perf=summary)
        print(f"[evidence_harvest_reqlog] perf merged into {args.evidence}")

    if args.s3_uri:
        _upload_to_s3(out_path, args.s3_uri)
        print(f"[evidence_harvest_reqlog] uploaded {out_path} -> {args.s3_uri}")


if __name__ == "__main__":
    main()
