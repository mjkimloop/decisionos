from __future__ import annotations

def split_fees(amount: int, pg_fee_rate: float = 0.029, platform_fee_rate: float = 0.005) -> dict:
    pg_fee = int(amount * pg_fee_rate)
    platform_fee = int(amount * platform_fee_rate)
    net = amount - pg_fee - platform_fee
    return {
        "gross": amount,
        "pg_fee": pg_fee,
        "platform_fee": platform_fee,
        "net": net,
    }


__all__ = ["split_fees"]
