from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime


# naive in-memory meter events and aggregates
EVENTS: list[dict] = []
DAILY: dict[tuple[str, str, str, str], float] = defaultdict(float)  # (org, project, metric, date) -> value
MONTHLY: dict[tuple[str, str, str], float] = defaultdict(float)  # (org, metric, yyyymm)


def ingest_event(event: dict):
    # expected keys: org_id, project_id, metric, value
    now = datetime.now(UTC)
    event = {**event, "ts": now.isoformat()}
    EVENTS.append(event)
    date = now.strftime("%Y-%m-%d")
    yyyymm = now.strftime("%Y-%m")
    key_d = (event["org_id"], event.get("project_id", "-"), event["metric"], date)
    key_m = (event["org_id"], event["metric"], yyyymm)
    DAILY[key_d] += float(event.get("value", 1))
    MONTHLY[key_m] += float(event.get("value", 1))


def read_daily(org_id: str, metric: str, from_date: str | None = None, to_date: str | None = None):
    items = []
    for (o, _p, m, d), v in DAILY.items():
        if o == org_id and m == metric:
            items.append({"date": d, "value": v})
    items.sort(key=lambda x: x["date"])  # naive
    return items


def read_monthly(org_id: str, metric: str, yyyymm: str | None = None):
    items = []
    for (o, m, ym), v in MONTHLY.items():
        if o == org_id and m == metric and (yyyymm is None or ym == yyyymm):
            items.append({"yyyymm": ym, "value": v})
    items.sort(key=lambda x: x["yyyymm"])  # naive
    return items
