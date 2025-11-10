import sys, json
from pathlib import Path

# Ensure 'kai-decisionos' is importable regardless of CWD
BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from packages.common.config import settings


def _fail(msg: str, code: int = 2):
    print(f"SEAL_FAIL: {msg}")
    sys.exit(code)


def check_docs_guard():
    # 재사용: 내부 모듈 호출
    try:
        import kai_decisionos.scripts.doc_guard as doc_guard  # type: ignore
    except Exception:
        import scripts.doc_guard as doc_guard  # type: ignore
    # doc_guard는 print 후 종료코드로 신호함
    try:
        doc_guard.main()  # type: ignore[attr-defined]
    except SystemExit as e:
        if int(e.code or 0) != 0:
            _fail("docs guard failed", int(e.code or 2))


def check_rule_linter(path: Path):
    from apps.rule_engine.linter import lint_rules
    issues, coverage = lint_rules(path)
    if issues:
        kinds = {i.kind for i in issues}
        _fail(f"rule linter issues: {len(issues)} ({','.join(sorted(kinds))})")
    # 최소 커버리지 힌트(권고): action.class 100%
    if coverage.get("action_class_pct", 0.0) < 100.0:
        print(f"SEAL_WARN: action.class coverage {coverage.get('action_class_pct')}% (<100%)")


def check_audit_chain():
    from apps.audit_ledger.verify_hashes import verify_chain
    # prefer kai-decisionos/var if default not found
    p = Path(settings.audit_log_path)
    if not p.exists():
        p = BASE / settings.audit_log_path
    ok = verify_chain(p)
    if not ok:
        _fail("audit hash chain verification failed")


def check_metrics_report(optional: bool = True):
    # 존재 시 포맷 검사, 없으면 경고
    j = Path("var/reports/simulate_lead_triage.json")
    if not j.exists():
        j = BASE / j
    if not j.exists():
        if not optional:
            _fail("missing metrics JSON report: var/reports/simulate_lead_triage.json")
        print("SEAL_WARN: metrics JSON not found (skipping)")
        return
    data = json.loads(j.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or data
    for key in ("reject_precision", "reject_recall", "review_rate"):
        if key not in metrics:
            _fail(f"metrics missing key: {key}")


def main():
    # 1) 문서 가드
    check_docs_guard()
    # 2) 룰 린터(엄격)
    rules_dir = Path("packages/rules/triage")
    if not rules_dir.exists():
        rules_dir = BASE / rules_dir
    if rules_dir.exists():
        check_rule_linter(rules_dir)
    else:
        print("SEAL_WARN: rules directory not found, skipping linter")
    # 3) 감사 해시체인 검증
    check_audit_chain()
    # 4) 메트릭 JSON 형식(선택)
    check_metrics_report(optional=True)
    print("SEAL_OK")


if __name__ == "__main__":
    main()
