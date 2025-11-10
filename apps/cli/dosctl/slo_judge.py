"""
apps/cli/dosctl/slo_judge.py

CLI: dosctl judge slo --slo <file> --evidence <file> --quorum <k/n>
"""
import json
import sys
import os
from pathlib import Path
from apps.judge.slo_judge import evaluate
from apps.judge.quorum import decide


def main():
    import argparse

    ap = argparse.ArgumentParser(
        prog="dosctl judge slo", description="SLO-based deployment judgment"
    )
    ap.add_argument("--slo", required=True, help="Path to SLO JSON file")
    ap.add_argument("--evidence", required=True, help="Path to Evidence JSON file")
    ap.add_argument(
        "--quorum",
        default="1/1",
        help='Quorum format "k/n" (e.g., "2/3"). Default: "1/1"',
    )
    args = ap.parse_args()

    # RBAC Hook (더미/플러그 가능)
    if os.getenv("DECISIONOS_ENFORCE_RBAC") == "1":
        actor = os.getenv("USER", "unknown")
        # TODO: 실제 pep.enforce 연동
        # if not enforce_policy("judge.run", actor):
        #     print(f"[ERROR] RBAC: User '{actor}' not authorized for 'judge.run'", file=sys.stderr)
        #     sys.exit(3)

    # SLO 및 Evidence 로드
    try:
        slo = json.loads(Path(args.slo).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to load SLO: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        ev = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to load Evidence: {e}", file=sys.stderr)
        sys.exit(2)

    # Quorum 파싱
    try:
        k, n = map(int, args.quorum.split("/"))
    except Exception as e:
        print(f"[ERROR] Invalid quorum format: {e}", file=sys.stderr)
        sys.exit(2)

    # 멀티-저지 쿼럼 (현재는 Local Judge N개, 향후 타 Judge 연동 가능)
    providers = [evaluate] * n
    result = decide(providers, ev, slo, k=k, n=n)

    # 결과 출력
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))

    # Exit code: pass=0, fail=2
    sys.exit(0 if result["final"] == "pass" else 2)


if __name__ == "__main__":
    main()
