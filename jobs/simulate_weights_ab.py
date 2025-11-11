#!/usr/bin/env python3
import json, os, argparse
from apps.ops.optimizer.simulator import simulate_ab
from apps.ops.optimizer.sandbox import write_sandbox_catalog

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="configs/labels/label_catalog.v2.json")
    ap.add_argument("--index-stats", required=True)  # var/evidence/index/group_stats.json
    ap.add_argument("--candidate", required=True)    # var/optimizer/weights_suggestion.json
    ap.add_argument("--out", default="var/optimizer/ab_report.json")
    ap.add_argument("--traffic-split", type=float, default=0.5)
    ap.add_argument("--sandbox-out", default="var/sandbox/label_catalog.sandbox.json")
    ap.add_argument("--commit-sandbox", action="store_true")
    args = ap.parse_args()

    os.makedirs("var/optimizer", exist_ok=True)
    baseline = json.load(open(args.catalog, "r", encoding="utf-8"))
    base_w = {g: float(meta.get("weight", 1.0)) for g, meta in baseline.get("groups", {}).items()}

    cand_raw = json.load(open(args.candidate, "r", encoding="utf-8"))
    cand_w = cand_raw.get("suggested_weights") or cand_raw  # 유연 처리

    index_stats = json.load(open(args.index_stats, "r", encoding="utf-8"))

    report = simulate_ab(index_stats, base_w, cand_w, args.traffic_split)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[OK] AB report saved: {args.out}")

    if args.commit_sandbox:
        path = write_sandbox_catalog(args.catalog, cand_w, args.sandbox_out)
        print(f"[OK] sandbox catalog written: {path}")

if __name__ == "__main__":
    main()
