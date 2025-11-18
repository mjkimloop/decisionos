import pathlib

from scripts import wo_apply


def test_apply_modes(tmp_path):
    ts = tmp_path / "techspec.md"
    pl = tmp_path / "plan.md"
    ts.write_text("<!-- AUTOGEN:BEGIN:Sec --><!-- AUTOGEN:END:Sec -->", encoding="utf-8")
    pl.write_text("<!-- AUTOGEN:BEGIN:Sec --><!-- AUTOGEN:END:Sec -->", encoding="utf-8")
    wo = {
        "meta": {"version": "v0.0.1", "date": "2025-01-01", "status": "draft", "summary": ""},
        "patches": {
            "techspec": [{"section": "Sec", "mode": "replace", "content": "A"}],
            "plan": [
                {"section": "Sec", "mode": "replace", "content": "B"},
                {"section": "Sec", "mode": "append", "content": "C"},
                {"section": "Sec", "mode": "ensure", "content": "D"},
            ],
        },
    }
    changed = wo_apply.apply_work_order(wo, ts, pl, check_only=False)
    assert changed
    assert "A" in ts.read_text(encoding="utf-8")
    pl_text = pl.read_text(encoding="utf-8")
    assert "B" in pl_text and "C" in pl_text
