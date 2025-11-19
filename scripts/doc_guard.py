# -*- coding: utf-8 -*-
"""
문서 가드:
- AUTOGEN 마커 짝/중복 확인
- meta 헤더(version/date/status/summary) 확인(유효한 Work Order가 있을 때만)
- --strict 시 wo_apply --all --check로 out-of-sync 감지
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from typing import Dict, List

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
        try:
            with open(f, "r", encoding="utf-8") as fh:
                wo = yaml.safe_load(fh)
                if isinstance(wo, dict) and "meta" in wo:
                    meta = wo["meta"]
        except Exception:
            continue
    return meta


def main():
    strict = "--strict" in sys.argv
    errors: List[str] = []

    meta = latest_work_order_meta()
    for path in (TECHSPEC, PLAN):
        if not path.exists():
            errors.append(f"DOC003: {path} 없음")
            continue
        text = path.read_text(encoding="utf-8")
        errors += check_markers(text)
        if meta and meta.get("version") and meta.get("date"):
            hdr = parse_header(text)
            if not all([hdr.get("version"), hdr.get("date"), hdr.get("status")]):
                errors.append("DOC003: 헤더 누락")
            elif hdr.get("version") != meta.get("version"):
                errors.append("DOC003: 헤더 버전 불일치")

    if strict:
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
