from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field

class WatermarkPolicy(BaseModel):
    """
    - max_lag_sec: 현재(now) 기준 허용 지연 한도(초)
    - drop_too_late: 한도 초과시 드롭 여부(True=드롭, False=유지)
    """
    max_lag_sec: int = Field(ge=0, default=900)  # 15분
    drop_too_late: bool = True

    def classify(self, event_ts: dt.datetime, now: dt.datetime) -> str:
        """
        반환: 'on_time' | 'late_kept' | 'late_dropped'
        - age_sec <= 0 → on_time
        - 0 < age_sec <= max_lag_sec → late_kept
        - age_sec > max_lag_sec → late_dropped (drop_too_late=True일 때만 실제 드롭)
        """
        age = (now - event_ts).total_seconds()
        if age <= 0:
            return "on_time"
        if age <= self.max_lag_sec:
            return "late_kept"
        return "late_dropped"
