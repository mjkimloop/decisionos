#!/usr/bin/env python3
import os, sys, json
from apps.ops.optimizer.bayes import WeightOptimizer, build_space_from_catalog, default_loglik_from_index, HistoryPoint

def load_index_stats(path: str):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--index-stats", required=True, help="evidence index 요약(그룹별 incidents/cost 등)")
    ap.add_argument("--history", default="", help="이전 탐색/운영 결과(옵션)")
    ap.add_argument("--out", default="var/optimizer/weights_suggestion.json")
    ap.add_argument("--commit", action="store_true", help="catalog v2 groups.weight 갱신")
    args = ap.parse_args()

    os.makedirs("var/optimizer", exist_ok=True)
    space = build_space_from_catalog(args.catalog)
    index_stats = load_index_stats(args.index_stats)
    loglik = default_loglik_from_index(index_stats)

    history=[]
    if args.history and os.path.exists(args.history):
        with open(args.history,"r",encoding="utf-8") as f:
            for row in json.load(f):
                history.append(HistoryPoint(weights=row["weights"], objective=row["objective"], meta=row.get("meta",{})))

    opt = WeightOptimizer(space)
    w = opt.suggest(history, loglik, n_iter=60)

    result = {"suggested_weights": w, "objective_estimate": loglik(w)}
    with open(args.out,"w",encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] suggestion saved: {args.out}")

    if args.commit:
        cat = json.load(open(args.catalog,"r",encoding="utf-8"))
        for g in cat.get("groups",{}):
            if g in w: cat["groups"][g]["weight"] = round(float(w[g]), 3)
        json.dump(cat, open(args.catalog,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[OK] catalog updated")

if __name__=="__main__":
    main()
