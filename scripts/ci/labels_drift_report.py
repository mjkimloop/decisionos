#!/usr/bin/env python3
import os, sys, json, hashlib, time
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def gh_api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    if not REPO:
        print("Missing GITHUB_REPOSITORY", file=sys.stderr); sys.exit(0)
    catalog_path = sys.argv[1] if len(sys.argv) > 1 else "configs/ops/label_catalog.json"
    try:
        gh_labels = gh_api(f"/repos/{REPO}/labels")
    except Exception as e:
        print(f"Warn: cannot fetch GH labels: {e}", file=sys.stderr); sys.exit(0)

    cat = load_json(catalog_path)
    cat_map = {x["name"]: x for x in cat.get("labels", [])}
    gh_map = {x["name"]: x for x in gh_labels}

    drift = {"missing_on_github": [], "extra_on_github": [], "meta_mismatch": []}
    for name, meta in cat_map.items():
        if name not in gh_map:
            drift["missing_on_github"].append(name)
        else:
            gh = gh_map[name]
            if (gh.get("color") != meta.get("color")) or (gh.get("description") or "") != (meta.get("description") or ""):
                drift["meta_mismatch"].append({"name": name, "want": meta, "have": {"color": gh.get("color"), "description": gh.get("description")}})

    for name in gh_map.keys():
        if name.startswith("reason:") and name not in cat_map:
            drift["extra_on_github"].append(name)

    out = {
        "repo": REPO,
        "ts": int(time.time()),
        "catalog_sha256": hashlib.sha256(json.dumps(cat, sort_keys=True).encode()).hexdigest(),
        "drift": drift
    }
    os.makedirs("reports", exist_ok=True)
    with open("reports/labels_drift.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("labels_drift.json generated at reports/")

if __name__ == "__main__":
    main()
