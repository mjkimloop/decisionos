import re, sys, pathlib, datetime

ROOT = pathlib.Path(".")
DOCS = ROOT / "docs"
REQ = [DOCS/"techspec.md", DOCS/"plan.md", DOCS/"index.md"]
CHANGELOG = ROOT / "CHANGELOG.md"

VER_RE = re.compile(r"version:\s*(v\d+\.\d+\.\d+)", re.I)
DATE_RE = re.compile(r"date:\s*(\d{4}-\d{2}-\d{2})", re.I)

def head_meta(p: pathlib.Path):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    mver = VER_RE.search(txt)
    mdt  = DATE_RE.search(txt)
    return (mver.group(1) if mver else None, mdt.group(1) if mdt else None)

def main():
    missing = [str(p) for p in REQ if not p.exists()]
    if missing:
        print("MISSING:", ", ".join(missing)); sys.exit(2)

    v1, d1 = head_meta(REQ[0])
    v2, d2 = head_meta(REQ[1])
    if not v1 or not v2:
        print("NO_VERSION_TAG in techspec/plan"); sys.exit(3)
    if v1 != v2:
        print(f"VERSION_MISMATCH: {v1} != {v2}"); sys.exit(4)

    # index 최신행 포함 여부 확인(경고 수준)
    idx = REQ[2].read_text(encoding="utf-8", errors="ignore")
    if v1 not in idx:
        print(f"INDEX_WARN: {v1} 미기재 — bump 스크립트로 갱신 필요")
    # changelog 존재 확인(경고 수준)
    if not CHANGELOG.exists():
        print("CHANGELOG_WARN: 파일 없음(초기화 필요)")

    print("OK")

if __name__ == "__main__":
    main()

