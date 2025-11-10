from __future__ import annotations

from enum import Enum


class PaymentState(str, Enum):
    CREATED = "created"
    REQUIRES_ACTION = "requires_action"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    SETTLED = "settled"
    CANCELED = "canceled"
    FAILED = "charge_failed"


class RefundState(str, Enum):
    PENDING = "refund_pending"
    REFUNDED = "refunded"
    FAILED = "refund_failed"


class InvalidTransition(Exception):
    """Raised when a payment state transition is invalid."""


def transition_payment(current: PaymentState, target: PaymentState) -> PaymentState:
    allowed = {
        PaymentState.CREATED: {PaymentState.AUTHORIZED, PaymentState.REQUIRES_ACTION, PaymentState.CANCELED, PaymentState.FAILED},
        PaymentState.REQUIRES_ACTION: {PaymentState.AUTHORIZED, PaymentState.CANCELED, PaymentState.FAILED},
        PaymentState.AUTHORIZED: {PaymentState.CAPTURED, PaymentState.CANCELED, PaymentState.FAILED},
        PaymentState.CAPTURED: {PaymentState.SETTLED},
        PaymentState.SETTLED: set(),
        PaymentState.CANCELED: set(),
        PaymentState.FAILED: set(),
    }
    if target not in allowed[current]:
        raise InvalidTransition(f"{current.value} -> {target.value}")
    return target


def transition_refund(current: RefundState, target: RefundState) -> RefundState:
    allowed = {
        RefundState.PENDING: {RefundState.REFUNDED, RefundState.FAILED},
        RefundState.REFUNDED: set(),
        RefundState.FAILED: set(),
    }
    if target not in allowed[current]:
        raise InvalidTransition(f"{current.value} -> {target.value}")
    return target


__all__ = ["PaymentState", "RefundState", "transition_payment", "transition_refund", "InvalidTransition"]
