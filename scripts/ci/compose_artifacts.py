#!/usr/bin/env python3
"""Compose artifact links for CI summary."""
import json
import os
from pathlib import Path

repo = os.getenv("GITHUB_REPOSITORY")
base = os.getenv("GITHUB_SERVER_URL", "https://github.com")
run_id = os.getenv("GITHUB_RUN_ID")
run_url = f"{base}/{repo}/actions/runs/{run_id}" if repo and run_id else ""
artifacts = [
    {"name": "reason-trend", "url": run_url + "#artifacts"} if run_url else None,
    {"name": "evidence", "url": run_url + "#artifacts"} if run_url else None,
]
payload = {"artifacts": [a for a in artifacts if a]}
out = Path("var/reports")
out.mkdir(parents=True, exist_ok=True)
out.joinpath("artifacts.json").write_text(json.dumps(payload), encoding="utf-8")
print(f"[compose_artifacts] wrote {len(payload['artifacts'])} artifacts to var/reports/artifacts.json")
