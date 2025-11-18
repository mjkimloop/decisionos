import pathlib

import pytest

from scripts import doc_guard


def test_marker_mismatch_detects(tmp_path, monkeypatch):
    ts = tmp_path / "techspec.md"
    ts.write_text("<!-- AUTOGEN:BEGIN:A --><!-- AUTOGEN:END:B -->", encoding="utf-8")
    pl = tmp_path / "plan.md"
    pl.write_text("<!-- AUTOGEN:BEGIN:X --><!-- AUTOGEN:END:X -->", encoding="utf-8")
    monkeypatch.setattr(doc_guard, "TECHSPEC", ts)
    monkeypatch.setattr(doc_guard, "PLAN", pl)
    with pytest.raises(SystemExit):
        doc_guard.main()
