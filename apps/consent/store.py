from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

import hashlib


def _canonical(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now_ts() -> float:
    return time.time()


@dataclass
class ConsentRecord:
    subject_id: str
    doc_hash: str
    scope: str
    granted_at: str
    ttl_sec: int
    revoked: bool = False
    version: str = "v1"
    prev_hash: str = ""
    curr_hash: str = ""


class BaseConsentStore:
    async def grant(self, rec: ConsentRecord) -> ConsentRecord:
        raise NotImplementedError

    async def revoke(self, subject_id: str, doc_hash: str) -> None:
        raise NotImplementedError

    async def list(self, subject_id: str) -> List[ConsentRecord]:
        raise NotImplementedError


class InMemoryConsentStore(BaseConsentStore):
    def __init__(self):
        # subject_id -> list[ConsentRecord]
        self._data: Dict[str, List[ConsentRecord]] = {}
        self._lock = asyncio.Lock()

    def _compute_hashes(self, subject_id: str, rec: ConsentRecord) -> ConsentRecord:
        prev = ""
        if subject_id in self._data and self._data[subject_id]:
            prev = self._data[subject_id][-1].curr_hash
        rec.prev_hash = prev
        # curr_hash는 prev_hash를 포함한 canonical dict 기반
        rec.curr_hash = hashlib.sha256(_canonical(asdict(rec)).encode()).hexdigest()
        return rec

    def _expired(self, rec: ConsentRecord) -> bool:
        try:
            granted_ts = datetime.fromisoformat(rec.granted_at.replace("Z", "+00:00")).timestamp()
        except Exception:
            granted_ts = 0.0
        return (granted_ts + rec.ttl_sec) < _now_ts()

    async def grant(self, rec: ConsentRecord) -> ConsentRecord:
        async with self._lock:
            rec = self._compute_hashes(rec.subject_id, rec)
            self._data.setdefault(rec.subject_id, []).append(rec)
            return rec

    async def revoke(self, subject_id: str, doc_hash: str) -> None:
        async with self._lock:
            found = False
            for rec in self._data.get(subject_id, []):
                if rec.doc_hash == doc_hash and not rec.revoked:
                    rec.revoked = True
                    found = True
                    break
            if not found:
                raise LookupError("not found")

    async def list(self, subject_id: str) -> List[ConsentRecord]:
        async with self._lock:
            recs = self._data.get(subject_id, [])
            # 만료 제거
            filtered: List[ConsentRecord] = []
            for rec in recs:
                if rec.revoked:
                    continue
                try:
                    granted_ts = datetime.fromisoformat(rec.granted_at.replace("Z", "+00:00")).timestamp()
                except Exception:
                    granted_ts = 0.0
                if granted_ts + rec.ttl_sec < _now_ts():
                    continue
                filtered.append(rec)
            return filtered


def get_store() -> BaseConsentStore:
    backend = os.getenv("DECISIONOS_CONSENT_BACKEND", "memory").lower()
    if backend == "memory":
        return InMemoryConsentStore()
    # 다른 백엔드는 추후 구현. 현재는 기본 메모리로 폴백.
    return InMemoryConsentStore()
