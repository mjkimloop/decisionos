#!/usr/bin/env python3
import json, os, argparse
from apps.ops.optimizer.simulator import simulate_ab, simulate_ab_bootstrap
from apps.ops.optimizer.sandbox import write_sandbox_catalog

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="configs/labels/label_catalog.v2.json")
    ap.add_argument("--index-stats", help="집계형 입력(JSON)")
    ap.add_argument("--history", help="부트스트랩용 히스토리(JSON)")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default="var/optimizer/ab_report.json")
    ap.add_argument("--traffic-split", type=float, default=0.5)
    ap.add_argument("--sandbox-out", default="var/sandbox/label_catalog.sandbox.json")
    ap.add_argument("--commit-sandbox", action="store_true")
    ap.add_argument("--iters", type=int, default=int(os.getenv("DECISIONOS_BOOTSTRAP_ITERS", "500")))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs("var/optimizer", exist_ok=True)
    baseline = json.load(open(args.catalog, "r", encoding="utf-8"))
    base_w = {g: float(meta.get("weight", 1.0)) for g, meta in baseline.get("groups", {}).items()}

    cand_raw = json.load(open(args.candidate, "r", encoding="utf-8"))
    cand_w = cand_raw.get("suggested_weights") or cand_raw

    if args.history:
        history = json.load(open(args.history, "r", encoding="utf-8"))
        report = simulate_ab_bootstrap(history, base_w, cand_w, args.traffic_split, args.iters, args.seed)
    else:
        if not args.index_stats:
            raise ValueError("Either --index-stats or --history must be provided")
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
