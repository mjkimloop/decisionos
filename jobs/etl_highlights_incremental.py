#!/usr/bin/env python3
import os, json, time, argparse, hashlib

def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def compute_highlights(index, catalog, k: int, weighted: bool = True):
    groups = list(catalog.get("groups", {}).keys())
    labels = [l["name"] for l in catalog.get("labels", [])]
    gw = {g: float(meta.get("weight", 1.0)) for g, meta in catalog.get("groups", {}).items()}
    matrix = {g: {l: 0.0 for l in labels} for g in groups}
    for r in index.get("rows", []):
        g, l, c = r.get("group"), r.get("label"), float(r.get("count", 0))
        if g in matrix and l in matrix[g]:
            matrix[g][l] += c
    cells = []
    for g in groups:
        for l in labels:
            val = matrix[g][l] * (gw.get(g, 1.0) if weighted else 1.0)
            if val > 0:
                cells.append({"group": g, "label": l, "value": float(val)})
    cells.sort(key=lambda x: x["value"], reverse=True)
    for i, c in enumerate(cells[:k], 1):
        c["rank"] = i
    return cells[:k]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="var/evidence/index/summary.json")
    ap.add_argument("--catalog", default="configs/labels/label_catalog.v2.json")
    ap.add_argument("--out-dir", default="var/cards/highlights")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--weighted", action="store_true", default=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    index = json.load(open(args.index, "r", encoding="utf-8"))
    catalog = json.load(open(args.catalog, "r", encoding="utf-8"))
    rev = index.get("rev", "0")
    items = compute_highlights(index, catalog, args.k, weighted=args.weighted)
    now = int(time.time())
    token = f"{rev}:{now}"

    # state
    state_path = os.path.join(args.out_dir, "state.json")
    state = {}
    if os.path.exists(state_path):
        state = json.load(open(state_path, "r", encoding="utf-8"))
    last_rev = state.get("last_rev")

    if last_rev == rev:
        # 동일 리비전이면 증분 없음 → 최신만 갱신
        pass
    else:
        # stream append
        line = json.dumps({"rev": rev, "token": token, "items": items}, ensure_ascii=False)
        with open(os.path.join(args.out_dir, "stream.jsonl"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
        state["last_rev"] = rev
        state["last_token"] = token
        json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # latest
    latest = {
        "rev": rev,
        "token": state.get("last_token", token),
        "items": items,
        "etag": sha({"rev": rev, "items": items})
    }
    json.dump(latest, open(os.path.join(args.out_dir, "latest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] highlights updated rev={rev} token={state.get('last_token', token)}")

if __name__ == "__main__":
    main()
