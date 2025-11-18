# -*- coding: utf-8 -*-
"""
Fail CI on:
- Windows 'NUL' file present at repo root
- zero-byte __init__.py (excluding allowlist)
Warn (non-fatal):
- comment-only __init__.py (auto-fixed by maintenance script)
"""
import json
import os
import sys
from pathlib import Path

EXCLUDE_DIRS = {".venv", "venv", "env", "vendor", "node_modules"}


def load_allowlist(path: str):
    allow = set()
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                allow.add(line.replace("\\", "/"))
    return allow


def is_comment_only(p: Path) -> bool:
    if not p.name.endswith(".py"):
        return False
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:
        return False
    code = [ln for ln in txt.splitlines() if ln.strip()]
    return bool(code) and all(ln.strip().startswith("#") for ln in code)


def scan_tree(root: Path, allowlist: set):
    errors, warnings = [], []
    nul = root / "NUL"
    try:
        nul_is_file = nul.exists() and nul.is_file()
    except Exception:
        nul_is_file = False
    if nul_is_file:
        errors.append("Ghost file 'NUL' must be removed")

    for p in root.rglob("__init__.py"):
        rel = str(p.relative_to(root)).replace("\\", "/")
        parts = set(Path(rel).parts)
        if EXCLUDE_DIRS & parts:
            continue
        if rel in allowlist:
            continue
        if p.stat().st_size == 0:
            errors.append(f"Zero-byte __init__: {rel}")
        elif is_comment_only(p):
            warnings.append(f"Comment-only __init__: {rel}")
    return {"errors": errors, "warnings": warnings}


def main():
    root = Path(".")
    allow_path = os.getenv("DECISIONOS_SKELETON_ALLOWLIST", "configs/ci/skeleton_allowlist.txt")
    allowlist = load_allowlist(allow_path)
    report = scan_tree(root, allowlist)
    print(json.dumps(report, ensure_ascii=False))
    if report["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
