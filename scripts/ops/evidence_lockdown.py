#!/usr/bin/env python3
"""
Evidence 불변성 강화 도구 (v0.5.11r-6)

기능:
1. var/evidence/*.json 스캔 및 인덱스 생성
2. 변조 감지 (SHA256 + 시그니처 검증)
3. S3 ObjectLock 자동 설정 (옵션)
4. manifest.jsonl 업데이트

Usage:
  python scripts/ops/evidence_lockdown.py --verify
  python scripts/ops/evidence_lockdown.py --lock --s3-bucket=my-bucket --s3-prefix=evidence/
  python scripts/ops/evidence_lockdown.py --manifest=var/evidence/manifest.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from apps.obs.evidence.indexer import scan_dir, write_index


def verify_integrity(root: str = "var/evidence") -> int:
    """
    Evidence 무결성 검증

    Returns:
        0: 정상, 1: 변조 감지
    """
    print(f"[lockdown] 스캔 중: {root}")
    index = scan_dir(root)

    summary = index.get("summary", {})
    tampered_count = summary.get("tampered", 0)

    print(f"[lockdown] 파일 수: {summary.get('count', 0)}")
    print(f"[lockdown] LOCKED: {summary.get('locked', 0)}")
    print(f"[lockdown] WIP: {summary.get('wip', 0)}")
    print(f"[lockdown] 변조 감지: {tampered_count}")

    if tampered_count > 0:
        print("\n⚠️  변조된 Evidence 파일:", file=sys.stderr)
        for f in index.get("files", []):
            if f.get("tampered"):
                print(f"  - {f['path']}: {f.get('error', 'signature mismatch')}", file=sys.stderr)
        return 1

    print("\n✅ 모든 Evidence 파일 무결성 확인")
    return 0


def write_manifest(root: str = "var/evidence", manifest_path: str | None = None) -> str:
    """
    manifest.jsonl 생성 (각 Evidence 파일 1줄씩)

    Format:
        {"path": "evidence-123.json", "sha256": "abc...", "tier": "LOCKED", "mtime": "2025-01-11T..."}
    """
    index = scan_dir(root)
    manifest_file = Path(manifest_path) if manifest_path else Path(root) / "manifest.jsonl"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)

    with manifest_file.open("w", encoding="utf-8") as f:
        for entry in index.get("files", []):
            record = {
                "path": entry["path"],
                "sha256": entry["sha256"],
                "tier": entry["tier"],
                "mtime": entry["mtime"],
                "tampered": entry.get("tampered", False),
            }
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"[lockdown] manifest 작성: {manifest_file} ({index['summary']['count']} 파일)")
    return str(manifest_file)


def lock_to_s3(root: str, bucket: str, prefix: str, retain_days: int = 7) -> int:
    """
    Evidence 파일을 S3에 업로드하고 ObjectLock 적용

    Returns:
        0: 성공, 1: 실패
    """
    try:
        import boto3
        from botocore.client import Config
        from datetime import datetime, timedelta, timezone
    except ImportError:
        print("[lockdown] boto3 필요: pip install boto3", file=sys.stderr)
        return 1

    index = scan_dir(root)
    client = boto3.client("s3", config=Config(signature_version="s3v4"))

    uploaded = 0
    for f in index.get("files", []):
        if f.get("tampered"):
            print(f"[lockdown] 스킵 (변조): {f['path']}", file=sys.stderr)
            continue

        local_path = Path(root) / f["path"]
        s3_key = f"{prefix}{f['path']}"

        # ObjectLock 적용 업로드
        try:
            retain_until = datetime.now(timezone.utc) + timedelta(days=retain_days)
            body = local_path.read_bytes()

            client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=body,
                ContentType="application/json",
                ObjectLockMode="COMPLIANCE",
                ObjectLockRetainUntilDate=retain_until,
                Metadata={
                    "decisionos-evidence": "1",
                    "sha256": f["sha256"],
                    "tier": f["tier"],
                },
            )
            print(f"[lockdown] 업로드: s3://{bucket}/{s3_key} (LOCKED until {retain_until.date()})")
            uploaded += 1
        except Exception as e:
            print(f"[lockdown] 업로드 실패: {f['path']} - {e}", file=sys.stderr)

    print(f"\n[lockdown] S3 업로드 완료: {uploaded}/{index['summary']['count']} 파일")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence 불변성 강화 도구")
    parser.add_argument("--root", default="var/evidence", help="Evidence 디렉토리")
    parser.add_argument("--verify", action="store_true", help="무결성 검증만 수행")
    parser.add_argument("--index", action="store_true", help="index.json 생성")
    parser.add_argument("--manifest", help="manifest.jsonl 경로 (기본: {root}/manifest.jsonl)")
    parser.add_argument("--lock", action="store_true", help="S3 ObjectLock 적용")
    parser.add_argument("--s3-bucket", help="S3 버킷 이름 (--lock 시 필수)")
    parser.add_argument("--s3-prefix", default="evidence/", help="S3 키 접두사")
    parser.add_argument("--retain-days", type=int, default=7, help="ObjectLock 보관 기간 (일)")

    args = parser.parse_args()

    # 1. 무결성 검증
    if args.verify or args.lock:
        rc = verify_integrity(args.root)
        if rc != 0:
            print("\n❌ 변조 감지로 중단", file=sys.stderr)
            return rc

    # 2. 인덱스 생성
    if args.index:
        out_path = write_index(args.root)
        print(f"[lockdown] 인덱스 생성: {out_path}")

    # 3. manifest 생성
    if args.manifest or args.lock:
        manifest_path = write_manifest(args.root, args.manifest)

    # 4. S3 ObjectLock
    if args.lock:
        if not args.s3_bucket:
            print("❌ --s3-bucket 필수", file=sys.stderr)
            return 1
        return lock_to_s3(args.root, args.s3_bucket, args.s3_prefix, args.retain_days)

    return 0


if __name__ == "__main__":
    sys.exit(main())
