#!/usr/bin/env python3
import argparse, json, os, subprocess, sys, re

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def match_any(code: str, patterns):
    for pat in patterns:
        # glob-like: convert * to .*
        rx = "^" + re.escape(pat).replace("\\*", ".*") + "$"
        if re.match(rx, code):
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reasons", required=True)
    ap.add_argument("--map", required=True, help="configs/ops/reason_labels.json")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", required=True)
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN missing", file=sys.stderr)
        sys.exit(3)

    reasons = load_json(args.reasons) or []
    mapping = load_json(args.map) or {}
    rules = mapping.get("map", [])
    max_labels = int(mapping.get("max_labels", 6))
    prefix = mapping.get("prefix", "reason:")

    # aggregate counts by code
    counts = {}
    for r in reasons:
        code = (r.get("code") or "").strip()
        if not code:
            continue
        counts[code] = counts.get(code, 0) + int(r.get("count", 1))

    # pick labels by rules and descending count
    candidates = []
    for code, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        for rule in rules:
            pats = [rule.get("match")] if isinstance(rule.get("match"), str) else (rule.get("match") or [])
            if any(match_any(code, [p]) for p in pats):
                for lab in rule.get("labels", []):
                    lbl = lab if lab.startswith(prefix) else (prefix + lab)
                    candidates.append(lbl)
                break

    # de-dup & cap
    labels = []
    seen = set()
    for l in candidates:
        if l not in seen:
            seen.add(l)
            labels.append(l)
        if len(labels) >= max_labels:
            break

    if not labels:
        print("[label] no labels resolved; skipping")
        return 0

    env = os.environ.copy()
    env["GH_TOKEN"] = token
    # POST labels (idempotent add)
    cmd = [
        "gh", "api", "-X", "POST",
        f"repos/{args.repo}/issues/{args.pr}/labels",
        "-f", f'labels={json.dumps(labels)}'
    ]
    print(f"[label] adding labels: {labels}")
    subprocess.check_call(cmd, env=env)
    return 0

if __name__ == "__main__":
    sys.exit(main())
