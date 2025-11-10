from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import yaml

SCHEDULE_PATH = Path(__file__).with_name("schedule.yaml")


@dataclass
class DunningRecord:
    invoice_id: str
    org_id: str | None
    status: str = "overdue"
    reason: str = "unpaid"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempts: List[dict] = field(default_factory=list)
    followups: List[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=lambda: {"attempts": 0, "recoveries": 0})

    def as_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "org_id": self.org_id,
            "status": self.status,
            "reason": self.reason,
            "started_at": self.started_at,
            "attempts": list(self.attempts),
            "followups": list(self.followups),
            "metrics": dict(self.metrics),
        }


class DunningEngine:
    def __init__(self) -> None:
        self._records: Dict[str, DunningRecord] = {}
        self.default_schedule = self._load_default_schedule()

    def _load_default_schedule(self) -> List[dict]:
        if not SCHEDULE_PATH.exists():
            return []
        return yaml.safe_load(SCHEDULE_PATH.read_text(encoding="utf-8")) or []

    def start(self, invoice_id: str, org_id: str | None, reason: str) -> DunningRecord:
        record = DunningRecord(invoice_id=invoice_id, org_id=org_id, reason=reason)
        self._records[invoice_id] = record
        return record

    def schedule(self, invoice_id: str, channel: str, eta: str, note: str | None = None) -> DunningRecord:
        record = self._require(invoice_id)
        record.followups.append({"channel": channel, "eta": eta, "note": note})
        return record

    def record_attempt(self, invoice_id: str, channel: str, outcome: str) -> DunningRecord:
        record = self._require(invoice_id)
        record.attempts.append(
            {
                "channel": channel,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        record.metrics["attempts"] += 1
        return record

    def mark_recovered(self, invoice_id: str) -> DunningRecord:
        record = self._require(invoice_id)
        record.status = "recovered"
        record.metrics["recoveries"] += 1
        return record

    def get(self, invoice_id: str) -> dict | None:
        record = self._records.get(invoice_id)
        return record.as_dict() if record else None

    def _require(self, invoice_id: str) -> DunningRecord:
        if invoice_id not in self._records:
            raise KeyError("dunning_not_started")
        return self._records[invoice_id]


ENGINE = DunningEngine()

__all__ = ["ENGINE", "DunningEngine"]
