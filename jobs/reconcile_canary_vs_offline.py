#!/usr/bin/env python3
import json, argparse, math, os

def _safe(x):
    return float(x) if x is not None else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab-report", default="var/optimizer/ab_report.json")
    ap.add_argument("--canary", default="var/canary/compare.json")
    ap.add_argument("--out", default="var/optimizer/reconcile_report.json")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    ab = json.load(open(args.ab_report, "r", encoding="utf-8"))
    can = json.load(open(args.canary, "r", encoding="utf-8"))

    # 예측 Δ: objective 델타 평균(있으면), 없으면 fallback로 delta.objective 사용
    pred = ab.get("delta", {}).get("mean")
    if pred is None:
        pred = ab.get("delta", {}).get("objective", 0.0)
    pred = _safe(pred)

    # 실측 Δ: canary_compare 산출물에서 동일 스케일 델타(예: weighted score delta) 가정
    # 없으면 tokens/latency 등 단위 델타를 score로 환산하지 않고 raw_delta로 사용
    obs = _safe(can.get("delta", {}).get("score_delta", can.get("delta", {}).get("raw_delta", 0.0)))

    err = obs - pred
    mae = abs(err)
    mape = abs(err) / (abs(pred) + 1e-9)
    sign_agree = (obs == 0 and pred == 0) or (obs * pred > 0)
    calibration_ratio = (obs / pred) if abs(pred) > 1e-9 else float("inf")

    rep = {
        "predicted_delta": pred,
        "observed_delta": obs,
        "error": err,
        "mae": mae,
        "mape": mape,
        "sign_agreement": bool(sign_agree),
        "calibration_ratio": calibration_ratio
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"[OK] reconcile report saved: {args.out}")

if __name__ == "__main__":
    main()
