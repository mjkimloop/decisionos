from __future__ import annotations

from hashlib import sha256
import json
import time

from pydantic import BaseModel, Field


class Witness(BaseModel):
    period_start: str
    period_end: str
    sample_n: int
    coverage_ratio: float
    dropped_spans: int
    latency_p95: float | None = None
    latency_p99: float | None = None
    err_rate: float | None = None
    cost_krw: float | None = None
    citation_cov: float | None = None
    parity_delta: float | None = None
    watermark_ts: int = Field(default_factory=lambda: int(time.time()))
    clock_skew_ms: int = 0
    build_id: str
    commit_sha: str
    source_id: str
    sha256: str | None = None
    q_ledger_ref: str | None = None

    def seal(self) -> "Witness":
        payload = self.model_dump(exclude={"sha256", "q_ledger_ref"})
        digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        self.sha256 = digest
        return self


__all__ = ["Witness"]
