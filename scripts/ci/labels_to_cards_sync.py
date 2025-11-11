#!/usr/bin/env python3
import os, sys, json, hashlib, urllib.request

OPS_URL = os.environ.get("OPS_API_URL", "http://localhost:8081")
TOKEN = os.environ.get("OPS_API_TOKEN", "")   # 내부용 토큰(예: RBAC 프록시)
CAT_PATH = sys.argv[1] if len(sys.argv) > 1 else "configs/ops/label_catalog.json"

def main():
    try:
        with open(CAT_PATH, "r", encoding="utf-8") as f:
            cat = json.load(f)
    except Exception as e:
        print(f"Skip: cannot load catalog: {e}")
        sys.exit(0)

    seed = hashlib.sha256(json.dumps(cat, sort_keys=True).encode()).hexdigest()
    payload = {"scope": "labels", "seed": seed}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{OPS_URL}/ops/admin/invalidate", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print("Ops cache invalidated:", r.status)
    except Exception as e:
        print("Warn: cannot reach Ops API (cached update will apply later):", e)

if __name__ == "__main__":
    main()
