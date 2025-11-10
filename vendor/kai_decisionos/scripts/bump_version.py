import re, sys, pathlib, datetime, argparse

ROOT = pathlib.Path(".")
DOCS = ROOT / "docs"
FILES = [DOCS/"techspec.md", DOCS/"plan.md"]
INDEX = DOCS / "index.md"
CHANGELOG = ROOT / "CHANGELOG.md"

VER_RE = re.compile(r"(version:\s*)v(\d+)\.(\d+)\.(\d+)", re.I)
DATE_RE = re.compile(r"(date:\s*)\d{4}-\d{2}-\d{2}", re.I)


def bump(ver: tuple[int, int, int], mode: str):
    major, minor, patch = ver
    if mode == "major":
        return (major + 1, 0, 0)
    if mode == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def get_current_version(text: str):
    m = VER_RE.search(text)
    if not m:
        return None
    return (int(m.group(2)), int(m.group(3)), int(m.group(4)))


def fmt(v):
    return f"v{v[0]}.{v[1]}.{v[2]}"


def replace_in_file(p: pathlib.Path, new_ver: str, new_date: str, summary: str | None):
    t = p.read_text(encoding="utf-8")
    t = VER_RE.sub(rf"\1{new_ver}", t, count=1)
    t = DATE_RE.sub(rf"\1{new_date}", t, count=1)
    if summary:
        # summary 줄이 있으면 갱신
        if "summary:" in t:
            t = re.sub(r"(summary:\s*).*", rf"\1{summary}", t, count=1)
    p.write_text(t, encoding="utf-8")


def ensure_index(new_ver: str, date: str, summary: str):
    if not INDEX.exists():
        INDEX.write_text("# DecisionOS Docs — Version Index\n\n", encoding="utf-8")
    idx = INDEX.read_text(encoding="utf-8")
    top = f"- {new_ver} — {date} — {summary}".strip()
    lines = idx.splitlines()
    # 헤더 다음 줄에 신규 항목 삽입
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            insert_at = i + 1
            break
    lines.insert(insert_at, top)
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_changelog(new_ver: str, date: str, summary: str):
    if not CHANGELOG.exists():
        CHANGELOG.write_text("# Changelog\n\n", encoding="utf-8")
    log = CHANGELOG.read_text(encoding="utf-8")
    entry = f"## {new_ver} — {date}\n- {summary}\n"
    CHANGELOG.write_text(log + ("\n" if not log.endswith("\n") else "") + entry + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["patch", "minor", "major"], default="patch")
    ap.add_argument("--summary", required=True, help="한 줄 변경 요약")
    args = ap.parse_args()

    texts = [p.read_text(encoding="utf-8") for p in FILES]
    vers = [get_current_version(t) for t in texts]
    if not all(vers):
        print("ERROR: version tag missing"); sys.exit(2)
    if vers[0] != vers[1]:
        print("ERROR: techspec/plan version mismatch"); sys.exit(3)

    new = bump(vers[0], args.mode)
    new_ver = fmt(new)
    today = datetime.date.today().strftime("%Y-%m-%d")

    for p in FILES:
        replace_in_file(p, new_ver, today, args.summary)

    ensure_index(new_ver, today, args.summary)
    ensure_changelog(new_ver, today, args.summary)

    print("BUMPED", new_ver)


if __name__ == "__main__":
    main()

