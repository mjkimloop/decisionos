from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

from apps.common.metrics import REG


@dataclass
class WindowSpec:
    name: str
    duration: int
    fast_threshold: float
    slow_threshold: float


@dataclass
class MetricSpec:
    key: str
    kind: str  # "availability" or "latency"
    objective: float


def _parse_duration(value: str | int) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    value = value.strip().lower()
    if value.endswith("ms"):
        return int(float(value[:-2]) / 1000.0)
    if value.endswith("s"):
        return int(float(value[:-1]))
    if value.endswith("m"):
        return int(float(value[:-1]) * 60)
    if value.endswith("h"):
        return int(float(value[:-1]) * 3600)
    return int(value)


def load_policy(path: str) -> Tuple[List[WindowSpec], Dict[str, MetricSpec]]:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    window_specs: List[WindowSpec] = []
    for raw in data.get("windows", []):
        window_specs.append(
            WindowSpec(
                name=str(raw.get("name")),
                duration=_parse_duration(raw.get("duration", 300)),
                fast_threshold=float(raw.get("fast_threshold", 2.0)),
                slow_threshold=float(raw.get("slow_threshold", 4.0)),
            )
        )
    metrics: Dict[str, MetricSpec] = {}
    m_cfg = data.get("metrics", {})
    if "error_rate" in m_cfg:
        metrics["error_rate"] = MetricSpec(
            key="error_rate",
            kind="availability",
            objective=float(m_cfg["error_rate"].get("objective_availability", 0.995)),
        )
    if "latency_p95" in m_cfg:
        metrics["latency_p95"] = MetricSpec(
            key="latency_p95",
            kind="latency",
            objective=float(m_cfg["latency_p95"].get("objective_ms", 400)),
        )
    if "latency_p99" in m_cfg:
        metrics["latency_p99"] = MetricSpec(
            key="latency_p99",
            kind="latency",
            objective=float(m_cfg["latency_p99"].get("objective_ms", 600)),
        )
    return window_specs, metrics


def load_samples(path: Optional[str] = None) -> List[dict]:
    candidates = [
        path,
        os.getenv("BURN_SAMPLES_PATH"),
        "var/metrics/burn_samples.json",
        "configs/slo/burn_samples_stub.json",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return json.loads(Path(candidate).read_text(encoding="utf-8"))["samples"]
    return []


def _calc_error_rate(samples: Iterable[dict]) -> Tuple[int, int, float]:
    total = sum(int(s.get("requests", 0)) for s in samples)
    errors = sum(int(s.get("errors", 0)) for s in samples)
    rate = (errors / total) if total > 0 else 0.0
    return total, errors, rate


def _calc_latency(samples: Iterable[dict], key: str) -> float:
    values = [float(s.get(key, 0.0)) for s in samples if key in s]
    return max(values) if values else 0.0


def _state_from_burn(burn: float, window: WindowSpec) -> str:
    if burn >= window.slow_threshold:
        return "critical"
    if burn >= window.fast_threshold:
        return "warn"
    return "ok"


def compute_burn_report(
    *,
    policy_path: str,
    sample_path: Optional[str] = None,
    now: Optional[int] = None,
) -> dict:
    windows, metrics = load_policy(policy_path)
    samples = load_samples(sample_path)
    if not samples:
        return {
            "generated_at": int(time.time()),
            "windows": [],
            "overall": {"state": "unknown", "reason": "no-samples"},
        }
    latest_ts = max(int(s.get("ts", 0)) for s in samples if s.get("ts"))
    now = now or latest_ts or int(time.time())
    severity_rank = {"critical": 3, "warn": 2, "ok": 0, "unknown": 0}
    result_windows = []
    overall_state = "ok"
    worst_descriptor = ""

    for window in windows:
        window_start = now - window.duration
        bucket = [s for s in samples if int(s.get("ts", 0)) >= window_start]
        if not bucket:
            state = "ok"
            metrics_payload = {}
        else:
            metrics_payload = {}
            for key, spec in metrics.items():
                if spec.kind == "availability":
                    total, errors, rate = _calc_error_rate(bucket)
                    allowed_error = max(1.0 - spec.objective, 1e-6)
                    burn = (rate / allowed_error) if allowed_error > 0 else 0.0
                    metrics_payload[key] = {
                        "burn": round(burn, 3),
                        "value": rate,
                        "total": total,
                        "errors": errors,
                    }
                else:
                    observed = _calc_latency(bucket, spec.key)
                    burn = (observed / spec.objective) if spec.objective > 0 else 0.0
                    metrics_payload[key] = {
                        "burn": round(burn, 3),
                        "value": observed,
                        "objective": spec.objective,
                    }
            metric_burn = max((m["burn"] for m in metrics_payload.values()), default=0.0)
            state = _state_from_burn(metric_burn, window)
        result_windows.append(
            {
                "name": window.name,
                "duration": window.duration,
                "state": state,
                "metrics": metrics_payload,
            }
        )
        if severity_rank.get(state, 0) > severity_rank.get(overall_state, 0):
            overall_state = state
            worst_descriptor = window.name

        gauge_prefix = window.name.replace("-", "_")
        for metric_name, info in metrics_payload.items():
            gauge = REG.gauge(
                f"burn_rate_{metric_name}_{gauge_prefix}",
                f"Burn rate for {metric_name} ({window.name})",
            )
            gauge.set(info.get("burn", 0.0))

    return {
        "generated_at": int(time.time()),
        "windows": result_windows,
        "overall": {"state": overall_state, "window": worst_descriptor},
    }


def save_report(report: dict, path: str) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def load_report(path: str) -> Optional[dict]:
    file = Path(path)
    if not file.exists():
        return None
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except Exception:
        return None


def ensure_report(report_path: str, policy_path: str) -> dict:
    report = load_report(report_path)
    if report:
        return report
    report = compute_burn_report(policy_path=policy_path)
    save_report(report, report_path)
    return report


def card_payload(report: dict, window_name: Optional[str] = None) -> dict:
    windows = report.get("windows", [])
    if window_name:
        windows = [w for w in windows if w.get("name") == window_name]
    return {
        "generated_at": report.get("generated_at"),
        "overall": report.get("overall", {}),
        "windows": windows,
    }


__all__ = [
    "compute_burn_report",
    "load_policy",
    "load_samples",
    "save_report",
    "load_report",
    "ensure_report",
    "card_payload",
]
