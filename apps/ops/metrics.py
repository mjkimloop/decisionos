from __future__ import annotations

try:
    from prometheus_client import Gauge, Counter
    _risk_score = Gauge("decisionos_risk_score", "Risk score [0..10)")
    _burn_rate = Gauge("decisionos_burn_rate", "Burn rate [0..∞)")
    _shadow_pct = Gauge("decisionos_shadow_pct", "Shadow sampling %")
    _alerts_total = Counter("decisionos_alerts_total", "Alert count", ["level"])
except ImportError:
    class _MockGauge:
        def set(self, value): pass
    class _MockCounter:
        def labels(self, **kwargs): return self
        def inc(self): pass
    _risk_score = _MockGauge()
    _burn_rate = _MockGauge()
    _shadow_pct = _MockGauge()
    _alerts_total = _MockCounter()

def observe_risk_score(value: float) -> None:
    _risk_score.set(value)

def observe_burn_rate(value: float) -> None:
    _burn_rate.set(value)

def set_shadow_pct(value: float) -> None:
    _shadow_pct.set(value)

def inc_alert(level: str) -> None:
    _alerts_total.labels(level=level).inc()
