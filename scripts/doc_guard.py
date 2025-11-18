# -*- coding: utf-8 -*-
"""
문서 가드:
- AUTOGEN 마커 짝/중복 확인
- meta 헤더(version/date/status/summary) 확인
- 최신 Work Order 적용 필요 여부 확인(--strict 시 wo_apply --check 호출)
"""
from __future__ import annotations

import io
import pathlib
import re
import subprocess
import sys
from typing import Dict, List

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(".")
DOCS = ROOT / "docs"
TECHSPEC = DOCS / "techspec.md"
PLAN = DOCS / "plan.md"

HDR_VER = re.compile(r"version:\s*(v\d+\.\d+\.\d+)", re.I)
HDR_DATE = re.compile(r"date:\s*(\d{4}-\d{2}-\d{2})", re.I)
HDR_SUM = re.compile(r"summary:\s*(.*)")
HDR_STATUS = re.compile(r"status:\s*(\w+)", re.I)


def parse_header(text: str) -> Dict[str, str]:
    return {
        "version": HDR_VER.search(text).group(1) if HDR_VER.search(text) else "",
        "date": HDR_DATE.search(text).group(1) if HDR_DATE.search(text) else "",
        "status": HDR_STATUS.search(text).group(1) if HDR_STATUS.search(text) else "",
        "summary": HDR_SUM.search(text).group(1) if HDR_SUM.search(text) else "",
    }


def find_markers(text: str) -> List[str]:
    return re.findall(r"<!--\s*AUTOGEN:BEGIN:(.*?)\s*-->", text)


def check_markers(text: str) -> List[str]:
    errors = []
    begins = re.findall(r"<!--\s*AUTOGEN:BEGIN:(.*?)\s*-->", text)
    ends = re.findall(r"<!--\s*AUTOGEN:END:(.*?)\s*-->", text)
    if sorted(begins) != sorted(ends):
        errors.append("DOC001: 마커 BEGIN/END 불일치")
    dupes = [m for m in begins if begins.count(m) > 1]
    if dupes:
        errors.append("DOC004: 중복 섹션 " + ",".join(sorted(set(dupes))))
    return errors


def latest_work_order_meta() -> Dict[str, str]:
    files = sorted(pathlib.Path("docs/work_orders").glob("wo-*.yaml"))
    if not files:
        return {}
    import yaml

    meta = {}
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            wo = yaml.safe_load(fh)
            meta = wo.get("meta", meta)
    return meta


def main():
    strict = "--strict" in sys.argv
    errors: List[str] = []

    for path in (TECHSPEC, PLAN):
        if not path.exists():
            errors.append(f"DOC003: {path} 없음")
            continue
        text = path.read_text(encoding="utf-8")
        errors += check_markers(text)
        meta = latest_work_order_meta()
        if meta:
            hdr = parse_header(text)
            if not all([hdr.get("version"), hdr.get("date"), hdr.get("status")]):
                errors.append("DOC003: 헤더 누락")
            elif hdr.get("version") != meta.get("version"):
                errors.append("DOC003: 헤더 버전 불일치")

    if strict:
        # wo_apply --all --check로 out-of-sync 탐지
        proc = subprocess.run(
            [sys.executable, "scripts/wo_apply.py", "docs/work_orders/wo-*.yaml", "--all", "--check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.returncode != 0:
            errors.append("DOC002: Work Order 미반영")
            sys.stdout.write(proc.stdout)

    if errors:
        for e in errors:
            print(e)
        raise SystemExit(1)
    print("doc_guard: OK")


if __name__ == "__main__":
    main()
