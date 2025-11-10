from __future__ import annotations

import random
from typing import Literal

from ..models import KYCRecord, KYCStatus


class KYCStubAdapter:
    name = "adapter_kyc_stub"

    def evaluate(self, record: KYCRecord) -> str:
        rand = random.random()
        if rand < 0.05:
            record.mark_rejected("Random rejection (stub)")
        elif rand < 0.20:
            record.mark_needs_more("Additional document required")
        else:
            record.mark_verified()
        return record.status


ADAPTER = KYCStubAdapter()

__all__ = ["ADAPTER", "KYCStubAdapter"]
