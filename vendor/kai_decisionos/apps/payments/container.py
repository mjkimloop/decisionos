from __future__ import annotations

from .core import PaymentsRepository, PaymentsService
from .service import PaymentGatewayService

_repo = PaymentsRepository({}, {}, {}, {})
payments_service = PaymentsService(_repo)
gateway_service = PaymentGatewayService(payments_service)

__all__ = ["payments_service", "gateway_service", "_repo"]
