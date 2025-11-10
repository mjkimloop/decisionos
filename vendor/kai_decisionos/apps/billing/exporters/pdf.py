from __future__ import annotations


def export_pdf(invoice: dict) -> bytes:
    # dev stub: return UTF-8 bytes of a simple text; real PDF later
    txt = f"INVOICE {invoice['id']} org={invoice['org_id']} period={invoice['period']} total={invoice['total']}\n"
    return txt.encode("utf-8")

