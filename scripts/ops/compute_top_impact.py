#!/usr/bin/env python3
import argparse, json, math, sys
from collections import defaultdict

def guess_module(reason):
    if isinstance(reason, dict) and "module" in reason and reason["module"]:
        return reason["module"]
    code = (reason.get("code") or "").strip()
    return code.split(".", 1)[0] if "." in code else (code or "misc")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reasons", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.reasons, "r", encoding="utf-8") as f:
        reasons = json.load(f)
    with open(args.weights, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    weights = cfg.get("weights", {})
    top_n = int(cfg.get("top_n", 5))

    impact = defaultdict(float)
    buckets = defaultdict(int)

    for r in reasons or []:
        m = guess_module(r)
        w = float(weights.get(m, weights.get("misc", 1.0)))
        c = float(r.get("count", 1))
        impact[m] += w * c
        buckets[m] += int(c)

    ranked = sorted(
        [{"module": m, "score": round(s, 3), "events": buckets[m]} for m, s in impact.items()],
        key=lambda x: (-x["score"], -x["events"], x["module"])
    )[:top_n]

    out = {"top_impact": ranked, "weights": weights}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[top-impact] wrote {args.out} with {len(ranked)} entries")

if __name__ == "__main__":
    sys.exit(main())
