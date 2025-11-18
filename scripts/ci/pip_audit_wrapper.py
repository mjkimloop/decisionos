from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_pip_audit(requirements: str) -> str:
    cmd = [sys.executable, "-m", "pip_audit", "-r", requirements, "-f", "json"]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return json.dumps({"error": "pip_audit_not_available", "results": []})
    if completed.stdout:
        return completed.stdout
    return json.dumps({"error": "pip_audit_failed", "stderr": completed.stderr})


def main() -> None:
    parser = argparse.ArgumentParser(description="pip-audit wrapper")
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--out", default="var/ci/pip_audit.json")
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result = run_pip_audit(args.requirements)
    Path(args.out).write_text(result, encoding="utf-8")
    print(f"[pip_audit] wrote {args.out}")


if __name__ == "__main__":
    main()
