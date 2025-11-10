from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict

from .collector import MONTHLY


def summary_monthly(org_id: str, yyyymm: str | None = None) -> Dict:
    now_m = datetime.now(UTC).strftime('%Y-%m')
    ym = yyyymm or now_m
    items = { (m): v for (o, m, period), v in MONTHLY.items() if o == org_id and period == ym }
    # collector uses key (org, metric, yyyymm)
    items = {}
    for (o, metric, period), v in MONTHLY.items():
        if o == org_id and (yyyymm is None or period == yyyymm):
            items[metric] = items.get(metric, 0.0) + float(v)
    return {"org_id": org_id, "yyyymm": yyyymm or now_m, "metrics": items}
