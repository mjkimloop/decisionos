import pathlib

from scripts import wo_apply


def test_header_sync(tmp_path, monkeypatch):
    ts = tmp_path / "techspec.md"
    pl = tmp_path / "plan.md"
    ts.write_text("# TechSpec\n", encoding="utf-8")
    pl.write_text("# Plan\n", encoding="utf-8")

    wo = {
        "meta": {"version": "v0.1.2", "date": "2025-11-02", "status": "locked", "summary": "test"},
        "patches": {},
    }
    changed = wo_apply.apply_work_order(wo, ts, pl, check_only=False)
    assert changed
    text = ts.read_text(encoding="utf-8")
    assert "v0.1.2" in text and "2025-11-02" in text and "locked" in text and "summary" in text
