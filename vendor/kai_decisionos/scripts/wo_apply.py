import sys, pathlib, re, argparse
from typing import Dict, Any, List

try:
    import yaml
except Exception as e:
    print("Missing dependency: pyyaml", e)
    sys.exit(2)

ROOT = pathlib.Path('.')
DOCS = ROOT / 'docs'
TS = DOCS / 'techspec.md'
PL = DOCS / 'plan.md'
IDX = DOCS / 'index.md'
CHG = ROOT / 'CHANGELOG.md'

HEADER_RE = re.compile(r"(?s)^<!--.*?version:.*?-->")
SECTION_NAME_RE = re.compile(r"^[^<>\n]+$")


def ensure_file(p: pathlib.Path, initial: str | None = None):
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(initial or '', encoding='utf-8')


def upsert_header(md: pathlib.Path, meta: Dict[str, Any]):
    head = (
        "<!--\n"
        f"version: {meta['version']}\n"
        f"date: {meta['date']}\n"
        f"status: {meta.get('status','locked')}\n"
        f"summary: {meta.get('summary','')}\n"
        "-->\n\n"
    )
    txt = md.read_text(encoding='utf-8') if md.exists() else ''
    if HEADER_RE.match(txt):
        txt = HEADER_RE.sub(head, txt, count=1)
    else:
        txt = head + txt
    md.write_text(txt, encoding='utf-8')


def _dedupe_sections(txt: str, section: str) -> str:
    """동일 섹션 마커가 여러 번 존재할 때 첫 번째만 남기고 제거"""
    begin = f"<!-- AUTOGEN:BEGIN:{section} -->"
    end = f"<!-- AUTOGEN:END:{section} -->"
    pattern = re.compile(rf"(?s){re.escape(begin)}.*?{re.escape(end)}")
    matches = list(pattern.finditer(txt))
    if len(matches) <= 1:
        return txt
    # keep first, drop others
    first = matches[0].group(0)
    # remove all occurrences, then append first once at the end
    txt = re.sub(pattern, '', txt)
    if not txt.endswith('\n'):
        txt += '\n'
    txt += first + '\n'
    return txt


def apply_patch(md: pathlib.Path, section: str, mode: str, content: str):
    if not SECTION_NAME_RE.match(section):
        raise SystemExit(f"INVALID_SECTION_NAME: {section}")
    begin = f"<!-- AUTOGEN:BEGIN:{section} -->"
    end = f"<!-- AUTOGEN:END:{section} -->"
    txt = md.read_text(encoding='utf-8')
    if begin not in txt or end not in txt:
        # append markers at end
        if not txt.endswith('\n'):
            txt += '\n'
        txt += f"\n{begin}\n(툴이 이 영역을 관리합니다)\n{end}\n"

    # normalize duplicates if any
    txt = _dedupe_sections(txt, section)

    # now replace within markers
    pattern = re.compile(rf"(?s){re.escape(begin)}.*?{re.escape(end)}")
    block_current = re.search(pattern, txt)
    if not block_current:
        return md.write_text(txt, encoding='utf-8')
    inner = content.strip('\n') + '\n'
    if mode == 'append':
        # append content if not already present
        inside_text = block_current.group(0)
        body = inside_text[len(begin):-len(end)].strip('\n')
        if content.strip() not in body:
            inner = (body + '\n' + content.strip()) if body else content.strip()
            inner += '\n'
    elif mode == 'ensure':
        # ensure each line present
        inside_text = block_current.group(0)
        body_lines = [l for l in inside_text[len(begin):-len(end)].splitlines() if l.strip()]
        for line in content.splitlines():
            if line.strip() and line.strip() not in [b.strip() for b in body_lines]:
                body_lines.append(line)
        inner = '\n'.join(body_lines) + ('\n' if body_lines else '')
    new_block = f"{begin}\n{inner}{end}"
    txt = pattern.sub(new_block, txt, count=1)
    md.write_text(txt, encoding='utf-8')


def ensure_index_and_changelog(meta: Dict[str, Any]):
    ensure_file(IDX, "# DecisionOS Docs — Version Index\n\n")
    top = f"- {meta['version']} — {meta['date']} — {meta.get('summary','')}"
    idx = IDX.read_text(encoding='utf-8')
    lines = idx.splitlines()
    insert_at = 1 if lines and lines[0].startswith('#') else 0
    if top not in idx:
        lines.insert(insert_at, top)
        IDX.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    ensure_file(CHG, "# Changelog\n\n")
    log = CHG.read_text(encoding='utf-8')
    entry = f"## {meta['version']} — {meta['date']}\n- {meta.get('summary','')}\n"
    if entry not in log:
        CHG.write_text(log + ('\n' if not log.endswith('\n') else '') + entry + '\n', encoding='utf-8')


def load(path: str) -> Dict[str, Any]:
    p = pathlib.Path(path)
    return yaml.safe_load(p.read_text(encoding='utf-8'))


def _expand_braces(path: str) -> List[str]:
    if '{' not in path or '}' not in path:
        return [path]
    pre, rest = path.split('{', 1)
    opts, post = rest.split('}', 1)
    return [pre + opt.strip() + post for opt in opts.split(',')]


def _scaffold_deliverables(wo: Dict[str, Any]):
    work = wo.get('work') or {}
    for group in work.values() if isinstance(work, dict) else []:
        if not isinstance(group, list):
            continue
        for item in group:
            paths = item.get('deliverables') or []
            for p in paths:
                for exp in _expand_braces(p):
                    target = pathlib.Path(exp)
                    if not target.is_absolute() and not str(target).startswith('kai-decisionos'):
                        target = pathlib.Path('kai-decisionos') / target
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.suffix and not target.exists():
                        try:
                            target.write_text('# scaffold\n', encoding='utf-8')
                        except Exception:
                            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work_order', help='work order yaml path')
    ap.add_argument('--scaffold', action='store_true', help='deliverables 디렉토리/파일 스캐폴딩')
    args = ap.parse_args()

    wo = load(args.work_order)
    meta = wo['meta']

    ensure_file(TS)
    ensure_file(PL)

    # 헤더 동기화
    upsert_header(TS, meta)
    upsert_header(PL, meta)

    # 섹션 패치
    for tgt, ops in (wo.get('patches') or {}).items():
        if tgt not in {'techspec', 'plan'}:
            print(f"WARN: unknown target '{tgt}', skip")
            continue
        md = TS if tgt == 'techspec' else PL
        for op in ops or []:
            sec = op.get('section')
            if not sec:
                print('WARN: missing section in op, skip')
                continue
            if not SECTION_NAME_RE.match(sec):
                print(f"WARN: invalid section name: {sec}")
                continue
            apply_patch(md, sec, op.get('mode','replace'), op.get('content',''))

    if args.scaffold:
        _scaffold_deliverables(wo)

    ensure_index_and_changelog(meta)
    print("APPLIED:", meta['version'])


if __name__ == '__main__':
    main()
