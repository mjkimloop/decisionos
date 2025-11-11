#!/usr/bin/env python3
import os, sys, json, urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "")
PR = os.environ.get("PR_NUMBER", "")
MARK = os.environ.get("COMMENT_MARK", "<!-- decisionos-release-gate -->")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def gh(path, method="GET", data=None):
    req = urllib.request.Request(f"https://api.github.com{path}", method=method, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def main():
    if not (REPO and PR):
        print("Missing REPO/PR_NUMBER; skip"); sys.exit(0)

    body_path = sys.argv[1] if len(sys.argv) > 1 else "reports/release_gate_comment.md"
    try:
        body = open(body_path, "r", encoding="utf-8").read()
    except Exception as e:
        print("Skip: no body:", e); sys.exit(0)
    body_marked = f"{MARK}\n{body}\n{MARK}"

    # 읽기
    try:
        comments = gh(f"/repos/{REPO}/issues/{PR}/comments")
    except Exception as e:
        print("Skip: cannot fetch comments:", e); sys.exit(0)

    target = None
    for c in comments:
        if c.get("body","").find(MARK) != -1:
            target = c
            break

    payload = json.dumps({"body": body_marked}).encode()
    try:
        if target:
            gh(f"/repos/{REPO}/issues/comments/{target['id']}", "PATCH", payload)
            print("Comment updated")
        else:
            gh(f"/repos/{REPO}/issues/{PR}/comments", "POST", payload)
            print("Comment created")
    except Exception as e:
        print("Warn: comment upsert failed:", e)

if __name__ == "__main__":
    main()
