from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.gateway.main import app
from apps.events import sdk as events_sdk
from apps.events import collector as events_collector
from apps.feedback import store as feedback_store
from apps.backlog import store as backlog_store


client = TestClient(app)
HEADERS = {"X-Api-Key": "dev-key", "X-Role": "admin", "X-Tenant-ID": "demo-tenant"}


def test_event_ingest_and_summary(tmp_path, monkeypatch):
    event_path = tmp_path / "events" / "events.jsonl"
    monkeypatch.setattr(events_sdk, "DEFAULT_EVENT_STORE", event_path)
    monkeypatch.setattr(events_collector, "DEFAULT_EVENT_STORE", event_path)

    payload = {"event": "decision.accepted", "user_id": "u1", "metadata": {"contract": "demo"}}
    res = client.post("/api/v1/analytics/events", json=payload, headers=HEADERS)
    assert res.status_code == 201

    payload2 = {"event": "decision.review", "user_id": "u2", "metadata": {"contract": "demo"}}
    client.post("/api/v1/analytics/events", json=payload2, headers=HEADERS)

    summary = client.get("/api/v1/analytics/summary", headers=HEADERS)
    assert summary.status_code == 200
    data = summary.json()
    assert data["total"] == 2
    assert data["by_event"]["decision.accepted"] == 1

    dashboard = client.get("/api/v1/analytics/dashboard", headers=HEADERS)
    assert dashboard.status_code == 200
    assert "DecisionOS Analytics" in dashboard.text


def test_feedback_and_backlog(tmp_path, monkeypatch):
    feedback_path = tmp_path / "feedback" / "nps.jsonl"
    backlog_path = tmp_path / "backlog" / "items.jsonl"
    monkeypatch.setattr(feedback_store, "DEFAULT_FEEDBACK_STORE", feedback_path)
    monkeypatch.setattr(backlog_store, "DEFAULT_BACKLOG_STORE", backlog_path)

    feedback_payload = {"rating": 9, "comment": "Great", "user_id": "user-123"}
    res = client.post("/api/v1/feedback/nps", json=feedback_payload, headers=HEADERS)
    assert res.status_code == 201
    stats = client.get("/api/v1/feedback/stats", headers=HEADERS)
    assert stats.json()["n"] == 1
    assert stats.json()["counts"]["promoter"] == 1

    backlog_payload = {
        "title": "Improve latency",
        "reach": 100.0,
        "impact": 2.0,
        "confidence": 0.8,
        "effort": 5.0,
        "owner": "ops",
    }
    item = client.post("/api/v1/backlog/items", json=backlog_payload, headers=HEADERS)
    assert item.status_code == 201
    listing = client.get("/api/v1/backlog/items", headers=HEADERS)
    items = listing.json().get("items", [])
    assert len(items) == 1
    assert items[0]["title"] == "Improve latency"
