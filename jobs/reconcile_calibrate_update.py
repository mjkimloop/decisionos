#!/usr/bin/env python3
import json, argparse, os
from apps.ops.optimizer.calibration import compute_gain, apply_calibration_to_ab_report
from apps.ops.optimizer.bayesian import update_pwin_beta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab-report", default="var/optimizer/ab_report.json")
    ap.add_argument("--canary-compare", default="var/canary/compare.json")
    ap.add_argument("--canary-windows", default="var/canary/windows.json")  # optional
    ap.add_argument("--out-dir", default="var/optimizer")
    ap.add_argument("--prior-alpha", type=float, default=2.0)
    ap.add_argument("--prior-beta", type=float, default=2.0)
    ap.add_argument("--topk", type=int, default=0)  # reserved
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    ab = json.load(open(args.ab_report, "r", encoding="utf-8"))

    # 관측 윈도 로드
    wins = 0
    trials = 0
    obs_series = []
    try:
        w = json.load(open(args.canary_windows, "r", encoding="utf-8"))
        arr = w.get("windows", [])
        for it in arr:
            d = float(it.get("score_delta", it.get("raw_delta", 0.0)))
            obs_series.append(d)
            trials += 1
            if d > 0:
                wins += 1
    except FileNotFoundError:
        cmp = json.load(open(args.canary_compare, "r", encoding="utf-8"))
        d = float(cmp.get("delta", {}).get("score_delta", cmp.get("delta", {}).get("raw_delta", 0.0)))
        trials = 1
        wins = 1 if d > 0 else 0
        obs_series = [d]

    # 예측 시계열(없으면 단일 mean 사용)
    pred_series = []
    delta = ab.get("delta", {})
    if "series" in delta:
        pred_series = [float(x) for x in delta["series"][:len(obs_series)]]
    elif "mean" in delta:
        pred_series = [float(delta["mean"])] * len(obs_series)
    else:
        pred_series = [float(delta.get("objective", 0.0))] * len(obs_series)

    # 교정치 산출 & 적용
    calib = compute_gain(pred_series, obs_series)
    with open(os.path.join(args.out_dir, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(calib, f, ensure_ascii=False, indent=2)
    ab_cal = apply_calibration_to_ab_report(ab, calib["gain"])
    with open(os.path.join(args.out_dir, "ab_report_calibrated.json"), "w", encoding="utf-8") as f:
        json.dump(ab_cal, f, ensure_ascii=False, indent=2)

    # p_win 베이지안 업데이트
    prior_p = float(delta.get("p_win", 0.5))
    # Beta 사전 알파/베타는 prior 평균에 맞추되 집중도는 인자로
    prior_a = args.prior_alpha * prior_p
    prior_b = args.prior_beta * (1 - prior_p)
    post = update_pwin_beta(prior_a, prior_b, wins, trials)
    with open(os.path.join(args.out_dir, "posterior_pwin.json"), "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    print("[OK] calibration.json, ab_report_calibrated.json, posterior_pwin.json")

if __name__ == "__main__":
    main()
