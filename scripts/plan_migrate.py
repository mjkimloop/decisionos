"""
plan.md 마이그레이션 스크립트

기존 plan.md의 AUTOGEN 섹션 내용을 게이트별 H2 섹션으로 분리:
  - "## Milestones — Gate-XX"
  - "## Next Actions — Gate-XX"

사용법:
    python scripts/plan_migrate.py
"""

import sys
import io
import pathlib
import re
import yaml

# Windows 콘솔 인코딩 처리
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = pathlib.Path('.')
DOCS = ROOT / 'docs'
PLAN = DOCS / 'plan.md'
WO_DIR = DOCS / 'work_orders'
INDEX = DOCS / 'index.md'

# 버전 파싱 패턴
VERSION_PATTERN = re.compile(r'- (v[\d.]+[a-z]?)\s+—.*?Gate-([A-Z]+[a-z]*):')


def load_yaml(p):
    """YAML 파일 로드"""
    with open(p, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_gate_id(summary: str) -> str:
    """summary에서 Gate ID 추출 (Gate-A, Gate-AH 등)"""
    match = re.search(r'Gate-([A-Z]+[a-z]*)', summary)
    return match.group(1) if match else 'Unknown'


def find_work_orders():
    """work_orders 디렉토리에서 모든 YAML 파일 찾기"""
    if not WO_DIR.exists():
        return []
    return sorted(WO_DIR.glob('wo-*.yaml'))


def extract_plan_content(wo_path: pathlib.Path) -> dict:
    """work order에서 plan 섹션 내용 추출"""
    wo = load_yaml(wo_path)
    meta = wo.get('meta', {})
    patches = wo.get('patches', {})
    plan_patches = patches.get('plan', [])

    result = {
        'version': meta.get('version', ''),
        'gate': extract_gate_id(meta.get('summary', '')),
        'milestones': '',
        'next_actions': ''
    }

    for patch in plan_patches:
        section = patch.get('section', '')
        content = patch.get('content', '')

        if 'Milestone' in section:
            result['milestones'] = content.strip()
        elif 'Next Action' in section or 'Actions' in section:
            result['next_actions'] = content.strip()

    return result


def build_gate_sections():
    """모든 work order에서 gate별 섹션 구축"""
    sections = []

    wo_files = find_work_orders()
    if not wo_files:
        print("경고: work_orders 디렉토리에 파일이 없습니다.")
        return sections

    print(f"{len(wo_files)}개의 work order 파일 처리 중...\n")

    for wo_path in wo_files:
        try:
            plan = extract_plan_content(wo_path)
            if not plan['gate'] or plan['gate'] == 'Unknown':
                continue

            print(f"  - {wo_path.name}: Gate-{plan['gate']}")

            if plan['milestones']:
                sections.append(f"## Milestones — Gate-{plan['gate']}\n{plan['milestones']}\n")

            if plan['next_actions']:
                sections.append(f"## Next Actions — Gate-{plan['gate']}\n{plan['next_actions']}\n")

        except Exception as e:
            print(f"경고: {wo_path.name} 처리 실패 - {e}")
            continue

    return sections


def migrate_plan():
    """plan.md 마이그레이션 수행"""
    print("plan.md 마이그레이션 시작...\n")

    # 백업 생성
    if PLAN.exists():
        backup = PLAN.with_suffix('.md.backup')
        backup.write_text(PLAN.read_text(encoding='utf-8'), encoding='utf-8')
        print(f"백업 생성: {backup}\n")
    else:
        print("경고: plan.md가 존재하지 않습니다. 새로 생성합니다.\n")

    # 기존 헤더 추출
    original = PLAN.read_text(encoding='utf-8') if PLAN.exists() else ""
    header_match = re.search(r'(<!--.*?-->)', original, re.DOTALL)
    header = header_match.group(1) + "\n\n" if header_match else ""

    # Overview 추출
    overview_match = re.search(r'(# DecisionOS Implementation Plan.*?)(?=<!--\s*AUTOGEN|##\s+|\Z)', original, re.DOTALL)
    overview = overview_match.group(1).strip() if overview_match else """# DecisionOS Implementation Plan

## Overview
이 문서는 DecisionOS의 전체 구현 계획을 시간순으로 정리합니다.
각 Gate는 독립적인 기능 단위이며, 순차적으로 완료됩니다.

---"""

    # gate별 섹션 구축
    gate_sections = build_gate_sections()

    if not gate_sections:
        print("\n경고: 마이그레이션할 내용이 없습니다.")
        return

    # 새 plan.md 구성
    new_content = header + overview + "\n\n" + "\n".join(gate_sections)

    # 저장
    PLAN.write_text(new_content, encoding='utf-8')

    print(f"\n[OK] 마이그레이션 완료!")
    print(f"   - {len(gate_sections)}개 섹션 생성")
    print(f"   - {PLAN.relative_to(ROOT)}")
    print(f"   - 백업: {PLAN.with_suffix('.md.backup')}")


def main():
    """메인 실행"""
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    migrate_plan()


if __name__ == '__main__':
    main()
