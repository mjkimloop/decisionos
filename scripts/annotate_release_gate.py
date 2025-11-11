#!/usr/bin/env python3
import os, sys, json, time, hashlib, textwrap
from typing import Dict, Any
try:
    import requests
except Exception:
    print("requests 필요: pip install requests", file=sys.stderr); sys.exit(2)

MARKER = "<!-- decisionos:release-gate:v5 -->"

def h(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()[:8]

def render(evidence: Dict[str,Any], diff_link: str, artifacts: Dict[str,str], catalog_hash: str) -> str:
    reasons = evidence.get("reasons", []) or evidence.get("anomaly", {})
    top = evidence.get("top_impact", {})  # optional
    body = []
    body.append(MARKER)
    body.append("## ✅ Release Gate Result")
    body.append("")
    body.append(f"**Diff:** {diff_link}" if diff_link else "")
    if artifacts:
        body.append("**Artifacts:** " + ", ".join(f"[{k}]({v})" for k,v in artifacts.items()))
    body.append(f"**Label Catalog Hash:** `{catalog_hash}`")
    body.append("")
    # Compact reasons
    if isinstance(reasons, list) and reasons:
        body.append("**Primary Reasons**")
        for r in reasons[:8]:
            code = r.get("code","n/a"); msg=r.get("message","")
            body.append(f"- `{code}` — {msg}")
        body.append("")
    if top:
        body.append("**Top-Impact**")
        for k,v in list(top.items())[:5]:
            body.append(f"- {k}: {v}")
        body.append("")
    body.append("_automated by DecisionOS_")
    return "\n".join([x for x in body if x is not None])

def upsert_comment(repo: str, pr: int, token: str, body: str):
    hdr={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}"} if token else {"Accept":"application/vnd.github+json"}
    base=f"https://api.github.com/repos/{repo}"
    # find existing
    r = requests.get(f"{base}/issues/{pr}/comments?per_page=100", headers=hdr, timeout=20); r.raise_for_status()
    comments = r.json()
    target_id = None
    for c in comments:
        if c.get("body","").startswith(MARKER):
            target_id = c["id"]; break
    if target_id:
        requests.patch(f"{base}/issues/comments/{target_id}", json={"body": body}, headers=hdr, timeout=20).raise_for_status()
    else:
        requests.post(f"{base}/issues/{pr}/comments", json={"body": body}, headers=hdr, timeout=20).raise_for_status()

def main():
    import argparse, pathlib
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--diff-link", default="")
    ap.add_argument("--artifacts-json", help='{"report":"url", ...}', default="{}")
    ap.add_argument("--catalog", required=True)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN","")
    with open(args.evidence,"r",encoding="utf-8") as f: ev = json.load(f)
    with open(args.catalog,"r",encoding="utf-8") as f: cat_raw=f.read()
    cat_hash = hashlib.sha256(cat_raw.encode()).hexdigest()

    body = render(ev, args.diff_link, json.loads(args.artifacts_json), cat_hash)
    upsert_comment(args.repo, args.pr, token, body)
    print("[OK] PR comment upserted.")

if __name__ == "__main__":
    main()
