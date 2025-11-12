#!/usr/bin/env python3
"""
Shadow Autotune Job
적응형 샘플링 비율 자동 조정
"""
import os
import json
import argparse
from apps.experiment.shadow_sampler import load_sampler_config, adjust_sample_pct
from apps.ops.metrics import update_shadow_pct


def load_current_shadow_pct(path: str = "var/shadow/current_pct.json") -> tuple[float, float]:
    """현재 샘플링 % 및 마지막 변경 시각 로드"""
    if not os.path.exists(path):
        return 10.0, 0.0  # 기본값: 10%, timestamp 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("pct", 10.0), data.get("last_change_ts", 0.0)


def load_load_signals(path: str = "var/metrics/load.json") -> dict:
    """부하 신호 로드"""
    if not os.path.exists(path):
        print(f"[WARN] Load signals not found: {path}, using defaults")
        return {"qps": 100, "cpu": 0.3, "queue_depth": 5}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_shadow_config(pct: float, timestamp: float, path: str = "var/shadow/current_pct.json"):
    """샘플링 % 저장"""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    data = {"pct": pct, "last_change_ts": timestamp}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/shadow/sampler.json")
    ap.add_argument("--current", default="var/shadow/current_pct.json")
    ap.add_argument("--load-signals", default="var/metrics/load.json")
    args = ap.parse_args()

    # Load
    config = load_sampler_config(args.config)
    current_pct, last_change_ts = load_current_shadow_pct(args.current)
    signals = load_load_signals(args.load_signals)

    print(f"[INFO] Current shadow pct: {current_pct:.2f}%")

    # Adjust
    new_pct, new_ts = adjust_sample_pct(current_pct, signals, config, last_change_ts)

    if new_pct != current_pct:
        print(f"[INFO] Adjusted shadow pct: {current_pct:.2f}% → {new_pct:.2f}%")
        write_shadow_config(new_pct, new_ts, args.current)
        update_shadow_pct(new_pct)
    else:
        print(f"[INFO] Shadow pct unchanged: {current_pct:.2f}%")
        update_shadow_pct(current_pct)

    print("[OK] Shadow autotune complete")


if __name__ == "__main__":
    main()
