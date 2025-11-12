"""
Prometheus Metrics
DecisionOS 핵심 메트릭 등록 및 노출
"""
try:
    from prometheus_client import Gauge, Counter, generate_latest, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when prometheus_client is not available
    class MockGauge:
        def set(self, value): pass
    class MockCounter:
        def labels(self, **kwargs): return self
        def inc(self, amount=1): pass

from typing import Dict, Any


# 핵심 메트릭 정의
if PROMETHEUS_AVAILABLE:
    risk_score_gauge = Gauge(
        "decisionos_risk_score",
        "Current risk score from Risk Governor"
    )

    burn_rate_gauge = Gauge(
        "decisionos_burn_rate",
        "Current error budget burn rate"
    )

    shadow_pct_gauge = Gauge(
        "decisionos_shadow_pct",
        "Current shadow sampling percentage"
    )

    alerts_total_counter = Counter(
        "decisionos_alerts_total",
        "Total number of alerts dispatched",
        ["level"]
    )
else:
    risk_score_gauge = MockGauge()
    burn_rate_gauge = MockGauge()
    shadow_pct_gauge = MockGauge()
    alerts_total_counter = MockCounter()


def update_risk_score(score: float):
    """Risk score 업데이트"""
    risk_score_gauge.set(score)


def update_burn_rate(rate: float):
    """Burn rate 업데이트"""
    burn_rate_gauge.set(rate)


def update_shadow_pct(pct: float):
    """Shadow sampling % 업데이트"""
    shadow_pct_gauge.set(pct)


def increment_alert(level: str):
    """Alert 카운터 증가"""
    alerts_total_counter.labels(level=level).inc()


def get_metrics_text() -> str:
    """Prometheus 포맷으로 메트릭 텍스트 반환"""
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY).decode("utf-8")
    else:
        return "# Prometheus client not available\n"


def export_snapshot(path: str):
    """메트릭 스냅샷을 파일로 저장 (CI 아티팩트용)"""
    import os

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(get_metrics_text())

    print(f"[OK] Metrics snapshot exported to {path}")
