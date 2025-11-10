"""
Work Order 자동 적용 스크립트

Work Order YAML 파일을 읽어서:
1) docs/techspec.md와 docs/plan.md의 헤더(version/date/status/summary) 동기화
2) AUTOGEN 마커 섹션에 패치 적용 (replace/append/ensure 모드)
3) docs/index.md와 CHANGELOG.md 자동 업데이트

사용법:
    python scripts/wo_apply.py docs/work_orders/wo-v0.1.2-gate-a.yaml
"""

import sys
import json
import yaml
import pathlib
import re
import datetime
import subprocess
import io

# Windows 콘솔 인코딩 처리
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 경로 상수
ROOT = pathlib.Path('.')
DOCS = ROOT / 'docs'
TS = DOCS / 'techspec.md'
PL = DOCS / 'plan.md'
IDX = DOCS / 'index.md'
CHG = ROOT / 'CHANGELOG.md'

# 마커 함수
BEGIN = lambda name: f"<!-- AUTOGEN:BEGIN:{name} -->"
END   = lambda name: f"<!-- AUTOGEN:END:{name} -->"

# 헤더 정규식
HDR_VER = re.compile(r"version:\s*(v\d+\.\d+\.\d+)", re.I)
HDR_DATE= re.compile(r"date:\s*(\d{4}-\d{2}-\d{2})", re.I)
HDR_SUM = re.compile(r"summary:\s*(.*)")
HDR_STATUS = re.compile(r"status:\s*(\w+)", re.I)
H2 = r"^##\s+"


def load(p):
    """YAML 파일 로드"""
    with open(p, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_file(p, default="# init\n"):
    """파일이 없으면 기본 내용으로 생성"""
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(default, encoding='utf-8')


def upsert_header(md: pathlib.Path, meta: dict):
    """문서 헤더의 메타데이터 동기화"""
    txt = md.read_text(encoding='utf-8')

    # 헤더가 없으면 새로 생성
    if '<!--' not in txt or 'version:' not in txt:
        head = f"""<!--
version: {meta['version']}
date: {meta['date']}
status: {meta.get('status','draft')}
summary: {meta.get('summary','')}
-->

"""
        txt = head + txt
    else:
        # 기존 헤더 업데이트
        txt = HDR_VER.sub(f"version: {meta['version']}", txt, count=1)
        txt = HDR_DATE.sub(f"date: {meta['date']}", txt, count=1)
        txt = HDR_STATUS.sub(f"status: {meta.get('status','draft')}", txt, count=1)
        if meta.get('summary'):
            if HDR_SUM.search(txt):
                txt = HDR_SUM.sub(f"summary: {meta['summary']}", txt, count=1)
            else:
                # summary 라인 추가
                txt = txt.replace('-->', f"summary: {meta['summary']}\n-->", 1)

    md.write_text(txt, encoding='utf-8')


def upsert_section(md_text: str, header: str, body: str) -> str:
    """
    Upsert a level-2 section '## {header}' in md_text.
    If section exists, replace its body until next H2.
    Else, append at EOF with a separating newline.
    """
    pattern = re.compile(rf"(?ms)^(##\s+{re.escape(header)}\s*\n)(.*?)(?=^{H2}|\Z)")
    if match := pattern.search(md_text):
        start, end = match.span(2)  # body span
        return md_text[:start] + body.rstrip() + "\n" + md_text[end:]
    # append new section
    sep = "" if md_text.endswith("\n") else "\n"
    return md_text + f"{sep}\n## {header}\n{body.rstrip()}\n"


def apply_plan_patch(md: pathlib.Path, section: str, mode: str, content: str):
    """Handle plan.md patches with gate-scoped upsert support"""
    txt = md.read_text(encoding='utf-8')

    if mode.lower() in ("upsert", "append"):
        txt = upsert_section(txt, section, content + ("\n" if not content.endswith("\n") else ""))
    elif mode.lower() == "replace":
        # legacy: replace whole AUTOGEN section (discouraged for plan.md)
        # Fall back to original apply_patch behavior
        apply_patch(md, section, mode, content)
        return
    else:
        raise ValueError(f"Unsupported plan patch mode: {mode}")

    md.write_text(txt, encoding='utf-8')


def apply_patch(md: pathlib.Path, section: str, mode: str, content: str):
    """AUTOGEN 마커 섹션에 패치 적용"""
    txt = md.read_text(encoding='utf-8')
    b = BEGIN(section)
    e = END(section)

    if b not in txt:
        # 신규 섹션 생성: 끝에 추가
        block = f"\n\n{b}\n{content.strip()}\n{e}\n"
        txt += block
    else:
        # 기존 섹션 수정
        start = txt.index(b) + len(b)
        end = txt.index(e)
        before = txt[:start]
        after  = txt[end:]
        inner = txt[start: end]

        normalized_mode = mode.lower()
        if normalized_mode in ('replace', 'upsert'):
            new_inner = "\n" + content.strip() + "\n"
        elif normalized_mode == 'append':
            new_inner = inner.rstrip() + "\n" + content.strip() + "\n"
        elif normalized_mode == 'ensure':
            # ������� ���� ä��
            new_inner = inner if inner.strip() else "\n" + content.strip() + "\n"
        else:
            raise SystemExit(f"Unknown mode: {mode}")

        txt = before + new_inner + after

    md.write_text(txt, encoding='utf-8')


def ensure_index_and_changelog(meta):
    """docs/index.md와 CHANGELOG.md 업데이트"""
    # index.md 업데이트
    ensure_file(IDX, "# DecisionOS Docs — Version Index\n\n")
    top = f"- {meta['version']} — {meta['date']} — {meta.get('summary','')}\n"
    idx = IDX.read_text(encoding='utf-8')
    lines = idx.splitlines()

    # 첫 번째 헤딩 다음에 삽입
    insert_at = 1 if lines and lines[0].startswith('#') else 0
    if insert_at < len(lines):
        insert_at += 1  # 빈 줄 고려

    # 중복 체크
    version_exists = any(meta['version'] in line for line in lines)
    if not version_exists:
        lines.insert(insert_at, top)
        IDX.write_text("\n".join(lines) + "\n", encoding='utf-8')

    # CHANGELOG.md 업데이트
    ensure_file(CHG, "# Changelog\n\n")
    log = CHG.read_text(encoding='utf-8')
    entry = f"## {meta['version']} — {meta['date']}\n- {meta.get('summary','')}\n\n"

    # 중복 체크
    if meta['version'] not in log:
        CHG.write_text(log + ("\n" if not log.endswith("\n") else "") + entry, encoding='utf-8')


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("사용법: python scripts/wo_apply.py <work_order.yaml>")
        sys.exit(2)

    wo_file = pathlib.Path(sys.argv[1])
    if not wo_file.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {wo_file}")
        sys.exit(1)

    print(f"Work Order 로드 중: {wo_file}")
    wo = load(wo_file)
    meta = wo['meta']

    print(f"버전: {meta['version']}, 날짜: {meta['date']}, 상태: {meta.get('status','draft')}")

    # 파일 보장
    ensure_file(TS, "# TechSpec\n\n")
    ensure_file(PL, "# Plan\n\n")

    # 헤더 동기화
    print("헤더 동기화 중...")
    upsert_header(TS, meta)
    upsert_header(PL, meta)

    # 패치 적용
    patches_applied = 0
    for tgt, ops in wo.get('patches', {}).items():
        md = TS if tgt == 'techspec' else PL
        print(f"\n{md.name}에 패치 적용 중...")
        for op in ops:
            section = op['section']
            mode = op.get('mode', 'replace')
            content = op.get('content', '')
            print(f"  - 섹션: {section} (모드: {mode})")

            # plan.md에 upsert/append 모드가 있으면 게이트별 섹션 업서트 사용
            if tgt == 'plan' and mode.lower() in ('upsert', 'append'):
                apply_plan_patch(md, section, mode, content)
            else:
                apply_patch(md, section, mode, content)
            patches_applied += 1

    # 인덱스/체인지로그 업데이트
    print("\nindex.md와 CHANGELOG.md 업데이트 중...")
    ensure_index_and_changelog(meta)

    print(f"\n[OK] 완료: {meta['version']} ({patches_applied}개 패치 적용)")
    print(f"   - {TS.relative_to(ROOT)}")
    print(f"   - {PL.relative_to(ROOT)}")
    print(f"   - {IDX.relative_to(ROOT)}")
    print(f"   - {CHG.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
