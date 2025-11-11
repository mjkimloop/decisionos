#!/usr/bin/env python3
"""
Autotune Promote Threshold Job
- AB 리포트 히스토리 로드
- calibration gain 적용
- suggest_thresholds() 호출
- guard (bounds/slew/rollback) 적용
- policy.autotuned.json 출력
"""
import os, json, argparse, shutil
from apps.ops.optimizer.autotune import suggest_thresholds
from apps.ops.optimizer.guard import apply_bounds_slew, apply_bounds_slew_adaptive, should_rollback
from apps.ops.optimizer.adaptive import load_adaptive, load_bucket_stats, compute_adaptive_caps

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab-history", default="var/ab_reports/history.jsonl")
    ap.add_argument("--calibration", default="var/ab_reports/calibration.json")
    ap.add_argument("--base-policy", default="configs/canary/policy.json")
    ap.add_argument("--guard-config", default="configs/optimizer/autotune_guard.json")
    ap.add_argument("--adaptive-config", default="")
    ap.add_argument("--bucket-stats", default="var/metrics/bucket_stats.json")
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

    # Load base policy
    base_policy = {"promote": {"delta_threshold": 0.02, "p_win_threshold": 0.6, "min_windows": 5}}
    if os.path.exists(args.base_policy):
        base_policy = json.load(open(args.base_policy, "r", encoding="utf-8"))
    base = base_policy.get("promote", {})

    # Autotune
    proposed = suggest_thresholds(ab_reports, calibration_gain=cal_gain, safety_factor=args.safety_factor)

    # Load guard config
    guard = {"bounds": {}, "slew_rate": {}, "rollback": {"trigger": {"severity": [], "consecutive": 2}}}
    if os.path.exists(args.guard_config):
        guard = json.load(open(args.guard_config, "r", encoding="utf-8"))

    # Apply bounds and slew-rate (adaptive or static)
    if args.adaptive_config and os.path.exists(args.adaptive_config):
        # Adaptive mode
        adaptive_cfg = load_adaptive(args.adaptive_config)
        bucket_stats = load_bucket_stats(args.bucket_stats)
        base_caps = guard.get("slew_rate", {})
        adaptive_caps = compute_adaptive_caps(base_caps, bucket_stats, adaptive_cfg)
        guarded = apply_bounds_slew_adaptive(proposed, base, guard.get("bounds", {}), adaptive_caps)
        print(f"[ADAPTIVE] caps={adaptive_caps}")
    else:
        # Static mode
        guarded = apply_bounds_slew(proposed, base, guard.get("bounds", {}), guard.get("slew_rate", {}))

    # 롤백 판단
    drift_path = "var/alerts/posterior_drift.json"
    rollback = False
    try:
        if os.path.exists(drift_path):
            drift = json.load(open(drift_path, "r", encoding="utf-8"))
            rollback = should_rollback(drift, guard.get("rollback", {}).get("trigger", {}))
    except Exception as e:
        print(f"[WARN] Rollback check failed: {e}")

    # last_good 관리
    last_good = guard.get("rollback", {}).get("last_good_path", "configs/canary/policy.last_good.json")
    os.makedirs(os.path.dirname(last_good), exist_ok=True)
    if not os.path.exists(last_good) and os.path.exists(args.base_policy):
        shutil.copyfile(args.base_policy, last_good)

    # 롤백 또는 정상 업데이트
    if rollback:
        print("[ROLLBACK] Drift trigger → restore last_good")
        if os.path.exists(last_good):
            shutil.copyfile(last_good, args.out)
        else:
            print("[WARN] last_good not found, using base policy")
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            json.dump(base_policy, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    else:
        # 정상 업데이트
        policy = base_policy.copy()
        policy["promote"] = guarded
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(policy, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[OK] Guarded thresholds → {args.out}")
        print(f"  delta_threshold={guarded['delta_threshold']}, p_win_threshold={guarded['p_win_threshold']}, min_windows={guarded['min_windows']}")

if __name__ == "__main__":
    main()
