#!/usr/bin/env python3
import os, sys, json, hashlib, time
from typing import Dict, Any, List, Tuple
try:
    import requests
except Exception:
    print("requests가 필요합니다: pip install requests", file=sys.stderr); sys.exit(2)

MARKER = "decisionos:labels-sync-v2"

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def github_api(repo: str, path: str) -> str:
    return f"https://api.github.com/repos/{repo}{path}"

def load_catalog(path: str) -> Tuple[Dict[str, Any], str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    d = json.loads(raw)
    h = sha256_hex(raw)
    d["_catalog_hash"] = h
    return d, h

def get_headers(token: str) -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def fetch_existing(repo: str, token: str) -> Dict[str, Dict[str, Any]]:
    url = github_api(repo, "/labels?per_page=100")
    r = requests.get(url, headers=get_headers(token), timeout=20)
    r.raise_for_status()
    return {x["name"]: x for x in r.json()}

def create_label(repo: str, token: str, name: str, color: str, description: str, dry: bool):
    url = github_api(repo, "/labels")
    payload = {"name": name, "color": color, "description": description}
    if dry:
        print(f"[DRY] CREATE {name} {color} {description}"); return
    requests.post(url, json=payload, headers=get_headers(token), timeout=20).raise_for_status()

def update_label(repo: str, token: str, orig_name: str, color: str, description: str, dry: bool):
    url = github_api(repo, f"/labels/{orig_name}")
    payload = {"new_name": orig_name, "color": color, "description": description}
    if dry:
        print(f"[DRY] UPDATE {orig_name} {color} {description}"); return
    requests.patch(url, json=payload, headers=get_headers(token), timeout=20).raise_for_status()

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # 카탈로그 로드 (토큰 없어도 해시 검증)
    cat, cat_hash = load_catalog(args.catalog)

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        print(f"[SKIP] GITHUB_TOKEN 없음: 라벨 동기화 skip. catalog_hash={cat_hash}", file=sys.stderr)
        print(f"catalog_hash={cat_hash}")  # stdout으로도 출력
        sys.exit(0)
    existing = fetch_existing(args.repo, token)

    # alias → canonical 매핑
    alias_to_name = {}
    for item in cat["labels"]:
        for al in item.get("aliases", []):
            alias_to_name[al] = item["name"]

    # 생성/업데이트
    for item in cat["labels"]:
        nm, color, desc = item["name"], item["color"], item.get("description","")
        if nm not in existing:
            create_label(args.repo, token, nm, color, desc, args.dry_run)
        else:
            cur = existing[nm]
            if (cur.get("color","").lower()!=color.lower()) or (cur.get("description") or "") != desc:
                update_label(args.repo, token, nm, color, desc, args.dry_run)

    # alias 정리: 존재하면 canonical로 색/설명 동기화
    for al, canon in alias_to_name.items():
        if al in existing:
            # alias는 유지하되(호환), 외형을 canonical과 맞춤
            canon_item = next(x for x in cat["labels"] if x["name"]==canon)
            update_label(args.repo, token, al, canon_item["color"], f"alias of {canon}", args.dry_run)

    print(f"[OK] labels synced. catalog_hash={cat_hash}  #{MARKER}")

if __name__ == "__main__":
    main()
