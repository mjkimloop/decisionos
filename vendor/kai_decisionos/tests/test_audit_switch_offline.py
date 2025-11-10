from pathlib import Path
from apps.audit_ledger.ledger import AuditLedger
from apps.switchboard.switch import choose_route
from apps.rule_engine.offline_eval import run_report


def test_audit_chain(tmp_path: Path):
    led = AuditLedger(tmp_path / "audit.jsonl")
    a = led.append("id1", {"input": {"a": 1}, "output": {"x": 1}})
    b = led.append("id2", {"input": {"a": 2}, "output": {"x": 2}})
    assert a.curr_hash == b.prev_hash


def test_switch_default_route():
    meta = choose_route("unknown_contract")
    assert meta["chosen_model"] == "rules-only"


def test_offline_eval_html(tmp_path: Path):
    csv = tmp_path / "s.csv"
    csv.write_text("org_id,credit_score,dti,income_verified,converted\na,700,0.3,True,1\n")
    out = tmp_path / "r.html"
    tpl = Path("apps/rule_engine/templates/report.html")
    report_data = run_report("lead_triage", csv, "converted", out, tpl)
    assert out.exists()
    assert "Offline Evaluation Report" in out.read_text(encoding="utf-8")
    assert "metrics" in report_data

