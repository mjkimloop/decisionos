from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict

@dataclass
class Hysteresis:
    up_ms: int = 900
    down_ms: int = 300

@dataclass
class SamplerConfig:
    min_pct: int = 1
    max_pct: int = 50
    hysteresis: Hysteresis = None

    def __post_init__(self):
        if self.hysteresis is None:
            self.hysteresis = Hysteresis()

class ShadowSampler:
    def __init__(self, cfg: SamplerConfig):
        self.cfg = cfg
        self._pct = cfg.min_pct
        self._last_change = datetime.now(timezone.utc)

    def percent(self) -> int:
        return int(self._pct)

    def _can_change(self, now: datetime, up: bool) -> bool:
        delta = now - self._last_change
        need = timedelta(milliseconds=self.cfg.hysteresis.up_ms if up else self.cfg.hysteresis.down_ms)
        return delta >= need

    def update(self, signals: Dict[str, float], now: datetime | None = None) -> int:
        """
        signals 예: {"qps": 1200, "cpu": 0.72, "queue_depth": 15}
        단순 휴리스틱: 과부하 추정 시 감소, 여유 시 증가(히스테리시스 적용)
        """
        now = now or datetime.now(timezone.utc)
        overload = (signals.get("cpu", 0.0) > 0.8) or (signals.get("queue_depth", 0.0) > 50)
        if overload and self._can_change(now, up=False):
            self._pct = max(self.cfg.min_pct, self._pct - 5)
            self._last_change = now
        elif not overload and self._can_change(now, up=True):
            self._pct = min(self.cfg.max_pct, self._pct + 5)
            self._last_change = now
        return int(self._pct)
