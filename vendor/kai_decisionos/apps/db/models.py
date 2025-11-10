from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    org_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    value_percentile: Mapped[int | None] = mapped_column(Integer, nullable=True)
    converted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    lead_id: Mapped[str | None] = mapped_column(String, ForeignKey("leads.id"), nullable=True)
    contract: Mapped[str] = mapped_column(String, nullable=False)
    klass: Mapped[str] = mapped_column("class", String, nullable=False)
    reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(String, nullable=True)
    model_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rules_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLedger(Base):
    __tablename__ = "audit_ledger"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    curr_hash: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Consent(Base):
    __tablename__ = "consent"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    subject_id: Mapped[str] = mapped_column(String, nullable=False)
    doc_hash: Mapped[str] = mapped_column(String, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
