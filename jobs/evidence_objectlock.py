from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload evidence to S3 with Object Lock")
    parser.add_argument("--file", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--retain-days", type=int, default=7)
    parser.add_argument("--mode", choices=["COMPLIANCE", "GOVERNANCE"], default="COMPLIANCE")
    args = parser.parse_args()

    try:
        import boto3
        from botocore.client import Config
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"[objectlock] boto3 missing or unusable: {exc}", file=sys.stderr)
        return

    client = boto3.client("s3", config=Config(signature_version="s3v4"))
    body = Path(args.file).read_bytes()
    client.put_object(
        Bucket=args.bucket,
        Key=args.key,
        Body=body,
        ContentType="application/json",
        ObjectLockMode=args.mode,
        Metadata={"decisionos-evidence": "1"},
    )
    print(f"[objectlock] uploaded s3://{args.bucket}/{args.key} ({len(body)} bytes) mode={args.mode}")


if __name__ == "__main__":
    main()
