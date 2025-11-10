from __future__ import annotations

from datetime import date


def prorate_amount(amount: float, days_used: int, total_days: int) -> float:
    if total_days <= 0:
        raise ValueError("total_days must be > 0")
    ratio = max(min(days_used / total_days, 1.0), 0.0)
    return round(amount * ratio, 4)


def prorate_for_period(amount: float, period_start: date, period_end: date, usage_start: date, usage_end: date) -> float:
    total_days = (period_end - period_start).days + 1
    used_start = max(period_start, usage_start)
    used_end = min(period_end, usage_end)
    if used_end < used_start:
        return 0.0
    used_days = (used_end - used_start).days + 1
    return prorate_amount(amount, used_days, total_days)


__all__ = ["prorate_amount", "prorate_for_period"]

