import pathlib

from scripts import doc_guard, wo_apply


def test_autodoc_flow(tmp_path, monkeypatch):
    # 준비: 복사본 경로로 포인터 교체
    techspec = tmp_path / "techspec.md"
    plan = tmp_path / "plan.md"
    techspec.write_text("<!-- AUTOGEN:BEGIN:Open Issues --><!-- AUTOGEN:END:Open Issues -->", encoding="utf-8")
    plan.write_text("<!-- AUTOGEN:BEGIN:Milestones --><!-- AUTOGEN:END:Milestones -->", encoding="utf-8")

    wo = {
        "meta": {"version": "v0.0.3", "date": "2025-03-03", "status": "locked", "summary": "e2e"},
        "patches": {
            "techspec": [{"section": "Open Issues", "mode": "replace", "content": "foo"}],
            "plan": [{"section": "Milestones", "mode": "replace", "content": "bar"}],
        },
    }
    changed = wo_apply.apply_work_order(wo, techspec_path=techspec, plan_path=plan, check_only=False)
    assert changed
    # doc_guard strict 호출이 성공해야 함
    monkeypatch.setattr(doc_guard, "TECHSPEC", techspec)
    monkeypatch.setattr(doc_guard, "PLAN", plan)
    monkeypatch.setattr(doc_guard, "latest_work_order_meta", lambda: wo["meta"])
    doc_guard.main()
