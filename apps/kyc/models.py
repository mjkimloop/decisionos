from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, Field
from apps.common.timeutil import time_utcnow


class KYCStatus(str):
    VERIFIED = "verified"
    NEEDS_MORE = "needs_more"
    REJECTED = "rejected"
    PENDING = "pending"


class KYCDocument(BaseModel):
    doc_type: str
    uri: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KYCRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"kyc_{uuid4().hex[:10]}")
    org_id: str
    applicant_type: str
    risk_tier: str = "low"
    status: str = KYCStatus.PENDING
    submitted_at: datetime = Field(default_factory=time_utcnow)
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    documents: list[KYCDocument] = Field(default_factory=list)
    notes: str | None = None

    def mark_verified(self, months_valid: int = 12) -> None:
        self.status = KYCStatus.VERIFIED
        self.reviewed_at = time_utcnow()
        self.expires_at = self.reviewed_at + timedelta(days=30 * months_valid)

    def mark_needs_more(self, notes: str | None = None) -> None:
        self.status = KYCStatus.NEEDS_MORE
        self.reviewed_at = time_utcnow()
        self.notes = notes

    def mark_rejected(self, notes: str | None = None) -> None:
        self.status = KYCStatus.REJECTED
        self.reviewed_at = time_utcnow()
        self.notes = notes


__all__ = ["KYCRecord", "KYCDocument", "KYCStatus"]
