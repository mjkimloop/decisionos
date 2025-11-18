import re
import pathlib


def test_links_exist():
    t = pathlib.Path("docs/ops/RUNBOOK-OPS.md").read_text(encoding="utf-8")
    for m in re.findall(r"\((docs/[^)]+)\)", t):
        assert pathlib.Path(m).exists(), f"missing doc link: {m}"
