from __future__ import annotations

from typing import Dict, Optional

from .adapters.stub import ADAPTER as stub_adapter
from .models import KYCRecord, KYCDocument, KYCStatus


class KYCService:
    def __init__(self) -> None:
        self._records: Dict[str, KYCRecord] = {}

    def submit(self, *, org_id: str, applicant_type: str, documents: list[KYCDocument], risk_tier: str = "low") -> KYCRecord:
        record = KYCRecord(org_id=org_id, applicant_type=applicant_type, documents=documents, risk_tier=risk_tier)
        self._records[record.org_id] = record
        return record

    def evaluate(self, org_id: str) -> KYCRecord:
        record = self._require(org_id)
        stub_adapter.evaluate(record)
        self._records[record.org_id] = record
        return record

    def status(self, org_id: str) -> KYCRecord:
        return self._require(org_id)

    def _require(self, org_id: str) -> KYCRecord:
        if org_id not in self._records:
            raise KeyError("kyc_not_found")
        return self._records[org_id]


SERVICE = KYCService()

__all__ = ["KYCService", "SERVICE", "KYCStatus", "KYCRecord", "KYCDocument"]
