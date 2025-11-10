from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from apps.ops.reports.reason_trend import aggregate_reason_trend


def _cors_origins() -> List[str]:
    raw = os.getenv("DECISIONOS_CORS_ORIGINS", "")
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


app = FastAPI(title="DecisionOS Ops API", version="v0.5.11p")

try:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins() or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    # In unit tests or stripped-down envs the middleware might be unavailable.
    pass


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "version": "v0.5.11p"})


@app.get("/ops/reason-trend")
def reason_trend(days: int = Query(7, ge=1, le=90)) -> JSONResponse:
    trend = aggregate_reason_trend("var/evidence", days)
    return JSONResponse(trend)


@app.get("/ops/reason-trend/card")
def reason_trend_card(
    days: int = Query(7, ge=1, le=90),
    topK: int = Query(5, ge=1, le=20),
) -> JSONResponse:
    trend = aggregate_reason_trend("var/evidence", days)
    top = (trend.get("total_top") or [])[:topK]
    return JSONResponse(
        {
            "window_days": trend.get("window_days"),
            "generated_at": trend.get("generated_at"),
            "top": top,
            "count_evidence": trend.get("count_evidence"),
        }
    )


@app.get("/ops/reason-trend/card.html", response_class=HTMLResponse)
def reason_trend_card_html(
    days: int = Query(7, ge=1, le=90),
    topK: int = Query(5, ge=1, le=20),
) -> HTMLResponse:
    trend = aggregate_reason_trend("var/evidence", days)
    top = (trend.get("total_top") or [])[:topK]
    list_items = "".join(f"<li><code>{code}</code> × {count}</li>" for code, count in top)
    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Reason Trend</title>
      </head>
      <body>
        <h3>Reason Trend (last {trend.get('window_days')} days)</h3>
        <p>generated_at: {trend.get('generated_at')}</p>
        <p>total reason count: {trend.get('count_evidence')}</p>
        <ul>{list_items}</ul>
      </body>
    </html>
    """
    return HTMLResponse(html)
