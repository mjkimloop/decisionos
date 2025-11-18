# -*- coding: utf-8 -*-
"""
Skeleton hygiene auto-fixer:
- Remove Windows 'NUL' ghost file if present
- Ensure docstring in known empty or comment-only __init__.py
- Drop stale TODO lines by pattern (idempotent)
"""
import io
import json
import os
import re
import sys
from pathlib import Path

EMPTY_INITS = [
    "apps/ops/monitor/__init__.py",
    "scripts/policy/__init__.py",
    "tests/policy/__init__.py",
]

COMMENTY_INITS = [
    "apps/executor/__init__.py",
    "apps/obs/witness/__init__.py",
    "apps/expops/__init__.py",
]

STALE_TODO_PATTERNS = [
    r"TODO:\s*httpx 요청/서명/재시도\. MVP는 스텁",
]

DOCSTRINGS = {
    "apps/ops/monitor/__init__.py": '"""Monitor module."""\n',
    "scripts/policy/__init__.py": '"""Policy scripts."""\n',
    "tests/policy/__init__.py": '"""Policy tests."""\n',
    "apps/executor/__init__.py": '"""Executor module."""\n',
    "apps/obs/witness/__init__.py": '"""Witness module."""\n',
    "apps/expops/__init__.py": '"""Experiment Ops module."""\n',
}


def _ensure_docstring(p: Path, default_doc: str) -> bool:
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or p.stat().st_size == 0:
        p.write_text(default_doc, encoding="utf-8")
        return True
    content = p.read_text(encoding="utf-8")
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if lines and all(ln.strip().startswith("#") for ln in lines):
        p.write_text(default_doc, encoding="utf-8")
        return True
    return False


def _drop_stale_todos(p: Path, patterns) -> bool:
    if not p.exists():
        return False
    content = p.read_text(encoding="utf-8")
    new = content
    for pat in patterns:
        new = re.sub(pat + r".*\n?", "", new)
    if new != content:
        p.write_text(new, encoding="utf-8")
        return True
    return False


def main(root=".") -> int:
    root = Path(root)
    changed = {"removed": [], "fixed_inits": [], "todo_swept": []}

    # 1) Remove NUL if tracked/created
    nul = root / "NUL"
    if nul.exists():
        try:
            nul.unlink()
            changed["removed"].append("NUL")
        except Exception:
            pass

    # 2) Ensure docstrings
    for rel in EMPTY_INITS + COMMENTY_INITS:
        p = root / rel
        if _ensure_docstring(p, DOCSTRINGS.get(rel, '"""Module."""\n')):
            changed["fixed_inits"].append(rel)

    # 3) Sweep stale TODOs
    exec_plugins = root / "apps" / "executor" / "plugins.py"
    if _drop_stale_todos(exec_plugins, STALE_TODO_PATTERNS):
        changed["todo_swept"].append(str(exec_plugins))

    print(json.dumps(changed, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
