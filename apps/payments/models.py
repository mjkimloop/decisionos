from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .state_machine import PaymentState, RefundState
from apps.common.timeutil import time_utcnow


class PaymentIntent(BaseModel):
    id: str = Field(default_factory=lambda: f"pi_{uuid4().hex[:12]}")
    org_id: str
    amount: int
    currency: str = "KRW"
    customer_ref: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=time_utcnow)
    state: PaymentState = PaymentState.CREATED
    payment_method: Optional[str] = None
    adapter: str = "manual_stub"


class Charge(BaseModel):
    id: str = Field(default_factory=lambda: f"ch_{uuid4().hex[:12]}")
    intent_id: str
    amount: int
    currency: str
    adapter: str
    state: PaymentState
    created_at: datetime = Field(default_factory=time_utcnow)
    captured_at: datetime | None = None
    settled_at: datetime | None = None
    receipt_id: str | None = None


class Refund(BaseModel):
    id: str = Field(default_factory=lambda: f"rf_{uuid4().hex[:12]}")
    charge_id: str
    amount: int
    currency: str
    reason: str | None = None
    state: RefundState = RefundState.PENDING
    created_at: datetime = Field(default_factory=time_utcnow)
    processed_at: datetime | None = None


class Receipt(BaseModel):
    id: str = Field(default_factory=lambda: f"rc_{uuid4().hex[:10]}")
    charge_id: str
    org_id: str
    total: int
    tax_amount: int = 0
    currency: str = "KRW"
    issued_at: datetime = Field(default_factory=time_utcnow)
    pdf_uri: str | None = None
    json_uri: str | None = None


__all__ = ["PaymentIntent", "Charge", "Refund", "Receipt"]
