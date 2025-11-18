import json
from pathlib import Path

from scripts.ci.check_skeletons import scan_tree


def test_scan_tree_detects_zero_byte_and_comment_only(tmp_path):
    root = tmp_path
    z = root / "pkg" / "a" / "__init__.py"
    z.parent.mkdir(parents=True, exist_ok=True)
    z.write_bytes(b"")
    c = root / "pkg" / "b" / "__init__.py"
    c.parent.mkdir(parents=True, exist_ok=True)
    c.write_text("# only comments\n# ok\n", encoding="utf-8")
    n = root / "pkg" / "c" / "__init__.py"
    n.parent.mkdir(parents=True, exist_ok=True)
    n.write_text('"""ok"""', encoding="utf-8")

    rep = scan_tree(root, allowlist=set())
    assert any("Zero-byte __init__" in e for e in rep["errors"])
    assert any("Comment-only __init__" in w for w in rep["warnings"])
