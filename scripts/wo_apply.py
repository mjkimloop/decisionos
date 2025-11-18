"""
Work Order → techspec.md / plan.md / index.md / CHANGELOG.md 자동 반영 스크립트.
특징: 멱등, 다중 워크오더(--all), 체크 모드(--check).
"""

from __future__ import annotations

import argparse
import io
import pathlib
import re
import sys
from typing import Dict, List, Tuple

import yaml

# Windows 콘솔 인코딩 대응
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(".")
DOCS = ROOT / "docs"
TS_DEFAULT = DOCS / "techspec.md"
PL_DEFAULT = DOCS / "plan.md"
IDX = DOCS / "index.md"
CHG = ROOT / "CHANGELOG.md"

BEGIN = lambda name: f"<!-- AUTOGEN:BEGIN:{name} -->"
END = lambda name: f"<!-- AUTOGEN:END:{name} -->"

HDR_VER = re.compile(r"version:\s*(v\d+\.\d+\.\d+)", re.I)
HDR_DATE = re.compile(r"date:\s*(\d{4}-\d{2}-\d{2})", re.I)
HDR_SUM = re.compile(r"summary:\s*(.*)")
HDR_STATUS = re.compile(r"status:\s*(\w+)", re.I)


class WorkOrderError(SystemExit):
    ...


def load_yaml(p: pathlib.Path) -> Dict:
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_file(path: pathlib.Path, default: str):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(default, encoding="utf-8")


def upsert_header_text(text: str, meta: Dict[str, str]) -> str:
    if "<!--" not in text or "version:" not in text:
        head = (
            f"<!--\nversion: {meta['version']}\n"
            f"date: {meta['date']}\n"
            f"status: {meta.get('status','draft')}\n"
            f"summary: {meta.get('summary','')}\n-->\n\n"
        )
        return head + text
    text = HDR_VER.sub(f"version: {meta['version']}", text, count=1)
    text = HDR_DATE.sub(f"date: {meta['date']}", text, count=1)
    text = HDR_STATUS.sub(f"status: {meta.get('status','draft')}", text, count=1)
    if meta.get("summary"):
        if HDR_SUM.search(text):
            text = HDR_SUM.sub(f"summary: {meta['summary']}", text, count=1)
        else:
            text = text.replace("-->", f"summary: {meta['summary']}\n-->", 1)
    return text


def apply_patch_text(current: str, section: str, mode: str, content: str) -> str:
    b, e = BEGIN(section), END(section)
    if b not in current:
        block = f"\n\n{b}\n{content.strip()}\n{e}\n"
        return current + block

    start = current.index(b) + len(b)
    end = current.index(e)
    before = current[:start]
    after = current[end:]
    inner = current[start:end]
    mode_l = mode.lower()
    if mode_l in ("replace", "upsert"):
        new_inner = "\n" + content.strip() + "\n"
    elif mode_l == "append":
        new_inner = inner.rstrip() + "\n" + content.strip() + "\n"
    elif mode_l == "ensure":
        new_inner = inner if inner.strip() else "\n" + content.strip() + "\n"
    else:
        raise WorkOrderError("WOS002")
    return before + new_inner + after


def ensure_index_and_changelog_text(index_text: str, changelog_text: str, meta: Dict) -> Tuple[str, str]:
    top = f"- {meta['version']} — {meta['date']} — {meta.get('summary','')}"
    idx_lines = index_text.splitlines()
    insert_at = 1 if idx_lines and idx_lines[0].startswith("#") else 0
    if insert_at < len(idx_lines):
        insert_at += 1
    if not any(meta["version"] in line for line in idx_lines):
        idx_lines.insert(insert_at, top)
        index_text = "\n".join(idx_lines) + "\n"

    entry = f"## {meta['version']} — {meta['date']}\n- {meta.get('summary','')}\n\n"
    if meta["version"] not in changelog_text:
        if not changelog_text.endswith("\n"):
            changelog_text += "\n"
        changelog_text += entry
    return index_text, changelog_text


def apply_work_order(
    wo: Dict, techspec_path: pathlib.Path, plan_path: pathlib.Path, check_only: bool = False
) -> bool:
    meta = wo["meta"]
    patches = wo.get("patches", {})

    ensure_file(techspec_path, "# TechSpec\n\n")
    ensure_file(plan_path, "# Plan\n\n")
    ts_text = techspec_path.read_text(encoding="utf-8")
    pl_text = plan_path.read_text(encoding="utf-8")
    idx_text = IDX.read_text(encoding="utf-8") if IDX.exists() else "# DecisionOS Docs — Version Index\n\n"
    chg_text = CHG.read_text(encoding="utf-8") if CHG.exists() else "# Changelog\n\n"

    ts_new = upsert_header_text(ts_text, meta)
    pl_new = upsert_header_text(pl_text, meta)

    for tgt, ops in patches.items():
        target_text = ts_new if tgt == "techspec" else pl_new
        for op in ops:
            section = op["section"]
            mode = op.get("mode", "replace")
            content = op.get("content", "")
            target_text = apply_patch_text(target_text, section, mode, content)
        if tgt == "techspec":
            ts_new = target_text
        else:
            pl_new = target_text

    idx_new, chg_new = ensure_index_and_changelog_text(idx_text, chg_text, meta)

    changed = any(
        new != old for new, old in ((ts_new, ts_text), (pl_new, pl_text), (idx_new, idx_text), (chg_new, chg_text))
    )
    if not check_only:
        techspec_path.write_text(ts_new, encoding="utf-8")
        plan_path.write_text(pl_new, encoding="utf-8")
        IDX.write_text(idx_new, encoding="utf-8")
        CHG.write_text(chg_new, encoding="utf-8")
    return changed


def load_work_orders(files: List[pathlib.Path]) -> List[Dict]:
    return [load_yaml(f) for f in files]


def parse_args():
    ap = argparse.ArgumentParser(description="Apply Work Order(s) to docs")
    ap.add_argument("work_orders", nargs="*", help="Work order yaml(s)")
    ap.add_argument("--all", action="store_true", help="docs/work_orders/wo-*.yaml 모두 적용")
    ap.add_argument("--check", action="store_true", help="변경 필요 여부만 확인")
    ap.add_argument("--techspec", default=str(TS_DEFAULT), help="techspec 경로")
    ap.add_argument("--plan", default=str(PL_DEFAULT), help="plan 경로")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.all:
        files = sorted(pathlib.Path("docs/work_orders").glob("wo-*.yaml"))
    else:
        files = [pathlib.Path(p) for p in args.work_orders]
    if not files:
        print("사용법: python scripts/wo_apply.py <work_order.yaml> [--all] [--check]")
        raise SystemExit(2)

    techspec_path = pathlib.Path(args.techspec)
    plan_path = pathlib.Path(args.plan)

    changed_any = False
    for wo_file in files:
        if not wo_file.exists():
            print(f"경고: 파일 없음 {wo_file}")
            continue
        try:
            wo = load_yaml(wo_file)
            changed = apply_work_order(wo, techspec_path, plan_path, check_only=args.check)
            changed_any = changed_any or changed
            print(f"APPLIED: {wo['meta']['version']} (check={args.check}, changed={changed})")
        except WorkOrderError as e:
            print(str(e))
            raise SystemExit(str(e))

    if args.check and changed_any:
        print("DOC002: Work Order 적용이 필요합니다 (변경 발생)")
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
