import pytest
from apps.alerts.dispatcher import dispatch_alerts

pytestmark = pytest.mark.gate_q

def test_dispatch_alerts_dry_run_noop():
    events = [{"level":"warn","reason":"reason:budget-burn","message":"burn>1x","evidence_link":"e.json"}]
    routes = {"slack":{"webhook_env":"NON_EXIST_WEBHOOK","channel":"#n/a"}, "filters":{"min_severity":"warn"}}
    # dry-run true → 외부 호출 없이 예외 없이 종료
    dispatch_alerts(events, routes, dry_run=True)

def test_dispatch_alerts_empty_events_noop():
    dispatch_alerts([], {"filters":{"min_severity":"warn"}}, dry_run=True)
