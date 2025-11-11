#!/usr/bin/env python3
"""
Autotune Promote Threshold Job
- AB 리포트 히스토리 로드
- calibration gain 적용
- suggest_thresholds() 호출
- policy.autotuned.json 출력
"""
import os, json, argparse
from apps.ops.optimizer.autotune import suggest_thresholds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab-history", default="var/ab_reports/history.jsonl")
    ap.add_argument("--calibration", default="var/ab_reports/calibration.json")
    ap.add_argument("--out", default="var/policy/policy.autotuned.json")
    ap.add_argument("--safety-factor", type=float, default=2.0)
    args = ap.parse_args()

    # Load AB history
    ab_reports = []
    if os.path.exists(args.ab_history):
        with open(args.ab_history, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ab_reports.append(json.loads(line))

    # Load calibration gain
    cal_gain = 1.0
    if os.path.exists(args.calibration):
        cal = json.load(open(args.calibration, "r", encoding="utf-8"))
        cal_gain = cal.get("gain", 1.0)

    # Autotune
    result = suggest_thresholds(ab_reports, calibration_gain=cal_gain, safety_factor=args.safety_factor)

    # Output
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] Autotuned thresholds → {args.out}")
    print(f"  delta_threshold={result['delta_threshold']}, p_win_threshold={result['p_win_threshold']}, min_windows={result['min_windows']}")

if __name__ == "__main__":
    main()
