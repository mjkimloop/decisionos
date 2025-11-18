#!/usr/bin/env python3
"""Ensure rotation countdown labels exist in GitHub repo.

Creates/updates labels:
- rotation:soon-14 (orange) - Key expiry <=14 days
- rotation:soon-7 (darker orange) - Key expiry <=7 days
- rotation:soon-3 (red) - Key expiry <=3 days
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any, Dict, List, Optional

PALETTE = [
    {"name": "rotation:soon-14", "color": "e67e22", "description": "Key expiry <=14 days"},
    {"name": "rotation:soon-7", "color": "d35400", "description": "Key expiry <=7 days"},
    {"name": "rotation:soon-3", "color": "c0392b", "description": "Key expiry <=3 days"},
]


def call(method: str, url: str, token: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Make GitHub API call."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")

    payload = None
    if data is not None:
        payload = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, payload) as r:
            body = r.read().decode() or "{}"
            return json.loads(body)
    except Exception as e:
        print(f"[label] {method} {url} -> {e}", file=sys.stderr)
        return None


def main() -> int:
    """Main entry point."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("CI_REPO") or os.environ.get("GITHUB_REPOSITORY")

    if not token or not repo:
        print("no token/repo; skip")
        return 0

    # Fetch existing labels
    labels_resp = call("GET", f"https://api.github.com/repos/{repo}/labels?per_page=100", token) or []
    existing = {label["name"]: label for label in labels_resp}

    # Create or update labels
    for spec in PALETTE:
        name = spec["name"]
        if name not in existing:
            print(f"create label {name}")
            call("POST", f"https://api.github.com/repos/{repo}/labels", token, spec)
        else:
            cur = existing[name]
            color_changed = cur.get("color") != spec["color"]
            desc_changed = (cur.get("description") or "") != spec["description"]

            if color_changed or desc_changed:
                print(f"update label {name}")
                call("PATCH", f"https://api.github.com/repos/{repo}/labels/{name}", token, spec)

    return 0


if __name__ == "__main__":
    sys.exit(main())
