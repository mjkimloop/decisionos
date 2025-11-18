import pathlib

from scripts import wo_apply


def test_idempotent(tmp_path):
    ts = tmp_path / "techspec.md"
    pl = tmp_path / "plan.md"
    ts.write_text("# TechSpec\n", encoding="utf-8")
    pl.write_text("# Plan\n", encoding="utf-8")
    wo = {
        "meta": {"version": "v0.0.2", "date": "2025-02-02", "status": "locked", "summary": "sum"},
        "patches": {"techspec": [{"section": "X", "mode": "replace", "content": "One"}]},
    }
    changed1 = wo_apply.apply_work_order(wo, ts, pl, check_only=False)
    changed2 = wo_apply.apply_work_order(wo, ts, pl, check_only=False)
    assert changed1
    assert changed2 is False
